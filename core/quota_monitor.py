"""Track free-tier quota usage per provider."""

import json
import os
from datetime import datetime
from pathlib import Path


QUOTA_STATE_PATH = Path("core") / "quota_state.json"


class QuotaMonitor:
    def __init__(self) -> None:
        self.quota_state_path = QUOTA_STATE_PATH
        self.state = self._load_state()

    def _load_state(self) -> dict:
        try:
            with open(self.quota_state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            state = {
                "openrouter": {"daily_limit": 1000, "used_today": 0},
                "deepseek": {"daily_limit": 1000, "used_today": 0},
                "groq": {"daily_limit": 1000, "used_today": 0},
                "huggingface": {"daily_limit": 1000, "used_today": 0},
                "last_reset": datetime.utcnow().isoformat(),
            }
            try:
                import yaml
                with open("providers.yaml", "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                for provider in cfg.get("providers", []):
                    name = provider.get("name")
                    if name and name not in state:
                        state[name] = {"daily_limit": 1000, "used_today": 0}
            except Exception:
                pass
            return state

    def save_state(self) -> None:
        try:
            self.quota_state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.quota_state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as exc:
            print(f"[QUOTA] Failed to save state: {exc}")

    def maybe_reset_daily(self) -> None:
        last_reset = self.state.get("last_reset")
        if not last_reset:
            self.reset_daily()
            return
        try:
            last = datetime.fromisoformat(last_reset)
            now = datetime.utcnow()
            if last.date() != now.date():
                self.reset_daily()
        except Exception:
            self.reset_daily()

    def reset_daily(self) -> None:
        for provider in self.state:
            if provider == "last_reset":
                continue
            self.state[provider]["used_today"] = 0
        self.state["last_reset"] = datetime.utcnow().isoformat()
        self.save_state()

    def track_api_call(self, provider: str, calls: int = 1) -> None:
        self.maybe_reset_daily()
        if provider in self.state and provider != "last_reset":
            self.state[provider]["used_today"] += calls
            self.save_state()

    def get_available_quota(self, provider: str) -> int:
        self.maybe_reset_daily()
        if provider not in self.state or provider == "last_reset":
            return 0
        limit = self.state[provider].get("daily_limit", 0)
        used = self.state[provider].get("used_today", 0)
        return max(0, limit - used)

    def can_afford_mutation(self, provider: str, estimated_calls: int) -> bool:
        available = self.get_available_quota(provider)
        return estimated_calls <= max(available * 0.8, 0)

    def get_status(self) -> dict:
        self.maybe_reset_daily()
        status = {}
        for provider, data in self.state.items():
            if provider == "last_reset":
                continue
            limit = data.get("daily_limit", 0)
            used = data.get("used_today", 0)
            status[provider] = {
                "used": used,
                "limit": limit,
                "available": max(0, limit - used),
                "percent": round((used / limit) * 100, 1) if limit else 0.0,
            }
        return status


quota_monitor = QuotaMonitor()
