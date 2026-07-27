"""Real-time monitoring dashboard for the autonomous council.

Shows:
- Agent reasoning traces from AgentState
- Inter-agent messages from message bus
- Goal execution status
- Mutation proposals and votes
- System events in real time
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from core.communication import get_message_bus
    from core.goals import get_goal_store
    from core.telegram import get_telegram_bot
except ImportError:
    get_message_bus = None
    get_goal_store = None
    get_telegram_bot = None


WORKSPACE = Path(".").resolve()
LOGS_DIR = WORKSPACE / "monitoring" / "council_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _write_session_log(filename: str, entries: List[Dict[str, Any]]) -> None:
    path = LOGS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)


class CouncilMonitor:
    def __init__(self, poll_interval: float = 1.0, duration: float = 300.0):
        self.poll_interval = poll_interval
        self.duration = duration
        self.start_time = time.time()
        self.session_entries: List[Dict[str, Any]] = []
        self.seen_messages: set = set()
        self.seen_goals: set = set()
        self.seen_trajectories: set = set()

    def _entry(self, category: str, source: str, content: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": _timestamp(),
            "category": category,
            "source": source,
            "content": content,
        }

    def _tail_file(self, path: Path, max_lines: int = 200) -> List[str]:
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            return [line.rstrip("\n") for line in lines[-max_lines:]]
        except Exception:
            return []

    def _poll_communication(self) -> List[Dict[str, Any]]:
        events = []
        if get_message_bus is None:
            return events
        try:
            bus = get_message_bus()
            messages = bus.receive(limit=50)
            for msg in messages:
                key = getattr(msg, "message_id", id(msg))
                if key in self.seen_messages:
                    continue
                self.seen_messages.add(key)
                events.append(self._entry(
                    "communication",
                    getattr(msg, "sender", "unknown"),
                    {
                        "message_type": getattr(msg, "message_type", "unknown"),
                        "receiver": getattr(msg, "receiver", "unknown"),
                        "content": getattr(msg, "content", {}),
                    },
                ))
        except Exception:
            pass
        return events

    def _poll_goals(self) -> List[Dict[str, Any]]:
        events = []
        if get_goal_store is None:
            return events
        try:
            store = get_goal_store()
            goals = store.get_recent_goals(limit=20)
            for goal in goals:
                gid = goal.get("goal_id")
                status = goal.get("status")
                if gid in self.seen_goals:
                    continue
                self.seen_goals.add(gid)
                events.append(self._entry(
                    "goal",
                    goal.get("assigned_agent", "unassigned"),
                    {
                        "goal_id": gid,
                        "status": status,
                        "description": goal.get("description", "")[:200],
                        "result_summary": goal.get("result_summary", ""),
                        "reward": goal.get("reward"),
                    },
                ))
        except Exception:
            pass
        return events

    def _poll_loop_logs(self) -> List[Dict[str, Any]]:
        events = []
        loop_root = WORKSPACE / "autonomous_loops"
        if not loop_root.exists():
            return events
        for agent_dir in sorted(loop_root.iterdir()):
            if not agent_dir.is_dir():
                continue
            cycle_files = sorted(agent_dir.glob("cycle_*.json"))[-5:]
            for cycle_file in cycle_files:
                key = str(cycle_file.resolve())
                if key in self.seen_trajectories:
                    continue
                self.seen_trajectories.add(key)
                try:
                    with open(cycle_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    events.append(self._entry(
                        "cycle",
                        agent_dir.name,
                        {
                            "cycle_file": cycle_file.name,
                            "cycle": data.get("cycle"),
                            "performance": data.get("performance", {}),
                            "curiosity_score": data.get("curiosity_score"),
                            "duration_seconds": data.get("duration_seconds"),
                        },
                    ))
                except Exception:
                    pass
        return events

    def _poll_mutations(self) -> List[Dict[str, Any]]:
        events = []
        mutations_dir = WORKSPACE / "evolution" / "mutations"
        if not mutations_dir.exists():
            return events
        files = sorted(mutations_dir.glob("mutation_*.json"), key=os.path.getmtime)[-10:]
        for mutation_file in files:
            try:
                with open(mutation_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                mid = data.get("mutation_id")
                if mid in self.seen_messages:
                    continue
                self.seen_messages.add(mid)
                events.append(self._entry(
                    "mutation",
                    data.get("agent_name", "unknown"),
                    {
                        "mutation_id": mid,
                        "status": data.get("status"),
                        "description": data.get("description", "")[:200],
                        "rollout_state": data.get("rollout_state"),
                        "quality_score": data.get("quality_score"),
                        "mission_pillar": data.get("mission_pillar"),
                    },
                ))
            except Exception:
                pass
        return events

    def _poll_trajectories(self) -> List[Dict[str, Any]]:
        events = []
        for agent in ["autobot", "alpha_evaluator", "beta_worker"]:
            try:
                from core.data_logger import get_trajectories
                entries = get_trajectories(agent_name=agent, limit=10)
                for entry in entries:
                    tid = entry.get("trajectory_id") or entry.get("session_id")
                    if tid in self.seen_trajectories:
                        continue
                    self.seen_trajectories.add(tid)
                    events.append(self._entry(
                        "trajectory",
                        agent,
                        {
                            "trajectory_id": tid,
                            "prompt": (entry.get("prompt") or "")[:220],
                            "response": (entry.get("response") or "")[:220],
                            "reward": entry.get("reward"),
                            "metadata": entry.get("metadata", {}),
                        },
                    ))
            except Exception:
                pass
        return events

    def _poll_reasoning_traces(self) -> List[Dict[str, Any]]:
        events = []
        try:
            from core.graph import app
            for agent in ["autobot", "alpha_evaluator", "beta_worker"]:
                from core.state import AgentState
                state: AgentState = {
                    "messages": [],
                    "loop_count": 0,
                    "completed_nodes": [],
                    "recent_tool_invocations": [],
                    "codebase_hash": "",
                    "reasoning_traces": [],
                    "error_feedback": [],
                    "active_mutation_id": None,
                    "proposed_mutation_code": None,
                    "mission_rationale": None,
                    "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},
                    "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},
                    "operator_override": None,
                    "operator_override_rationale": None,
                    "operator_override_timestamp": None,
                    "escalation_reason": None,
                    "requires_operator_approval": False,
                    "proposed_version": None,
                    "current_version": "v1.0.0",
                    "rollback_pending": False,
                    "rollback_target_version": None,
                    "rollback_approved": False,
                    "rollback_reason": None,
                }
                traces = state.get("reasoning_traces", [])
                for trace in traces[-5:]:
                    events.append(self._entry("reasoning", agent, {"trace": str(trace)[:300]}))
        except Exception:
            pass
        return events

    def _format_entry(self, entry: Dict[str, Any]) -> str:
        ts = entry.get("timestamp", _timestamp())
        category = entry.get("category", "unknown")
        source = entry.get("source", "unknown")
        content = entry.get("content", {})
        return f"[{ts}] [{category.upper():<14}] [{source.upper():<16}] {json.dumps(content, ensure_ascii=False, default=str)[:500]}"

    def run(self) -> None:
        print(f"[MONITOR] Council monitoring started for {self.duration}s")
        print(f"[MONITOR] Logs directory: {LOGS_DIR}")
        print(f"[MONITOR] Watching: communication, goals, mutations, trajectories, reasoning traces\n")

        last_summary = time.time()
        all_events: List[Dict[str, Any]] = []

        try:
            while time.time() - self.start_time < self.duration:
                batch_events: List[Dict[str, Any]] = []
                for poller in (
                    self._poll_communication,
                    self._poll_goals,
                    self._poll_loop_logs,
                    self._poll_mutations,
                    self._poll_trajectories,
                    self._poll_reasoning_traces,
                ):
                    try:
                        batch_events.extend(poller())
                    except Exception as exc:
                        batch_events.append(self._entry("monitor", "monitor", {"error": str(exc)}))

                for event in batch_events:
                    print(self._format_entry(event))
                    all_events.append(event)

                if time.time() - last_summary >= 30.0:
                    print("\n[COUNCIL SUMMARY]")
                    self._print_summary(all_events)
                    last_summary = time.time()

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[MONITOR] Interrupted")

        session_file = LOGS_DIR / f"monitor_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        _write_session_log(session_file.name, all_events)
        print(f"\n[MONITOR] Session log written: {session_file}")
        print(f"[MONITOR] Total events captured: {len(all_events)}")
        self._print_summary(all_events)

    def _print_summary(self, events: List[Dict[str, Any]]) -> None:
        counts: Dict[str, int] = {}
        agent_activity: Dict[str, int] = {}
        for event in events:
            category = event.get("category", "unknown")
            counts[category] = counts.get(category, 0) + 1
            source = event.get("source", "unknown")
            agent_activity[source] = agent_activity.get(source, 0) + 1

        print(f"  Events by category: {json.dumps(counts, ensure_ascii=False)}")
        print(f"  Events by source:   {json.dumps(agent_activity, ensure_ascii=False)}")

        reasoning = [e for e in events if e.get("category") == "reasoning"]
        if reasoning:
            print(f"  Latest reasoning traces ({len(reasoning)} total):")
            for trace in reasoning[-3:]:
                content = trace.get("content", {})
                print(f"    - [{trace.get('source')}] {str(content.get('trace', ''))[:240]}")

        goals = [e for e in events if e.get("category") == "goal"]
        if goals:
            latest = goals[-1]
            content = latest.get("content", {})
            print(f"  Latest goal: [{latest.get('source')}] {content.get('status')} | {content.get('description')[:120]}")

        mutations = [e for e in events if e.get("category") == "mutation"]
        if mutations:
            latest = mutations[-1]
            content = latest.get("content", {})
            print(f"  Latest mutation: [{latest.get('source')}] {content.get('status')} | {content.get('description')[:120]}")


def start_background_monitor(poll_interval: float = 1.0, duration: float = 300.0):
    monitor = CouncilMonitor(poll_interval=poll_interval, duration=duration)
    try:
        import threading
        thread = threading.Thread(target=monitor.run, daemon=True)
        thread.start()
        return thread
    except Exception as exc:
        print(f"[MONITOR] Failed to start background monitor: {exc}")
        return None


__all__ = ["CouncilMonitor", "start_background_monitor"]
