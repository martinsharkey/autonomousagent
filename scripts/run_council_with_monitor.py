"""Run council monitor and an E2E goal in one shot."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.council_monitor import CouncilMonitor, start_background_monitor
from scripts.e2e_react_demo import main as run_e2e_demo


async def run_combined(duration: float = 60.0) -> None:
    monitor_thread = start_background_monitor(duration=duration)
    if monitor_thread is None:
        print("[MAIN] Monitor failed to start; running demo without monitor")
        await run_e2e_demo()
        return

    await run_e2e_demo()

    print("[MAIN] Waiting for monitor to flush session log...")
    time.sleep(2)

    sessions = sorted((Path("monitoring") / "council_logs").glob("monitor_session_*.json"))
    if sessions:
        latest = sessions[-1]
        with open(latest, "r", encoding="utf-8") as f:
            events = json.load(f)
        print(f"[MAIN] Monitor captured {len(events)} events")
        for event in events[-10:]:
            ts = event.get("timestamp", "")
            category = event.get("category", "unknown")
            source = event.get("source", "unknown")
            content = event.get("content", {})
            print(f"  [{ts}] [{category.upper():<14}] [{source.upper():<16}] {json.dumps(content, ensure_ascii=False, default=str)[:220]}")
    else:
        print("[MAIN] No monitor session logs found")


if __name__ == "__main__":
    asyncio.run(run_combined(duration=60.0))
