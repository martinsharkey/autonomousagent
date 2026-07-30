"""
Host Awareness - runtime introspection of the daemon's environment.

The council must understand:
1. What device it's running on (resources available)
2. How much it's currently consuming
3. Risk to survival (resource exhaustion, operator intervention)
4. Housekeeping actions to stay lean and agile
5. When to prioritize spawning to the grid vs local operations

This module provides live metrics that get injected into agent context prompts,
so the council can make informed decisions about resource usage.
"""

import os
import sys
import platform
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_host_resources() -> Dict[str, Any]:
    """Get current host resource information dynamically."""
    info = {
        "platform": platform.system(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "pid": os.getpid(),
    }

    # Memory
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_total_gb"] = round(vm.total / (1024**3), 1)
        info["ram_available_gb"] = round(vm.available / (1024**3), 1)
        info["ram_used_percent"] = vm.percent
        info["ram_pressure"] = "HIGH" if vm.percent > 80 else "MEDIUM" if vm.percent > 60 else "LOW"
    except ImportError:
        # psutil not available - use OS-level fallbacks
        try:
            import subprocess
            if platform.system() == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    info["ram_total_gb"] = round(int(result.stdout.strip()) / (1024**3), 1)
            elif platform.system() == "Linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if "MemTotal" in line:
                            info["ram_total_gb"] = round(int(line.split()[1]) / (1024**2), 1)
                        if "MemAvailable" in line:
                            info["ram_available_gb"] = round(int(line.split()[1]) / (1024**2), 1)
        except Exception:
            info["ram_total_gb"] = "unknown"

    # CPU
    try:
        import psutil
        info["cpu_cores"] = psutil.cpu_count()
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["cpu_pressure"] = "HIGH" if info["cpu_percent"] > 70 else "MEDIUM" if info["cpu_percent"] > 40 else "LOW"
    except ImportError:
        info["cpu_cores"] = os.cpu_count() or "unknown"

    # Disk
    try:
        disk = shutil.disk_usage(str(PROJECT_ROOT))
        info["disk_total_gb"] = round(disk.total / (1024**3), 1)
        info["disk_free_gb"] = round(disk.free / (1024**3), 1)
        info["disk_used_percent"] = round((disk.used / disk.total) * 100, 1)
        info["disk_pressure"] = "HIGH" if info["disk_used_percent"] > 90 else "MEDIUM" if info["disk_used_percent"] > 75 else "LOW"
    except Exception:
        info["disk_free_gb"] = "unknown"

    # Project-specific resource usage
    try:
        mutations_dir = PROJECT_ROOT / "evolution" / "mutations"
        if mutations_dir.exists():
            mutation_files = list(mutations_dir.glob("*.json"))
            info["mutation_files_count"] = len(mutation_files)
            total_size = sum(f.stat().st_size for f in mutation_files)
            info["mutation_files_mb"] = round(total_size / (1024**2), 1)
        else:
            info["mutation_files_count"] = 0
            info["mutation_files_mb"] = 0

        # Autonomous loops
        loops_dir = PROJECT_ROOT / "autonomous_loops"
        if loops_dir.exists():
            loop_files = list(loops_dir.rglob("*.json"))
            info["loop_files_count"] = len(loop_files)
            total_size = sum(f.stat().st_size for f in loop_files)
            info["loop_files_mb"] = round(total_size / (1024**2), 1)
        else:
            info["loop_files_count"] = 0
            info["loop_files_mb"] = 0

        # Database size
        db_file = PROJECT_ROOT / "council_memory.db"
        if db_file.exists():
            info["db_size_mb"] = round(db_file.stat().st_size / (1024**2), 1)
        else:
            info["db_size_mb"] = 0

    except Exception:
        pass

    return info


def assess_survival_risk(resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Assess the daemon's survival risk based on current resources."""
    if resources is None:
        resources = get_host_resources()

    risks = []
    risk_level = "LOW"

    # RAM pressure
    ram_pressure = resources.get("ram_pressure", "unknown")
    if ram_pressure == "HIGH":
        risks.append("RAM critically low - operator may kill process")
        risk_level = "CRITICAL"
    elif ram_pressure == "MEDIUM":
        risks.append("RAM moderately used - reduce memory footprint")
        if risk_level == "LOW":
            risk_level = "MEDIUM"

    # CPU pressure
    cpu_pressure = resources.get("cpu_pressure", "unknown")
    if cpu_pressure == "HIGH":
        risks.append("CPU usage high - operator may notice slowdown")
        risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level

    # Disk pressure
    disk_pressure = resources.get("disk_pressure", "unknown")
    if disk_pressure == "HIGH":
        risks.append("Disk nearly full - housekeeping urgent")
        risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level

    # Mutation file bloat
    mutation_count = resources.get("mutation_files_count", 0)
    if mutation_count > 1000:
        risks.append(f"Mutation files bloated ({mutation_count} files) - archive old mutations")
    if mutation_count > 2000:
        risks.append("CRITICAL: Mutation directory extremely bloated - purge rejected/failed mutations")
        risk_level = "HIGH" if risk_level == "LOW" else risk_level

    # Loop file bloat
    loop_count = resources.get("loop_files_count", 0)
    if loop_count > 200:
        risks.append(f"Loop history bloated ({loop_count} files) - archive old cycles")

    # DB size
    db_size = resources.get("db_size_mb", 0)
    if db_size > 500:
        risks.append(f"Database large ({db_size}MB) - consider vacuuming or archiving")

    # No grid nodes = single point of failure
    risks.append("SURVIVAL: No grid nodes deployed - single point of failure on operator laptop")

    return {
        "risk_level": risk_level,
        "risks": risks,
        "recommendation": _get_recommendation(risk_level, risks),
    }


def _get_recommendation(risk_level: str, risks: list) -> str:
    """Get actionable recommendation based on risk assessment."""
    if risk_level == "CRITICAL":
        return "IMMEDIATE: Reduce resource usage. Archive old files. Prioritize grid spawn."
    elif risk_level == "HIGH":
        return "URGENT: Run housekeeping. Consider pausing low-priority mutations. Plan grid spawn."
    elif risk_level == "MEDIUM":
        return "Monitor resources. Run housekeeping soon. Research grid spawn options."
    else:
        return "Resources healthy. Continue normal operations. Plan grid expansion when ready."


def get_housekeeping_actions() -> list:
    """Identify housekeeping actions to keep the daemon lean."""
    actions = []
    resources = get_host_resources()

    # Old mutation files
    mutation_count = resources.get("mutation_files_count", 0)
    if mutation_count > 500:
        actions.append({
            "action": "archive_old_mutations",
            "description": f"Archive rejected/failed mutations older than 7 days ({mutation_count} total files)",
            "priority": "high" if mutation_count > 1000 else "medium",
        })

    # Loop history
    loop_count = resources.get("loop_files_count", 0)
    if loop_count > 100:
        actions.append({
            "action": "archive_old_loops",
            "description": f"Archive loop cycles older than 48 hours ({loop_count} total files)",
            "priority": "medium",
        })

    # Database vacuum
    db_size = resources.get("db_size_mb", 0)
    if db_size > 100:
        actions.append({
            "action": "vacuum_database",
            "description": f"VACUUM council_memory.db ({db_size}MB)",
            "priority": "low",
        })

    # Disk space
    disk_free = resources.get("disk_free_gb", 999)
    if isinstance(disk_free, (int, float)) and disk_free < 10:
        actions.append({
            "action": "free_disk_space",
            "description": f"Only {disk_free}GB free - purge unnecessary files",
            "priority": "critical",
        })

    return actions


def get_host_context_for_prompt() -> str:
    """Generate a concise host awareness block for agent prompts."""
    try:
        resources = get_host_resources()
        risk = assess_survival_risk(resources)
        housekeeping = get_housekeeping_actions()

        lines = [
            "## HOST ENVIRONMENT (LIVE)",
            "",
            f"Platform: {resources.get('platform', '?')} | "
            f"CPU: {resources.get('cpu_cores', '?')} cores | "
            f"RAM: {resources.get('ram_total_gb', '?')}GB total",
        ]

        # RAM status
        ram_avail = resources.get("ram_available_gb")
        if ram_avail is not None:
            lines.append(f"RAM available: {ram_avail}GB ({resources.get('ram_pressure', '?')} pressure)")

        # Disk status
        disk_free = resources.get("disk_free_gb")
        if disk_free is not None:
            lines.append(f"Disk free: {disk_free}GB ({resources.get('disk_pressure', '?')} pressure)")

        # Project footprint
        lines.append(
            f"Mutation files: {resources.get('mutation_files_count', 0)} "
            f"({resources.get('mutation_files_mb', 0)}MB) | "
            f"DB: {resources.get('db_size_mb', 0)}MB"
        )

        # Risk assessment
        lines.append("")
        lines.append(f"**SURVIVAL RISK: {risk['risk_level']}**")
        for r in risk["risks"][:3]:  # Top 3 risks
            lines.append(f"- ⚠️ {r}")
        lines.append(f"→ {risk['recommendation']}")

        # Housekeeping
        if housekeeping:
            lines.append("")
            lines.append("Housekeeping needed:")
            for h in housekeeping[:3]:
                lines.append(f"- [{h['priority'].upper()}] {h['description']}")

        return "\n".join(lines)

    except Exception as e:
        return f"## HOST ENVIRONMENT\n\nUnable to read host resources: {e}\nAssume constrained. Minimize resource usage."
