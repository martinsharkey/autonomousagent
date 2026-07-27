"""Timed council monitor for live testing.

Usage:
  python scripts/council_monitor.py --duration 180 --interval 1.0

Shows:
- reasoning_traces from graph state
- inter-agent messages
- goal executions
- mutations and votes
- trajectory entries
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.council_monitor import CouncilMonitor


def main() -> None:
    parser = argparse.ArgumentParser(description="Live council monitor")
    parser.add_argument("--duration", type=float, default=180.0, help="Monitor duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds")
    args = parser.parse_args()

    monitor = CouncilMonitor(poll_interval=args.interval, duration=args.duration)
    monitor.run()


if __name__ == "__main__":
    main()
