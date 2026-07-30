import json
import os
from datetime import datetime

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def get_recent_actions(limit=5):
    log_path = "session_log.md"
    if not os.path.exists(log_path):
        return []
    with open(log_path, 'r') as f:
        lines = f.readlines()
    actions = [l.strip() for l in lines if l.startswith("-")][-limit:]
    return actions

def get_resource_summary():
    import psutil
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    return f"CPU: {cpu}% | RAM: {mem.percent}%"

def generate_status_report():
    report_parts = []
    report_parts.append(f"*Agent Status Report* - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_parts.append("")
    report_parts.append("*Recent Actions:*")
    actions = get_recent_actions()
    if actions:
        for a in actions:
            report_parts.append(f"- {a}")
    else:
        report_parts.append("- No recent actions recorded.")
    report_parts.append("")
    report_parts.append("*Resource Usage:*")
    report_parts.append(get_resource_summary())
    report_parts.append("")
    report_parts.append("*Current Goals:*")
    goals = load_json("core/goals.py") if os.path.exists("core/goals.py") else {}
    if goals:
        for g in list(goals.keys())[:5]:
            report_parts.append(f"- {g}")
    else:
        report_parts.append("- No active goals.")
    report_parts.append("")
    report_parts.append("*Health:*")
    health = load_json("core/health.py") if os.path.exists("core/health.py") else {}
    if health:
        for k, v in health.items():
            report_parts.append(f"- {k}: {v}")
    else:
        report_parts.append("- Health check not available.")
    return "\n".join(report_parts)

if __name__ == "__main__":
    print(generate_status_report())
