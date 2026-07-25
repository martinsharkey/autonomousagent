"""
Health check CLI and endpoint for council monitoring.
Reports: running loops, last cycle time, curiosity/performance scores,
active mutations, graph checkpointer status.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from core.models import MODEL_REGISTRY
from core.checkpointer import get_checkpointer
from core.model_check import run_preflight


def get_loop_status() -> Dict[str, Any]:
    """Get status of agent loops."""
    loops_dir = Path("autonomous_loops")
    status = {}
    
    for agent_name in ["autobot", "alpha_evaluator", "beta_worker"]:
        agent_dir = loops_dir / agent_name
        if agent_dir.exists():
            cycle_files = sorted(agent_dir.glob("cycle_*.json"), reverse=True)
            if cycle_files:
                with open(cycle_files[0], "r") as f:
                    latest_cycle = json.load(f)
                status[agent_name] = {
                    "running": True,
                    "last_cycle": latest_cycle.get("timestamp"),
                    "cycle_count": latest_cycle.get("cycle", 0),
                    "performance": latest_cycle.get("performance", {}),
                    "curiosity_score": latest_cycle.get("curiosity_score", 0),
                    "duration_seconds": latest_cycle.get("duration_seconds", 0)
                }
            else:
                status[agent_name] = {"running": False, "last_cycle": None}
        else:
            status[agent_name] = {"running": False, "last_cycle": None}
    
    return status


def get_active_mutations() -> List[Dict]:
    """Get list of active mutations."""
    mutations_dir = Path("evolution/mutations")
    active = []
    
    if mutations_dir.exists():
        for mutation_file in mutations_dir.glob("mutation_*.json"):
            with open(mutation_file, "r") as f:
                mutation = json.load(f)
            if mutation.get("status") in ["proposed", "pending_approval", "approved"]:
                active.append(mutation)
    
    return active


def get_checkpointer_status() -> Dict[str, Any]:
    """Get checkpointer status."""
    try:
        checkpointer = get_checkpointer()
        threads = checkpointer.list_threads()
        return {
            "status": "operational",
            "db_path": str(checkpointer.db_path),
            "active_threads": len(threads),
            "threads": threads[:10]  # Show first 10
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_telegram_status() -> Dict[str, Any]:
    """Get Telegram configuration status."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    return {
        "configured": bool(bot_token and chat_id),
        "bot_token_set": bool(bot_token),
        "chat_id_set": bool(chat_id),
        "allowed_user_ids": os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
    }


def get_audit_log_status() -> Dict[str, Any]:
    """Get audit log status."""
    audit_dir = Path("audit_logs")
    if audit_dir.exists():
        log_files = list(audit_dir.glob("audit_*.log"))
        return {
            "status": "operational",
            "log_files": len(log_files),
            "latest_log": log_files[-1].name if log_files else None
        }
    return {"status": "not_found"}


def get_hmac_key_status() -> Dict[str, Any]:
    """Get HMAC key status."""
    keys_dir = Path(".keys")
    if keys_dir.exists():
        key_files = list(keys_dir.glob("*.key"))
        return {
            "status": "configured",
            "key_files": len(key_files),
            "keys": [f.name for f in key_files]
        }
    return {"status": "not_configured"}


def generate_health_report() -> Dict[str, Any]:
    """Generate comprehensive health report."""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "loops": get_loop_status(),
        "mutations": get_active_mutations(),
        "checkpointer": get_checkpointer_status(),
        "telegram": get_telegram_status(),
        "audit_log": get_audit_log_status(),
        "hmac_keys": get_hmac_key_status(),
        "models": {
            agent: {
                "primary": config["primary"],
                "fallback": config["fallback"],
                "purpose": config["purpose"]
            }
            for agent, config in MODEL_REGISTRY.items()
        }
    }
    
    return report


def print_health_report(report: Dict[str, Any]):
    """Print formatted health report."""
    print("\n" + "=" * 70)
    print("COUNCIL HEALTH CHECK")
    print("=" * 70)
    print(f"Timestamp: {report['timestamp']}\n")
    
    print("AGENT LOOPS:")
    for agent, status in report['loops'].items():
        running = "[OK]" if status['running'] else "[FAIL]"
        print(f"  [{running}] {agent}")
        if status['running']:
            print(f"      Last cycle: {status['last_cycle']}")
            perf = status.get('performance', {})
            if perf:
                print(f"      Success rate: {perf.get('success_rate', 0):.2f}")
                print(f"      Curiosity: {status.get('curiosity_score', 0):.2f}")
    
    print(f"\nACTIVE MUTATIONS: {len(report['mutations'])}")
    for mutation in report['mutations'][:5]:
        print(f"  - {mutation['mutation_id'][:12]}... ({mutation['status']})")
    
    print(f"\nCHECKPOINTER: {report['checkpointer']['status']}")
    if report['checkpointer']['status'] == 'operational':
        print(f"  Active threads: {report['checkpointer']['active_threads']}")
    
    print(f"\nTELEGRAM: {'[OK] Configured' if report['telegram']['configured'] else '[FAIL] Not configured'}")
    
    print(f"\nAUDIT LOG: {report['audit_log']['status']}")
    
    print(f"\nHMAC KEYS: {report['hmac_keys']['status']}")
    
    print("=" * 70 + "\n")


def main():
    """Main entry point for health check."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Council health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--preflight", action="store_true", help="Include preflight check")
    
    args = parser.parse_args()
    
    report = generate_health_report()
    
    if args.preflight:
        print("\nRunning preflight check...")
        preflight = run_preflight()
        report['preflight'] = preflight
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_health_report(report)
        
        if args.preflight and 'preflight' in report:
            from core.model_check import print_report
            print_report(report['preflight'])


if __name__ == "__main__":
    main()
