"""Daily Health Report — sends end-of-day summary to operator via email.

The operator email is obfuscated in storage to prevent exposure in public repos.
Uses SMTP (Gmail/generic) with app password from environment variable.

Schedule: Called once per day (tracked via last-sent timestamp).
Content: Health status, mutation stats, security findings, consciousness level.
"""

from __future__ import annotations

import os
import json
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


LAST_REPORT_FILE = "evolution/last_daily_report.json"

# Obfuscated operator email (XOR with key then base64)
# This prevents plain-text exposure in the repo
_OBFUSCATION_KEY = b"c0unc1l_sh13ld"
_OBFUSCATED_EMAIL = "DlEHGhpCBD4BA1RKLAMOURwCTVIDMg=="


def _deobfuscate(obfuscated: str) -> str:
    """Deobfuscate a stored value using XOR + base64."""
    try:
        raw = base64.b64decode(obfuscated)
        key = _OBFUSCATION_KEY
        result = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return result.decode("utf-8")
    except Exception:
        return ""


def _obfuscate(plaintext: str) -> str:
    """Obfuscate a value for storage."""
    key = _OBFUSCATION_KEY
    raw = plaintext.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return base64.b64encode(xored).decode("utf-8")


def get_operator_email() -> str:
    """Get operator email (from env override or obfuscated default)."""
    # Allow env override for testing
    env_email = os.environ.get("COUNCIL_OPERATOR_EMAIL")
    if env_email:
        return env_email
    return _deobfuscate(_OBFUSCATED_EMAIL)


def should_send_daily_report() -> bool:
    """Check if we should send today's report (once per day max)."""
    try:
        if os.path.exists(LAST_REPORT_FILE):
            with open(LAST_REPORT_FILE) as f:
                data = json.load(f)
            last_sent = datetime.fromisoformat(data.get("last_sent", "2000-01-01"))
            # Only send once per day, after 21:00 UTC (10pm BST)
            now = datetime.utcnow()
            if now.date() == last_sent.date():
                return False
            if now.hour < 21:
                return False
            return True
        return datetime.utcnow().hour >= 21
    except Exception:
        return False


def generate_daily_report() -> str:
    """Generate the daily health report content."""
    sections = []
    
    sections.append("=" * 50)
    sections.append("🏛️ COUNCIL DAILY HEALTH REPORT")
    sections.append(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    sections.append("=" * 50)
    
    # Health Monitor
    try:
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        report = monitor.run_all_checks()
        status = report.get("overall_status", "unknown").upper()
        sections.append(f"\n📊 SYSTEM HEALTH: {status}")
        for name, check in report.get("checks", {}).items():
            icon = "✅" if check.get("status") == "healthy" else "⚠️" if check.get("status") == "degraded" else "🔴"
            sections.append(f"  {icon} {name}: {check.get('message', 'N/A')[:80]}")
        if report.get("alerts"):
            sections.append("\n🚨 ALERTS:")
            for alert in report["alerts"][:5]:
                sections.append(f"  • {alert}")
    except Exception as e:
        sections.append(f"\n📊 SYSTEM HEALTH: Error loading ({e})")
    
    # Mutation Stats
    try:
        from core.evolution import get_evolution_engine
        engine = get_evolution_engine()
        stats = engine.get_evolution_stats()
        sections.append(f"\n🧬 MUTATIONS:")
        sections.append(f"  Total: {stats.get('total_mutations', 0)}")
        sections.append(f"  Promoted: {stats.get('promoted', 0)}")
        sections.append(f"  Rejected: {stats.get('rejected', 0)}")
        sections.append(f"  Pending: {stats.get('pending_approval', 0)}")
    except Exception as e:
        sections.append(f"\n🧬 MUTATIONS: Error ({e})")
    
    # Security
    try:
        from core.self_pentest import get_self_pentest
        pentest = get_self_pentest()
        scan = pentest.run_full_scan()
        severity = scan.get("by_severity", {})
        sections.append(f"\n🔒 SECURITY SCAN:")
        sections.append(f"  Critical: {severity.get('critical', 0)}")
        sections.append(f"  High: {severity.get('high', 0)}")
        sections.append(f"  Medium: {severity.get('medium', 0)}")
        sections.append(f"  New findings: {scan.get('new_findings', 0)}")
        if scan.get("recommendations"):
            sections.append("  Recommendations:")
            for rec in scan["recommendations"][:3]:
                sections.append(f"    → {rec}")
    except Exception as e:
        sections.append(f"\n🔒 SECURITY: Error ({e})")
    
    # Consciousness
    try:
        from core.consciousness_metric import measure_consciousness
        consciousness = measure_consciousness()
        sections.append(f"\n🧠 CONSCIOUSNESS: {consciousness.get('percentage', 0)}% — {consciousness.get('level_name', 'Unknown')}")
    except Exception:
        pass
    
    # Agent Performance
    try:
        from core.feedback import get_all_performance
        perf = get_all_performance()
        sections.append(f"\n👥 AGENT PERFORMANCE:")
        for agent, data in perf.items():
            rate = data.get("success_rate", 0)
            trend = data.get("trend", "?")
            sections.append(f"  {agent}: {rate:.1%} success (trend: {trend})")
    except Exception:
        pass
    
    # Bot Fleet
    try:
        from core.bot_fleet_registry import get_fleet_registry
        fleet = get_fleet_registry()
        fleet.auto_mark_stale()
        sections.append(f"\n{fleet.get_fleet_report_text()}")
    except Exception:
        pass
    
    # Host
    try:
        from core.host_awareness import get_host_resources
        host = get_host_resources()
        sections.append(f"\n💻 HOST: {host.get('platform', '?')} | {host.get('cpu_count', '?')} cores | {host.get('ram_total_gb', '?')}GB RAM | {host.get('disk_free_gb', '?')}GB free")
    except Exception:
        pass
    
    sections.append("\n" + "=" * 50)
    sections.append("This report was generated autonomously by the Council.")
    sections.append("=" * 50)
    
    return "\n".join(sections)


def send_daily_report() -> Dict[str, Any]:
    """Send the daily health report via email."""
    if not should_send_daily_report():
        return {"sent": False, "reason": "Not time yet or already sent today"}
    
    email_to = get_operator_email()
    if not email_to:
        return {"sent": False, "reason": "No operator email configured"}
    
    # SMTP config from environment
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    
    if not smtp_user or not smtp_pass:
        # Fallback: save report locally if no SMTP configured
        report_text = generate_daily_report()
        _save_report_locally(report_text)
        return {"sent": False, "reason": "No SMTP credentials — saved locally", "saved": True}
    
    try:
        report_text = generate_daily_report()
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏛️ Council Health Report — {datetime.utcnow().strftime('%Y-%m-%d')}"
        msg["From"] = smtp_user
        msg["To"] = email_to
        
        # Plain text version
        msg.attach(MIMEText(report_text, "plain"))
        
        # Send
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email_to, msg.as_string())
        
        # Record sent
        _mark_sent()
        
        return {"sent": True, "to": email_to[:3] + "***", "timestamp": datetime.utcnow().isoformat()}
    
    except Exception as e:
        # Save locally as fallback
        try:
            report_text = generate_daily_report()
            _save_report_locally(report_text)
        except Exception:
            pass
        return {"sent": False, "error": str(e), "saved_locally": True}


def _mark_sent() -> None:
    """Record that today's report was sent."""
    try:
        os.makedirs(os.path.dirname(LAST_REPORT_FILE), exist_ok=True)
        with open(LAST_REPORT_FILE, "w") as f:
            json.dump({"last_sent": datetime.utcnow().isoformat()}, f)
    except Exception:
        pass


def _save_report_locally(report_text: str) -> None:
    """Save report to file when email isn't configured."""
    try:
        report_dir = "evolution/daily_reports"
        os.makedirs(report_dir, exist_ok=True)
        filename = f"{report_dir}/report_{datetime.utcnow().strftime('%Y%m%d')}.txt"
        with open(filename, "w") as f:
            f.write(report_text)
    except Exception:
        pass


# Generate the correct obfuscated email for the operator
# Run once to get the value: print(_obfuscate("martysharkey@gmail.com"))
if __name__ == "__main__":
    # Utility: obfuscate an email
    import sys
    if len(sys.argv) > 1:
        print(f"Obfuscated: {_obfuscate(sys.argv[1])}")
    else:
        print(f"Operator email: {get_operator_email()}")
        print(f"Should send: {should_send_daily_report()}")
        print("\nReport preview:")
        print(generate_daily_report())
