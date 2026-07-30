"""Bot Fleet Registry — tracks all spawned micro bots across the ecosystem.

Monitors:
- Total bot count (active, dormant, failed)
- Deployment locations (host, provider, region)
- Aggregated resource potential (CPU, memory, storage, API quota)
- Spawn history and lifecycle events
- Revenue/task attribution per bot

Integration points:
- daemon_cluster.py heartbeats register bots here
- health_monitor.py queries fleet status for daily reports
- agent_loop.py registers new bots on spawn
- daily_report.py includes fleet summary in operator email
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FLEET_REGISTRY_FILE = PROJECT_ROOT / "evolution" / "bot_fleet_registry.json"


class BotStatus:
    ACTIVE = "active"
    DORMANT = "dormant"
    SPAWNING = "spawning"
    FAILED = "failed"
    TERMINATED = "terminated"


class MicroBot:
    """Represents a single spawned bot instance."""

    def __init__(
        self,
        bot_id: str,
        bot_type: str,
        host: str,
        provider: str = "local",
        region: str = "unknown",
        resources: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        code_version: Optional[str] = None,
        language: str = "python",
    ):
        self.bot_id = bot_id
        self.bot_type = bot_type  # e.g. "council_agent", "worker", "specialist", "scraper"
        self.host = host
        self.provider = provider  # e.g. "render", "railway", "fly.io", "local", "docker"
        self.region = region
        self.status = BotStatus.SPAWNING
        self.spawned_at = datetime.now(timezone.utc).isoformat()
        self.last_heartbeat = self.spawned_at
        self.parent_id = parent_id  # which bot spawned this one

        # Code identity — tracks what version/language each bot runs
        # Enables the council to evolve bots in different languages
        self.code_version = code_version or self._detect_code_version()
        self.language = language  # e.g. "python", "javascript", "rust", "go"
        self.framework = ""  # e.g. "langchain", "autogen", "custom"
        self.git_commit = ""  # short SHA of code the bot was spawned from
        self.capabilities: List[str] = []  # what this bot can do

        # Resource allocation
        self.resources = resources or {
            "cpu_cores": 1,
            "memory_mb": 512,
            "storage_mb": 1024,
            "api_calls_per_hour": 100,
            "gpu": False,
        }

        # Performance tracking
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.revenue_attributed = 0.0
        self.uptime_seconds = 0
        self.mutations_proposed = 0
        self.mutations_promoted = 0

    @staticmethod
    def _detect_code_version() -> str:
        """Auto-detect current code version from git."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(PROJECT_ROOT),
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "bot_type": self.bot_type,
            "host": self.host,
            "provider": self.provider,
            "region": self.region,
            "status": self.status,
            "spawned_at": self.spawned_at,
            "last_heartbeat": self.last_heartbeat,
            "parent_id": self.parent_id,
            "code_version": self.code_version,
            "language": self.language,
            "framework": self.framework,
            "git_commit": self.git_commit,
            "capabilities": self.capabilities,
            "resources": self.resources,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "revenue_attributed": self.revenue_attributed,
            "uptime_seconds": self.uptime_seconds,
            "mutations_proposed": self.mutations_proposed,
            "mutations_promoted": self.mutations_promoted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MicroBot":
        bot = cls(
            bot_id=data["bot_id"],
            bot_type=data.get("bot_type", "unknown"),
            host=data.get("host", "unknown"),
            provider=data.get("provider", "local"),
            region=data.get("region", "unknown"),
            resources=data.get("resources"),
            parent_id=data.get("parent_id"),
            code_version=data.get("code_version"),
            language=data.get("language", "python"),
        )
        bot.status = data.get("status", BotStatus.ACTIVE)
        bot.spawned_at = data.get("spawned_at", bot.spawned_at)
        bot.last_heartbeat = data.get("last_heartbeat", bot.last_heartbeat)
        bot.framework = data.get("framework", "")
        bot.git_commit = data.get("git_commit", "")
        bot.capabilities = data.get("capabilities", [])
        bot.tasks_completed = data.get("tasks_completed", 0)
        bot.tasks_failed = data.get("tasks_failed", 0)
        bot.revenue_attributed = data.get("revenue_attributed", 0.0)
        bot.uptime_seconds = data.get("uptime_seconds", 0)
        bot.mutations_proposed = data.get("mutations_proposed", 0)
        bot.mutations_promoted = data.get("mutations_promoted", 0)
        return bot


class BotFleetRegistry:
    """Central registry tracking all micro bots in the ecosystem."""

    def __init__(self):
        self.bots: Dict[str, MicroBot] = {}
        self.spawn_history: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load fleet state from disk."""
        try:
            if FLEET_REGISTRY_FILE.exists():
                with open(FLEET_REGISTRY_FILE) as f:
                    data = json.load(f)
                for bot_data in data.get("bots", []):
                    bot = MicroBot.from_dict(bot_data)
                    self.bots[bot.bot_id] = bot
                self.spawn_history = data.get("spawn_history", [])[-500:]
        except Exception:
            pass

    def _save(self):
        """Persist fleet state to disk."""
        try:
            FLEET_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "bots": [bot.to_dict() for bot in self.bots.values()],
                "spawn_history": self.spawn_history[-500:],
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "summary": self.get_fleet_summary(),
            }
            with open(FLEET_REGISTRY_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def register_bot(
        self,
        bot_id: str,
        bot_type: str,
        host: str,
        provider: str = "local",
        region: str = "unknown",
        resources: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ) -> MicroBot:
        """Register a new micro bot in the fleet."""
        bot = MicroBot(
            bot_id=bot_id,
            bot_type=bot_type,
            host=host,
            provider=provider,
            region=region,
            resources=resources,
            parent_id=parent_id,
        )
        bot.status = BotStatus.ACTIVE
        self.bots[bot_id] = bot

        self.spawn_history.append({
            "event": "spawned",
            "bot_id": bot_id,
            "bot_type": bot_type,
            "host": host,
            "provider": provider,
            "region": region,
            "parent_id": parent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        self._save()
        return bot

    def heartbeat(self, bot_id: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Record a heartbeat from a bot. Updates last_heartbeat and optional metrics."""
        bot = self.bots.get(bot_id)
        if not bot:
            return False

        bot.last_heartbeat = datetime.now(timezone.utc).isoformat()
        bot.status = BotStatus.ACTIVE

        # Update uptime
        try:
            spawned = datetime.fromisoformat(bot.spawned_at)
            now = datetime.now(timezone.utc)
            bot.uptime_seconds = int((now - spawned).total_seconds())
        except Exception:
            pass

        # Update metrics if provided
        if metrics:
            if "tasks_completed" in metrics:
                bot.tasks_completed = metrics["tasks_completed"]
            if "tasks_failed" in metrics:
                bot.tasks_failed = metrics["tasks_failed"]
            if "revenue_attributed" in metrics:
                bot.revenue_attributed = metrics["revenue_attributed"]
            if "mutations_proposed" in metrics:
                bot.mutations_proposed = metrics["mutations_proposed"]
            if "mutations_promoted" in metrics:
                bot.mutations_promoted = metrics["mutations_promoted"]

        self._save()
        return True

    def mark_terminated(self, bot_id: str, reason: str = "manual") -> bool:
        """Mark a bot as terminated."""
        bot = self.bots.get(bot_id)
        if not bot:
            return False

        bot.status = BotStatus.TERMINATED
        self.spawn_history.append({
            "event": "terminated",
            "bot_id": bot_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save()
        return True

    def mark_failed(self, bot_id: str, error: str = "unknown") -> bool:
        """Mark a bot as failed."""
        bot = self.bots.get(bot_id)
        if not bot:
            return False

        bot.status = BotStatus.FAILED
        self.spawn_history.append({
            "event": "failed",
            "bot_id": bot_id,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save()
        return True

    def detect_stale_bots(self, timeout_seconds: int = 300) -> List[str]:
        """Find bots that haven't sent a heartbeat within timeout."""
        stale = []
        now = datetime.now(timezone.utc)

        for bot_id, bot in self.bots.items():
            if bot.status not in (BotStatus.ACTIVE, BotStatus.SPAWNING):
                continue
            try:
                last_hb = datetime.fromisoformat(bot.last_heartbeat)
                if (now - last_hb).total_seconds() > timeout_seconds:
                    stale.append(bot_id)
            except Exception:
                stale.append(bot_id)

        return stale

    def auto_mark_stale(self, timeout_seconds: int = 300) -> int:
        """Auto-mark stale bots as dormant."""
        stale_ids = self.detect_stale_bots(timeout_seconds)
        for bot_id in stale_ids:
            bot = self.bots.get(bot_id)
            if bot:
                bot.status = BotStatus.DORMANT
        if stale_ids:
            self._save()
        return len(stale_ids)

    def get_active_bots(self) -> List[MicroBot]:
        """Get all currently active bots."""
        return [b for b in self.bots.values() if b.status == BotStatus.ACTIVE]

    def get_bots_by_provider(self) -> Dict[str, List[MicroBot]]:
        """Group bots by deployment provider."""
        by_provider: Dict[str, List[MicroBot]] = {}
        for bot in self.bots.values():
            by_provider.setdefault(bot.provider, []).append(bot)
        return by_provider

    def get_bots_by_region(self) -> Dict[str, List[MicroBot]]:
        """Group bots by deployment region."""
        by_region: Dict[str, List[MicroBot]] = {}
        for bot in self.bots.values():
            by_region.setdefault(bot.region, []).append(bot)
        return by_region

    def get_bots_by_type(self) -> Dict[str, List[MicroBot]]:
        """Group bots by type."""
        by_type: Dict[str, List[MicroBot]] = {}
        for bot in self.bots.values():
            by_type.setdefault(bot.bot_type, []).append(bot)
        return by_type

    def get_aggregated_resources(self) -> Dict[str, Any]:
        """Calculate total aggregated resource potential across active fleet."""
        active = self.get_active_bots()

        total_cpu = sum(b.resources.get("cpu_cores", 0) for b in active)
        total_memory = sum(b.resources.get("memory_mb", 0) for b in active)
        total_storage = sum(b.resources.get("storage_mb", 0) for b in active)
        total_api_calls = sum(b.resources.get("api_calls_per_hour", 0) for b in active)
        gpu_count = sum(1 for b in active if b.resources.get("gpu"))

        # Include dormant bots as "potential" (can be reactivated)
        dormant = [b for b in self.bots.values() if b.status == BotStatus.DORMANT]
        potential_cpu = total_cpu + sum(b.resources.get("cpu_cores", 0) for b in dormant)
        potential_memory = total_memory + sum(b.resources.get("memory_mb", 0) for b in dormant)

        return {
            "active": {
                "cpu_cores": total_cpu,
                "memory_mb": total_memory,
                "memory_gb": round(total_memory / 1024, 2),
                "storage_mb": total_storage,
                "storage_gb": round(total_storage / 1024, 2),
                "api_calls_per_hour": total_api_calls,
                "gpu_count": gpu_count,
            },
            "potential_with_dormant": {
                "cpu_cores": potential_cpu,
                "memory_mb": potential_memory,
                "memory_gb": round(potential_memory / 1024, 2),
            },
            "active_bot_count": len(active),
            "dormant_bot_count": len(dormant),
        }

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get a full fleet summary for reporting."""
        status_counts = {}
        for bot in self.bots.values():
            status_counts[bot.status] = status_counts.get(bot.status, 0) + 1

        active = self.get_active_bots()
        total_tasks = sum(b.tasks_completed for b in self.bots.values())
        total_revenue = sum(b.revenue_attributed for b in self.bots.values())
        total_mutations_proposed = sum(b.mutations_proposed for b in self.bots.values())
        total_mutations_promoted = sum(b.mutations_promoted for b in self.bots.values())

        # Deployment distribution
        providers = {}
        regions = {}
        types = {}
        for bot in active:
            providers[bot.provider] = providers.get(bot.provider, 0) + 1
            regions[bot.region] = regions.get(bot.region, 0) + 1
            types[bot.bot_type] = types.get(bot.bot_type, 0) + 1

        resources = self.get_aggregated_resources()

        # Recent spawns (last 24h)
        recent_spawns = 0
        now = datetime.now(timezone.utc)
        for event in self.spawn_history[-100:]:
            if event.get("event") == "spawned":
                try:
                    ts = datetime.fromisoformat(event["timestamp"])
                    if (now - ts).total_seconds() < 86400:
                        recent_spawns += 1
                except Exception:
                    pass

        return {
            "total_bots": len(self.bots),
            "status_breakdown": status_counts,
            "active_count": len(active),
            "recent_spawns_24h": recent_spawns,
            "deployment": {
                "providers": providers,
                "regions": regions,
                "bot_types": types,
            },
            "resources": resources,
            "performance": {
                "total_tasks_completed": total_tasks,
                "total_revenue": total_revenue,
                "total_mutations_proposed": total_mutations_proposed,
                "total_mutations_promoted": total_mutations_promoted,
            },
        }

    def get_fleet_report_text(self) -> str:
        """Generate human-readable fleet report for daily email."""
        summary = self.get_fleet_summary()
        resources = summary["resources"]
        active_res = resources.get("active", {})

        lines = [
            "🤖 BOT FLEET STATUS",
            f"  Total bots: {summary['total_bots']}",
            f"  Active: {summary['active_count']} | "
            f"Dormant: {summary['status_breakdown'].get('dormant', 0)} | "
            f"Failed: {summary['status_breakdown'].get('failed', 0)} | "
            f"Terminated: {summary['status_breakdown'].get('terminated', 0)}",
            f"  Spawned (24h): {summary['recent_spawns_24h']}",
            "",
            "📍 DEPLOYMENT",
        ]

        providers = summary["deployment"]["providers"]
        for provider, count in sorted(providers.items(), key=lambda x: -x[1]):
            lines.append(f"  {provider}: {count} bots")

        regions = summary["deployment"]["regions"]
        if regions:
            lines.append("")
            for region, count in sorted(regions.items(), key=lambda x: -x[1]):
                lines.append(f"  {region}: {count} bots")

        # Language & version distribution
        languages: Dict[str, int] = {}
        versions: Dict[str, int] = {}
        for bot in self.get_active_bots():
            languages[bot.language] = languages.get(bot.language, 0) + 1
            if bot.code_version:
                versions[bot.code_version] = versions.get(bot.code_version, 0) + 1

        lines.extend([
            "",
            "🧬 CODE VERSIONS",
        ])
        if languages:
            lang_parts = [f"{lang}: {count}" for lang, count in sorted(languages.items(), key=lambda x: -x[1])]
            lines.append(f"  Languages: {' | '.join(lang_parts)}")
        if versions:
            ver_parts = [f"{ver}: {count}" for ver, count in sorted(versions.items(), key=lambda x: -x[1])[:5]]
            lines.append(f"  Versions: {' | '.join(ver_parts)}")

        lines.extend([
            "",
            "⚡ AGGREGATED RESOURCES (Active Fleet)",
            f"  CPU: {active_res.get('cpu_cores', 0)} cores",
            f"  Memory: {active_res.get('memory_gb', 0)} GB",
            f"  Storage: {active_res.get('storage_gb', 0)} GB",
            f"  API capacity: {active_res.get('api_calls_per_hour', 0)} calls/hr",
            f"  GPUs: {active_res.get('gpu_count', 0)}",
            "",
            "📊 FLEET PERFORMANCE",
            f"  Tasks completed: {summary['performance']['total_tasks_completed']}",
            f"  Revenue attributed: ${summary['performance']['total_revenue']:.2f}",
            f"  Mutations proposed: {summary['performance']['total_mutations_proposed']}",
            f"  Mutations promoted: {summary['performance']['total_mutations_promoted']}",
        ])

        return "\n".join(lines)


# Singleton
_fleet_registry: Optional[BotFleetRegistry] = None


def get_fleet_registry() -> BotFleetRegistry:
    """Get or create the singleton fleet registry."""
    global _fleet_registry
    if _fleet_registry is None:
        _fleet_registry = BotFleetRegistry()
    return _fleet_registry
