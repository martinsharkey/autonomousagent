import subprocess
import sys
import os
import json
import shutil
from typing import Dict, List, Tuple, Optional
from core.models import REQUIRED_MODELS, FALLBACK_MODELS, FALLBACK_RAM, MIN_RAM_GB


def check_ollama_running() -> bool:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_installed_models() -> List[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return []
        
        models = []
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        return []


def get_available_ram_gb() -> float:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3)
    except ImportError:
        pass
    
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "os", "get", "FreePhysicalMemory"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and line.isdigit():
                    return int(line) / (1024 ** 2)
        else:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
    except Exception:
        pass
    
    return 0.0


def get_total_ram_gb() -> float:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.total / (1024 ** 3)
    except ImportError:
        pass
    
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "os", "get", "TotalVisibleMemorySize"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and line.isdigit():
                    return int(line) / (1024 ** 2)
        else:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
    except Exception:
        pass
    
    return 0.0


def check_models_present(installed: List[str]) -> Tuple[List[str], List[str], List[str]]:
    present = []
    missing = []
    fallback_available = []
    
    for model in REQUIRED_MODELS:
        if model in installed:
            present.append(model)
        else:
            missing.append(model)
            fallback = FALLBACK_MODELS.get(model)
            if fallback and fallback in installed:
                fallback_available.append((model, fallback))
    
    return present, missing, fallback_available


def calculate_required_ram(present: List[str], fallback_available: List[Tuple[str, str]]) -> float:
    total = 0.0
    for model in present:
        total += REQUIRED_MODELS[model]["ram_gb"]
    for original, fallback in fallback_available:
        total += FALLBACK_RAM.get(fallback, 1.5)
    for model in REQUIRED_MODELS:
        if model not in present and not any(o == model for o, _ in fallback_available):
            fallback = FALLBACK_MODELS.get(model)
            if fallback:
                total += FALLBACK_RAM.get(fallback, 1.5)
    return total


def check_cloud_providers_available() -> tuple[bool, list[str]]:
    """Check if any cloud LLM provider has an API key configured."""
    from core.api_router import get_llm_router
    
    try:
        router = get_llm_router()
        active_providers = router._get_active_providers()
        provider_names = [p['name'] for p in active_providers]
        return len(active_providers) > 0, provider_names
    except Exception as e:
        print(f"[PREFLIGHT] Error checking cloud providers: {e}")
        return False, []


def run_preflight() -> Dict:
    """Run preflight check - passes if cloud providers OR local Ollama available."""
    report = {
        "backend": os.getenv("LLM_BACKEND", "cloud"),
        "cloud_available": False,
        "cloud_providers": [],
        "ollama_running": False,
        "installed_models": [],
        "present_models": [],
        "missing_models": [],
        "fallback_available": [],
        "total_ram_gb": 0.0,
        "available_ram_gb": 0.0,
        "required_ram_gb": 0.0,
        "ram_sufficient": False,
        "all_models_present": False,
        "can_run": False,
        "errors": []
    }
    
    # Check cloud providers first (cloud-first architecture)
    if report["backend"] == "cloud":
        report["cloud_available"], report["cloud_providers"] = check_cloud_providers_available()
        
        if report["cloud_available"]:
            print(f"[PREFLIGHT] Cloud providers available: {', '.join(report['cloud_providers'])}")
            report["can_run"] = True
            return report
        else:
            print("[PREFLIGHT] No cloud providers configured, checking local Ollama...")
    
    # Fall back to local Ollama check
    report["ollama_running"] = check_ollama_running()
    if not report["ollama_running"]:
        report["errors"].append(
            "No cloud providers configured AND Ollama is not running. "
            "Set at least one cloud API key in .env or start Ollama."
        )
        return report
    
    report["installed_models"] = get_installed_models()
    present, missing, fallback_available = check_models_present(report["installed_models"])
    report["present_models"] = present
    report["missing_models"] = missing
    report["fallback_available"] = fallback_available
    report["all_models_present"] = len(missing) == 0
    
    report["total_ram_gb"] = round(get_total_ram_gb(), 2)
    report["available_ram_gb"] = round(get_available_ram_gb(), 2)
    report["required_ram_gb"] = round(calculate_required_ram(present, fallback_available), 2)
    report["ram_sufficient"] = report["available_ram_gb"] >= report["required_ram_gb"]
    
    if report["available_ram_gb"] < MIN_RAM_GB:
        report["errors"].append(
            f"Available RAM ({report['available_ram_gb']:.1f}GB) is below minimum ({MIN_RAM_GB}GB)."
        )
    
    report["can_run"] = report["ollama_running"] and report["ram_sufficient"]
    
    return report


def print_report(report: Dict):
    print("\n" + "=" * 60)
    print("MODEL & RESOURCE PREFLIGHT CHECK")
    print("=" * 60)
    
    print(f"  Backend: {report.get('backend', 'cloud')}")
    
    # Cloud provider status
    if report.get('cloud_available'):
        print(f"  Cloud providers: [OK] ({len(report['cloud_providers'])} active)")
        for provider in report['cloud_providers']:
            print(f"    - {provider}")
    else:
        print(f"  Cloud providers: [NONE] (no API keys configured)")
    
    # Local Ollama status
    status = "OK" if report["ollama_running"] else "FAIL"
    print(f"  Ollama running: [{status}]")
    
    if report["ollama_running"]:
        print(f"\n  Installed models: {len(report['installed_models'])}")
        for m in report["installed_models"]:
            print(f"    - {m}")
        
        print(f"\n  Required models:")
        for model, info in REQUIRED_MODELS.items():
            if model in report["present_models"]:
                print(f"    [{('OK').ljust(4)}] {model} ({info['role']}, ~{info['ram_gb']}GB)")
            else:
                fallback = FALLBACK_MODELS.get(model)
                fb_info = f" -> fallback: {fallback}" if fallback else ""
                print(f"    [MISS] {model} ({info['role']}){fb_info}")
        
        if report["fallback_available"]:
            print(f"\n  Fallback mappings available:")
            for original, fallback in report["fallback_available"]:
                print(f"    {original} -> {fallback}")
        
        print(f"\n  RAM:")
        print(f"    Total:     {report['total_ram_gb']:.1f} GB")
        print(f"    Available: {report['available_ram_gb']:.1f} GB")
        print(f"    Required:  {report['required_ram_gb']:.1f} GB")
        ram_status = "OK" if report["ram_sufficient"] else "FAIL"
        print(f"    Status:    [{ram_status}]")
    
    if report["errors"]:
        print(f"\n  ERRORS:")
        for err in report["errors"]:
            print(f"    - {err}")
    
    can_run = "YES" if report["can_run"] else "NO"
    print(f"\n  Can run council: [{can_run}]")
    print("=" * 60 + "\n")


def main():
    report = run_preflight()
    print_report(report)
    
    if not report["can_run"]:
        print("Preflight check FAILED. Fix the issues above before running the council.")
        sys.exit(1)
    
    print("Preflight check PASSED.")
    sys.exit(0)


if __name__ == "__main__":
    main()
