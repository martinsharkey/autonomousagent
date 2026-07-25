#!/usr/bin/env python3
"""
Autonomous Council Daemon
Runs the council in continuous autonomous mode with curiosity-driven exploration
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path

from core.agent_loop import start_council, stop_council, get_agent_loop
from core.telegram import get_telegram_bot
from governance.audit_log import log_event


class CouncilDaemon:
    def __init__(self, cycle_interval: int = 60):
        self.cycle_interval = cycle_interval
        self.running = False
        self.telegram = get_telegram_bot()
        self.start_time = None
    
    async def start(self):
        self.running = True
        self.start_time = datetime.utcnow()
        
        print("\n" + "="*80)
        print("AUTONOMOUS COUNCIL DAEMON - STARTING")
        print("="*80)
        print(f"Cycle Interval: {self.cycle_interval}s")
        print(f"Start Time: {self.start_time.isoformat()}")
        print("="*80 + "\n")
        
        await self.telegram.send_message(
            "<b>🚀 Autonomous Council Daemon Started</b>\n\n"
            f"<b>Cycle Interval:</b> {self.cycle_interval}s\n"
            f"<b>Start Time:</b> {self.start_time.isoformat()}\n\n"
            "The council is now running autonomously with:\n"
            "• Curiosity-driven exploration\n"
            "• Performance-based evolution\n"
            "• Continuous monitoring\n"
            "• Autonomous decision making"
        )
        
        log_event(
            "daemon_started",
            "system",
            "autonomous_operation",
            {"cycle_interval": self.cycle_interval}
        )
        
        try:
            await start_council(self.cycle_interval)
        except KeyboardInterrupt:
            print("\n\nShutdown signal received...")
            await self.stop()
        except Exception as e:
            print(f"\n\nError in daemon: {e}")
            await self.telegram.send_message(
                f"<b>❌ Council Daemon Error</b>\n\nError: {str(e)}"
            )
            await self.stop()
    
    async def stop(self):
        self.running = False
        
        print("\n" + "="*80)
        print("AUTONOMOUS COUNCIL DAEMON - STOPPING")
        print("="*80)
        
        await stop_council()
        
        runtime = datetime.utcnow() - self.start_time
        print(f"Total Runtime: {runtime}")
        print("="*80 + "\n")
        
        await self.telegram.send_message(
            "<b>⏹️ Autonomous Council Daemon Stopped</b>\n\n"
            f"<b>Runtime:</b> {str(runtime)}\n"
            f"<b>Stop Time:</b> {datetime.utcnow().isoformat()}"
        )
        
        log_event(
            "daemon_stopped",
            "system",
            "autonomous_operation",
            {"runtime_seconds": runtime.total_seconds()}
        )


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Council Daemon")
    parser.add_argument("--interval", type=int, default=60, help="Cycle interval in seconds")
    parser.add_argument("--test", action="store_true", help="Run test mode (3 cycles)")
    
    args = parser.parse_args()
    
    daemon = CouncilDaemon(args.interval)
    
    if args.test:
        print("\n[TEST MODE] Running 3 cycles only\n")
        
        agents = ["autobot", "alpha_evaluator", "beta_worker"]
        loops = [get_agent_loop(agent, args.interval) for agent in agents]
        
        for cycle in range(3):
            print(f"\n{'='*80}")
            print(f"TEST CYCLE {cycle + 1}/3")
            print(f"{'='*80}\n")
            
            for loop in loops:
                await loop.run_cycle()
            
            if cycle < 2:
                await asyncio.sleep(5)
        
        print("\n[TEST MODE] Complete\n")
        
        await daemon.telegram.send_message(
            "<b>✅ Council Test Mode Complete</b>\n\n"
            "Ran 3 test cycles successfully.\n"
            "All systems operational."
        )
    else:
        await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
