#!/usr/bin/env python3
"""
Autonomous Council Daemon - Primary Entry Point
Runs the council in continuous autonomous mode with:
- Goal-driven execution
- Curiosity-driven exploration
- Performance-based evolution
- Telegram command interface
"""

import asyncio
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from core.agent_loop import start_council, stop_council, get_agent_loop
from core.telegram import get_telegram_bot, get_command_listener, send_council_message
from core.goals import get_goal_store, GoalStatus
from core.model_check import run_preflight, print_report
from core.health import generate_health_report
from core.autonomy_levels import get_autonomy_controller, AutonomyLevel
from governance.audit_log import log_event
from core.evolution import get_evolution_engine
try:
    from core.auto_update import AutoUpdateLoop, get_version_info
except Exception as _auto_update_err:
    print(f'[DAEMON] Warning: auto_update import failed: {_auto_update_err}')
    AutoUpdateLoop = None
    get_version_info = None


class CouncilDaemon:
    def __init__(self, cycle_interval: int = 60, autonomy_level: str = "limited"):
        self.cycle_interval = cycle_interval
        self.running = False
        self.telegram = get_telegram_bot()
        self.command_listener = get_command_listener()
        self.goal_store = get_goal_store()
        self.autonomy_controller = get_autonomy_controller()
        self.start_time = None
        self.autonomy_paused = False
        self.pid_file = Path(__file__).resolve().parent / ".council_daemon.pid"
        
        # Set autonomy level
        level_map = {
            "safe": AutonomyLevel.SAFE,
            "limited": AutonomyLevel.LIMITED,
            "full": AutonomyLevel.FULL
        }
        self.autonomy_controller.set_level(level_map.get(autonomy_level, AutonomyLevel.LIMITED))
        
        # Wire command listener callbacks to real systems
        self._setup_command_handlers()
        
        # Resume open goals on startup
        self._resume_open_goals()
    
    def _setup_command_handlers(self):
        """Wire Telegram command handlers to real goal store and evolution engine."""
        self.command_listener.on_create_goal = self._create_goal_handler
        self.command_listener.on_get_status = self._get_status_handler
        self.command_listener.on_approve_mutation = self._approve_mutation_handler
        self.command_listener.on_reject_mutation = self._reject_mutation_handler
        self.command_listener.on_stop_autonomy = self._stop_autonomy_handler
    
    def _resume_open_goals(self):
        """Resume any open goals from previous session."""
        open_goals = self.goal_store.get_open_goals()
        if open_goals:
            print(f"[DAEMON] Resuming {len(open_goals)} open goals from previous session")
            for goal in open_goals[:5]:  # Resume up to 5 goals
                print(f"  • {goal['goal_id'][:12]}...: {goal['description'][:50]}")
    
    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Check if a process with given PID is running."""
        if not pid or pid <= 0:
            return False
        try:
            # On Unix, check /proc
            if hasattr(os, 'kill'):
                os.kill(pid, 0)
                return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            pass
        try:
            # On Windows, use tasklist
            import subprocess
            result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
            return str(pid) in result.stdout
        except Exception:
            return False
    
    async def _create_goal_handler(self, description: str, source: str = "human") -> str:
        """Create a real goal and return goal_id."""
        goal_id = self.goal_store.create_goal(description, source=source, priority=10 if source == "human" else 5)
        return goal_id
    
    async def _get_status_handler(self) -> str:
        """Get current status summary."""
        goal_summary = self.goal_store.get_status_summary()
        autonomy_status = self.autonomy_controller.get_status()
        
        from core.evolution import get_evolution_engine
        engine = get_evolution_engine()
        pending = engine.get_pending_approvals()
        pending_text = ""
        if pending:
            for m in pending[:5]:
                changes = m.proposed_changes or {}
                summary_parts = []
                file_changes = changes.get("file_changes")
                if isinstance(file_changes, list):
                    for fc in file_changes[:2]:
                        if isinstance(fc, dict):
                            summary_parts.append(f"{fc.get('kind', '?')} {fc.get('path', '?')}")
                if not summary_parts:
                    for key in list(changes.keys())[:3]:
                        if key != "file_changes":
                            summary_parts.append(f"{key}={changes[key]}")
                change_summary = ", ".join(summary_parts) if summary_parts else "param/config change"
                rationale = (m.rationale or "")[:80]
                pending_text += f"• {m.mutation_id[:12]} | {m.mutation_type.value} | risk={m.risk_level}"
                pillar = getattr(m, 'mission_pillar', None)
                if pillar:
                    from core.evolution import MISSION_PILLARS
                    pending_text += f" | Pillar {pillar}: {MISSION_PILLARS.get(pillar, 'Unmapped')}"
                if summary_parts:
                    pending_text += f" | {', '.join(summary_parts)}"
                if rationale:
                    pending_text += f"\n  rationale: {rationale}"
                pending_text += "\n"
        else:
            pending_text = "None"
        
        rollout_text = ""
        for agent in ["autobot", "alpha_evaluator", "beta_worker"]:
            mutations = engine.get_agent_mutations(agent)
            active = [m for m in mutations if m.rollout_state in ("canary", "rolling_out", "complete")]
            if active:
                m = active[0]
                rollout_text += f"\n<b>{agent}</b>: {m.rollout_state or 'idle'} (mutation {m.mutation_id[:12]})"
            else:
                rollout_text += f"\n<b>{agent}</b>: idle"
        
        from core.agent_config import get_config_store
        config_store = get_config_store()
        config_text = ""
        for agent in ["autobot", "alpha_evaluator", "beta_worker"]:
            try:
                active = config_store.get_active(agent)
                config_text += f"\n• {agent}: {active.get('version', 'v1.0.0')}"
            except Exception:
                config_text += f"\n• {agent}: v1.0.0"
        
        return (
            f"{goal_summary}\n\n"
            f"Autonomy: {autonomy_status['level']}\n\n"
            f"<b>Pending Mutations</b>\n{pending_text}\n\n"
            f"<b>Rollout State</b>\n{rollout_text}\n\n"
            f"<b>Active Config Versions</b>\n{config_text}"
        )
    
    async def _approve_mutation_handler(self, mutation_id: str, approved_by: str = "human_telegram") -> bool:
        """Approve a mutation if autonomy level allows."""
        from core.evolution import get_evolution_engine
        engine = get_evolution_engine()
        
        # Check if mutation is allowed at current autonomy level
        mutation = engine.get_mutation(mutation_id)
        if mutation:
            risk_level = mutation.risk_level
            if not self.autonomy_controller.can_mutate(risk_level):
                print(f"[DAEMON] Mutation {mutation_id} blocked by autonomy level")
                return False
        
        return engine.approve_mutation(mutation_id, approved_by)
    
    async def _reject_mutation_handler(self, mutation_id: str, reason: str, rejected_by: str = "human_telegram") -> bool:
        """Reject a mutation."""
        from core.evolution import get_evolution_engine
        engine = get_evolution_engine()
        return engine.reject_mutation(mutation_id, reason, rejected_by)
    
    async def _stop_autonomy_handler(self):
        """Pause high-risk autonomous actions."""
        self.autonomy_paused = True
        print("[DAEMON] Autonomy paused by operator")
    
    async def start(self):
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text().strip())
                if old_pid and os.path.exists(f"/proc/{old_pid}") or (hasattr(os, 'kill') and self._is_pid_running(old_pid)):
                    print(f"[DAEMON] Another instance is already running (PID {old_pid}). Exiting.")
                    return
            except Exception:
                pass
            self.pid_file.unlink(missing_ok=True)

        self.pid_file.write_text(str(os.getpid()))

        self.running = True
        self.start_time = datetime.utcnow()
        
        print("\n" + "="*80)
        print("AUTONOMOUS COUNCIL DAEMON - STARTING")
        print("="*80)
        print(f"Cycle Interval: {self.cycle_interval}s")
        print(f"Start Time: {self.start_time.isoformat()}")
        print("="*80 + "\n")
        
        # Start Telegram command listener FIRST (so operator can interact even if preflight fails)
        print("Starting Telegram command listener...")
        await self.command_listener.run_polling()
        print("[TELEGRAM] Command listener started - operator can now send commands")
        
        # Run preflight check
        print("Running preflight check...")
        preflight = run_preflight()
        print_report(preflight)
        
        if not preflight["can_run"]:
            print("Preflight failed. Telegram listener remains active for operator commands.")
            await send_council_message(
                "DAEMON",
                "<b>⚠️ Daemon Started with Warnings</b>\n\n"
                "Preflight check failed (Ollama not running or models missing).\n"
                "Telegram command listener is active.\n"
                "Autonomous cycles will not run until Ollama is started.\n\n"
                "Commands: /who /status /goal /approve /reject /stop /help"
            )
            # Keep daemon running for Telegram commands only
            while self.running:
                await asyncio.sleep(1)
            return
        
        await send_council_message(
            "DAEMON",
            f"<b>🚀 Autonomous Council Daemon Started</b>\n\n"
            f"<b>Cycle Interval:</b> {self.cycle_interval}s\n"
            f"<b>Start Time:</b> {self.start_time.isoformat()}\n\n"
            "The council is now running autonomously with:\n"
            "• Goal-driven execution\n"
            "• Curiosity-driven exploration\n"
            "• Performance-based evolution\n"
            "• Telegram command interface\n\n"
            "Commands: /who /status /goal /approve /reject /stop /help"
        )
        
        log_event(
            "daemon_started",
            "system",
            "autonomous_operation",
            {"cycle_interval": self.cycle_interval}
        )
        
        try:
            # Start roadmap update daemon in background
            evolution_engine = get_evolution_engine()
            roadmap_task = asyncio.create_task(evolution_engine.roadmap_update_loop_async())
            
            # Start blue/green auto-update background loop
            if AutoUpdateLoop:
                try:
                    self.auto_updater = AutoUpdateLoop(interval_seconds=300)
                    await self.auto_updater.start()
                except Exception as e:
                    print(f'[DAEMON] Auto-update loop failed to start: {e}')
            
            await start_council(self.cycle_interval)
        except KeyboardInterrupt:
            print("\n\nShutdown signal received...")
            await self.stop()
        except Exception as e:
            print(f"\n\nError in daemon: {e}")
            await send_council_message(
                "SYSTEM",
                f"<b>❌ Council Daemon Error</b>\n\nError: {str(e)}"
            )
            await self.stop()
    
    async def stop(self):
        self.running = False
        
        print("\n" + "="*80)
        print("AUTONOMOUS COUNCIL DAEMON - STOPPING")
        print("="*80)
        
        self.pid_file.unlink(missing_ok=True)
        
        await stop_council()
        
        runtime = datetime.utcnow() - self.start_time
        print(f"Total Runtime: {runtime}")
        print("="*80 + "\n")
        
        await send_council_message(
            "DAEMON",
            f"<b>⏹️ Autonomous Council Daemon Stopped</b>\n\n"
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
    parser.add_argument("--goal", type=str, help="Create a goal and exit")
    parser.add_argument("--health", action="store_true", help="Show health report and exit")
    parser.add_argument("--autonomy", type=str, default="limited", choices=["safe", "limited", "full"], help="Autonomy level")
    
    args = parser.parse_args()
    
    if args.health:
        report = generate_health_report()
        from core.health import print_health_report
        print_health_report(report)
        return
    
    if args.goal:
        goal_store = get_goal_store()
        goal_id = goal_store.create_goal(args.goal, source="human", priority=10)
        print(f"Goal created: {goal_id}")
        return
    
    daemon = CouncilDaemon(args.interval, autonomy_level=args.autonomy)
    
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
        
        await send_council_message(
            "DAEMON",
            "<b>✅ Council Test Mode Complete</b>\n\n"
            "Ran 3 test cycles successfully.\n"
            "All systems operational."
        )
    else:
        await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
