"""Live system health monitoring and observational layer.

Provides real-time health checks, service status, performance metrics,
and alerting for the council daemon. Runs non-intrusively alongside
the main loop and reports anomalies via Telegram.

Checks:
- Process health (memory, CPU, file descriptors)
- API connectivity (OpenRouter, GitHub, Telegram)
- Database integrity (goals.db, mutations, checkpoints)
- Loop cadence (detecting stalls or runaway cycles)
- Disk pressure and cleanup triggers
"""

from __future__ import annotations

import os
import time
import json
import glob
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


HEALTH_LOG_FILE = "evolution/health_log.json"
ALERT_COOLDOWN_SECONDS = 1800  # Don't spam alerts more than every 30min
MAX_LOG_ENTRIES = 200


class HealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class HealthMonitor:
    """Continuous health monitoring for the council daemon."""

    def __init__(self):
        self._last_alert_time: Dict[str, float] = {}
        self._check_history: List[Dict[str, Any]] = []

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return consolidated report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "overall_status": HealthStatus.HEALTHY,
            "alerts": [],
        }

        checks = [
            ("process", self._check_process_health),
            ("disk", self._check_disk_pressure),
            ("database", self._check_database_integrity),
            ("loop_cadence", self._check_loop_cadence),
            ("api_connectivity", self._check_api_keys),
            ("mutation_pipeline", self._check_mutation_pipeline),
        ]

        for name, check_fn in checks:
            try:
                result = check_fn()
                report["checks"][name] = result
                if result.get("status") == HealthStatus.CRITICAL:
                    report["overall_status"] = HealthStatus.CRITICAL
                    report["alerts"].append(f"CRITICAL: {name} - {result.get('message', 'unknown')}")
                elif result.get("status") == HealthStatus.DEGRADED and report["overall_status"] != HealthStatus.CRITICAL:
                    report["overall_status"] = HealthStatus.DEGRADED
            except Exception as e:
                report["checks"][name] = {"status": HealthStatus.DEGRADED, "error": str(e)}

        self._save_report(report)
        return report

    def _check_process_health(self) -> Dict[str, Any]:
        """Check memory usage, open file descriptors."""
        import resource
        
        usage = resource.getrusage(resource.RUSAGE_SELF)
        max_rss_mb = usage.ru_maxrss / (1024 * 1024) if os.name != "nt" else usage.ru_maxrss / 1024
        
        # Check open file descriptors (Unix)
        fd_count = 0
        try:
            fd_count = len(os.listdir(f"/proc/{os.getpid()}/fd"))
        except (FileNotFoundError, PermissionError):
            # macOS fallback
            try:
                result = subprocess.run(
                    ["lsof", "-p", str(os.getpid())],
                    capture_output=True, text=True, timeout=5
                )
                fd_count = len(result.stdout.strip().split("\n")) - 1
            except Exception:
                fd_count = -1  # Unknown

        status = HealthStatus.HEALTHY
        message = f"RSS: {max_rss_mb:.1f}MB, FDs: {fd_count}"
        
        if max_rss_mb > 1024:  # >1GB
            status = HealthStatus.CRITICAL
            message = f"Memory critical: {max_rss_mb:.0f}MB"
        elif max_rss_mb > 512:
            status = HealthStatus.DEGRADED
            message = f"Memory elevated: {max_rss_mb:.0f}MB"
        
        if fd_count > 500:
            status = HealthStatus.CRITICAL
            message += f" | FD leak: {fd_count}"

        return {"status": status, "message": message, "rss_mb": max_rss_mb, "fd_count": fd_count}

    def _check_disk_pressure(self) -> Dict[str, Any]:
        """Check available disk space."""
        import shutil
        
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024**3)
        used_pct = (used / total) * 100
        
        # Count mutation files (growth indicator)
        mutation_count = len(glob.glob("evolution/mutations/mutation_*.json"))
        loop_count = len(glob.glob("autonomous_loops/*/*.json"))
        
        status = HealthStatus.HEALTHY
        message = f"{free_gb:.1f}GB free ({used_pct:.0f}% used), {mutation_count} mutations, {loop_count} loop files"
        
        if free_gb < 1:
            status = HealthStatus.CRITICAL
            message = f"DISK CRITICAL: Only {free_gb:.2f}GB free!"
        elif free_gb < 5:
            status = HealthStatus.DEGRADED
            message = f"Disk low: {free_gb:.1f}GB free"
        
        # Warn about unbounded growth
        if loop_count > 5000:
            status = max(status, HealthStatus.DEGRADED)
            message += f" | Loop files growing: {loop_count}"

        return {
            "status": status, "message": message,
            "free_gb": round(free_gb, 2), "used_pct": round(used_pct, 1),
            "mutation_files": mutation_count, "loop_files": loop_count,
        }

    def _check_database_integrity(self) -> Dict[str, Any]:
        """Verify SQLite databases are not corrupt."""
        db_paths = [
            "goals/goals.db",
            "data/checkpoints/state.db",
        ]
        
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for db_path in db_paths:
            if not os.path.exists(db_path):
                results[db_path] = "missing"
                continue
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                check = cursor.fetchone()
                conn.close()
                if check and check[0] == "ok":
                    results[db_path] = "ok"
                else:
                    results[db_path] = f"CORRUPT: {check}"
                    overall_status = HealthStatus.CRITICAL
            except Exception as e:
                results[db_path] = f"error: {str(e)[:80]}"
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status,
            "message": f"DBs: {results}",
            "databases": results,
        }

    def _check_loop_cadence(self) -> Dict[str, Any]:
        """Detect if agent loops have stalled or are running too fast."""
        agents = ["autobot", "alpha_evaluator", "beta_worker"]
        stalled = []
        runaway = []
        
        for agent in agents:
            loop_dir = f"autonomous_loops/{agent}"
            if not os.path.isdir(loop_dir):
                stalled.append(agent)
                continue
            
            files = sorted(glob.glob(f"{loop_dir}/cycle_*.json"), key=os.path.getmtime, reverse=True)
            if not files:
                stalled.append(agent)
                continue
            
            latest_mtime = os.path.getmtime(files[0])
            age_minutes = (time.time() - latest_mtime) / 60
            
            if age_minutes > 30:
                stalled.append(agent)
            elif len(files) > 5:
                # Check if last 5 cycles were within 1 minute (runaway)
                recent_5_ages = [os.path.getmtime(f) for f in files[:5]]
                span = recent_5_ages[0] - recent_5_ages[-1]
                if span < 10:  # 5 cycles in <10 seconds
                    runaway.append(agent)

        status = HealthStatus.HEALTHY
        message = "All loops active"
        
        if stalled:
            status = HealthStatus.DEGRADED
            message = f"Stalled: {', '.join(stalled)}"
        if runaway:
            status = HealthStatus.CRITICAL
            message += f" | Runaway: {', '.join(runaway)}"

        return {"status": status, "message": message, "stalled": stalled, "runaway": runaway}

    def _check_api_keys(self) -> Dict[str, Any]:
        """Verify API keys are configured (not connectivity test — that costs money)."""
        keys_to_check = {
            "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
            "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", ""),
            "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        }
        
        missing = [k for k, v in keys_to_check.items() if not v]
        
        if not missing:
            return {"status": HealthStatus.HEALTHY, "message": "All API keys present"}
        elif "OPENROUTER_API_KEY" in missing:
            return {"status": HealthStatus.CRITICAL, "message": f"Missing: {', '.join(missing)}"}
        else:
            return {"status": HealthStatus.DEGRADED, "message": f"Missing: {', '.join(missing)}"}

    def _check_mutation_pipeline(self) -> Dict[str, Any]:
        """Check mutation pipeline health — are mutations flowing through?"""
        mutation_dir = "evolution/mutations"
        if not os.path.isdir(mutation_dir):
            return {"status": HealthStatus.DEGRADED, "message": "No mutation directory"}
        
        files = sorted(glob.glob(f"{mutation_dir}/mutation_*.json"), key=os.path.getmtime, reverse=True)
        if not files:
            return {"status": HealthStatus.DEGRADED, "message": "No mutations found"}
        
        # Check last 20 mutations for status distribution
        status_counts: Dict[str, int] = {}
        for f in files[:20]:
            try:
                with open(f) as fh:
                    m = json.load(fh)
                s = m.get("status", "unknown")
                status_counts[s] = status_counts.get(s, 0) + 1
            except Exception:
                continue
        
        # Check age of newest mutation
        newest_age_hours = (time.time() - os.path.getmtime(files[0])) / 3600
        
        status = HealthStatus.HEALTHY
        message = f"Pipeline active. Last mutation {newest_age_hours:.1f}h ago. Recent: {status_counts}"
        
        if newest_age_hours > 24:
            status = HealthStatus.DEGRADED
            message = f"Pipeline stalled: no mutations in {newest_age_hours:.0f}h"
        
        # If all recent mutations are rejected/failed, that's concerning
        bad_count = status_counts.get("rejected", 0) + status_counts.get("failed", 0)
        if bad_count >= 15:
            status = HealthStatus.DEGRADED
            message += f" | {bad_count}/20 recent mutations rejected/failed"

        return {"status": status, "message": message, "status_distribution": status_counts}

    def _save_report(self, report: Dict[str, Any]) -> None:
        """Persist health report to log file (rolling)."""
        try:
            existing = []
            if os.path.exists(HEALTH_LOG_FILE):
                with open(HEALTH_LOG_FILE) as f:
                    existing = json.load(f)
            
            existing.append(report)
            if len(existing) > MAX_LOG_ENTRIES:
                existing = existing[-MAX_LOG_ENTRIES:]
            
            os.makedirs(os.path.dirname(HEALTH_LOG_FILE), exist_ok=True)
            with open(HEALTH_LOG_FILE, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass

    def should_alert(self, alert_key: str) -> bool:
        """Rate-limit alerts to prevent spam."""
        now = time.time()
        last = self._last_alert_time.get(alert_key, 0)
        if now - last > ALERT_COOLDOWN_SECONDS:
            self._last_alert_time[alert_key] = now
            return True
        return False

    def get_summary_for_prompt(self) -> str:
        """One-line health summary for agent context injection."""
        report = self.run_all_checks()
        status = report["overall_status"].upper()
        alerts = report["alerts"]
        
        disk = report["checks"].get("disk", {})
        loop = report["checks"].get("loop_cadence", {})
        pipeline = report["checks"].get("mutation_pipeline", {})
        
        summary = f"HEALTH: {status}"
        if alerts:
            summary += f" | ALERTS: {'; '.join(alerts[:3])}"
        summary += f" | Disk: {disk.get('free_gb', '?')}GB free"
        summary += f" | Loops: {loop.get('message', '?')}"
        summary += f" | Pipeline: {pipeline.get('message', '?')[:60]}"
        
        return summary


# Singleton
_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


def get_health_summary() -> str:
    """Quick health summary for prompts/Telegram."""
    return get_health_monitor().get_summary_for_prompt()
