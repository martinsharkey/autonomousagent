import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.curiosity import get_curiosity_engine, should_agent_explore, get_exploration_target
from core.feedback import get_feedback_loop, get_agent_performance
from core.evolution import get_evolution_engine, propose_mutation, MutationType
from core.communication import get_agent_communication, send_message
from core.data_logger import log_trajectory, get_trajectories
from core.snapdeploy import SnapDeployManager
from core.telegram import get_telegram_bot, send_council_message
from core.goals import get_goal_store, GoalStatus
from core.planning import AgentPlanner
from core.governor import get_governor
from governance.audit_log import log_event


def calculate_reward(feedback=None):
    """Calculate goal reward from feedback."""
    
    if feedback is None:
        # Default: neutral
        return 0.5
    
    # If feedback has success rate, use it
    success_rate = feedback.get("success_rate", 0.5)
    
    # If feedback has time bonus (faster = better)
    speed_bonus = feedback.get("speed_bonus", 0.0)
    
    # Combine: 70% from success, 30% from speed
    reward = (success_rate * 0.7) + (speed_bonus * 0.3)
    
    # Ensure it's in valid range
    reward = max(0.0, min(1.0, reward))
    
    return reward

class AutonomousAgentLoop:
    def __init__(self, agent_name: str, cycle_interval: int = 60):
        self.agent_name = agent_name
        self.cycle_interval = cycle_interval
        self.running = False
        self.cycle_count = 0
        self.start_time = datetime.utcnow()
        
        self.curiosity_engine = get_curiosity_engine(agent_name)
        self.feedback_loop = get_feedback_loop()
        self.evolution_engine = get_evolution_engine()
        self.communication = get_agent_communication(agent_name)
        self.snapdeploy = SnapDeployManager()
        self.telegram = get_telegram_bot()
        self.goal_store = get_goal_store()
        self.planner = AgentPlanner(agent_name)
        self.governor = get_governor()
        
        self.loop_dir = Path("autonomous_loops") / agent_name
        self.loop_dir.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        self.running = True
        self.start_time = datetime.utcnow()
        print(f"[{self.agent_name.upper()}] Autonomous loop started")
        
        await send_council_message(
            self.agent_name.upper(),
            f"<b>🤖 Autonomous Loop Started</b>\n\n"
            f"<b>Agent:</b> {self.agent_name}\n"
            f"<b>Cycle Interval:</b> {self.cycle_interval}s\n"
            f"<b>Start Time:</b> {self.start_time.isoformat()}"
        )
        
        while self.running:
            try:
                await self.run_cycle()
                self.cycle_count += 1
                await asyncio.sleep(self.cycle_interval)
            except Exception as e:
                print(f"[{self.agent_name.upper()}] Error in cycle: {e}")
                await send_council_message(
                    "SYSTEM",
                    f"<b>❌ Loop Error</b>\n\n"
                    f"<b>Agent:</b> {self.agent_name}\n"
                    f"<b>Error:</b> {str(e)}",
                )
                await asyncio.sleep(10)
    
    async def stop(self):
        self.running = False
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        print(f"[{self.agent_name.upper()}] Autonomous loop stopped after {self.cycle_count} cycles")
        
        await send_council_message(
            self.agent_name.upper(),
            f"<b>⏹️ Autonomous Loop Stopped</b>\n\n"
            f"<b>Agent:</b> {self.agent_name}\n"
            f"<b>Total Cycles:</b> {self.cycle_count}\n"
            f"<b>Uptime:</b> {uptime:.0f}s"
        )
    
    async def run_cycle(self):
        # Check resource limits before running
        if not self.governor.can_run_cycle():
            print(f"  [{self.agent_name.upper()}] Resource limit reached, skipping cycle")
            await asyncio.sleep(self.cycle_interval)
            return
        
        cycle_start = datetime.utcnow()
        cycle_id = f"cycle_{self.agent_name}_{self.cycle_count + 1}"
        print(f"\n[{self.agent_name.upper()}] === Cycle {self.cycle_count + 1} ===")
        
        performance = get_agent_performance(self.agent_name)
        curiosity_score = self.curiosity_engine.calculate_curiosity_score()
        
        print(f"  Performance: {performance.get('success_rate', 0):.2f}")
        print(f"  Curiosity: {curiosity_score:.2f}")
        
        # Select and execute a goal
        await self._select_and_execute_goal(cycle_id, cycle_start)
        
        if performance.get("trend") == "declining" or performance.get("success_rate", 0) < 0.4:
            await self._trigger_evolution(performance, cycle_id)
        
        if should_agent_explore(self.agent_name):
            await self._explore(cycle_id)
        
        if performance.get("total_trajectories", 0) > 10:
            await self._consider_spawning(cycle_id)
        
        await self._check_messages()
        
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        print(f"  Cycle completed in {cycle_duration:.2f}s")
        
        self._log_cycle(performance, curiosity_score, cycle_duration, cycle_id)
    
    async def _select_and_execute_goal(self, cycle_id: str = None, cycle_start: datetime = None):
        """Select highest-priority pending goal and execute it using planning."""
        pending_goals = self.goal_store.get_pending_goals(limit=1)
        
        if not pending_goals:
            print(f"  [{self.agent_name.upper()}] No pending goals")
            return
        
        goal = pending_goals[0]
        goal_id = goal["goal_id"]
        
        print(f"  [{self.agent_name.upper()}] Executing goal {goal_id[:12]}...: {goal['description'][:50]}")
        
        # Assign goal to this agent
        self.goal_store.assign_goal(goal_id, self.agent_name)
        self.goal_store.update_goal_status(goal_id, GoalStatus.IN_PROGRESS.value)
        
        await send_council_message(
            self.agent_name.upper(),
            f"<b>🎯 Goal Started</b>\n\n"
            f"<b>Goal ID:</b> {goal_id}\n"
            f"<b>Description:</b> {goal['description'][:100]}\n"
            f"<b>Agent:</b> {self.agent_name}"
        )
        
        try:
            # Create a plan for the goal
            plan_result = self.planner.create_plan(goal["description"])
            
            if plan_result.get("status") != "created":
                raise Exception(f"Failed to create plan: {plan_result.get('error')}")
            
            # Execute the plan
            execution_result = self.planner.execute_plan(plan_result)
            
            # Calculate reward based on execution success
            if execution_result.get("status") == "completed":
                reward = calculate_reward({"success_rate": 0.9, "speed_bonus": 0.1})
            else:
                reward = calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0})
            
            # Log trajectory
            log_trajectory(
                agent_name=self.agent_name,
                state={"phase": "goal_execution", "cycle_id": cycle_id, "plan_steps": len(plan_result.get("plan", {}).get("steps", []))},
                prompt=goal["description"],
                response=f"Goal executed: {goal_id}, Status: {execution_result.get('status')}",
                reward=reward,
                session_id=goal_id,
                metadata={"goal_id": goal_id, "type": "goal_execution", "execution_status": execution_result.get("status")}
            )
            
            # Update goal status
            self.goal_store.update_goal_status(
                goal_id,
                GoalStatus.COMPLETED.value if execution_result.get("status") == "completed" else GoalStatus.FAILED.value,
                result_summary=f"Executed by {self.agent_name}, Status: {execution_result.get('status')}",
                reward=reward
            )
            
            await send_council_message(
                self.agent_name.upper(),
                f"<b>✅ Goal Completed</b>\n\n"
                f"<b>Goal ID:</b> {goal_id}\n"
                f"<b>Status:</b> {execution_result.get('status')}\n"
                f"<b>Reward:</b> {reward:.2f}\n"
                f"<b>Duration:</b> {(datetime.utcnow() - cycle_start).total_seconds():.1f}s"
            )
            
        except Exception as e:
            print(f"  [{self.agent_name.upper()}] Goal execution failed: {e}")
            self.goal_store.update_goal_status(
                goal_id,
                GoalStatus.FAILED.value,
                result_summary=f"Failed: {str(e)}"
            )
            
            await send_council_message(
                "SYSTEM",
                f"<b>❌ Goal Failed</b>\n\n"
                f"<b>Goal ID:</b> {goal_id}\n"
                f"<b>Error:</b> {str(e)}"
            )
    
async def _trigger_evolution(self, performance: Dict[str, Any], cycle_id: str = None):
        print(f"  [{self.agent_name.upper()}] Triggering evolution due to poor performance")

        success_rate = performance.get("success_rate", 0)

        VALID_PARAMS = {
            "autobot": ["temperature", "max_retries", "system_prompt"],
            "alpha_evaluator": ["temperature", "system_prompt"],
            "beta_worker": ["temperature", "system_prompt"],
        }

        agent_valid_params = VALID_PARAMS.get(self.agent_name, ["temperature"])

        if success_rate < 0.3:
            mutation_type = MutationType.STRATEGY_EVOLUTION
            description = "Strategy evolution to improve success rate"
            rationale = f"Current success rate: {success_rate:.2f}"
            proposed_changes = {p: v for p, v in {"temperature": 0.15, "max_retries": 4}.items() if p in agent_valid_params}
            expected_improvement = 0.20
        else:
            mutation_type = MutationType.PARAMETER_ADJUSTMENT
            description = "Parameter tuning for performance optimization"
            rationale = f"Optimizing based on metrics"
            proposed_changes = {p: v for p, v in {"temperature": 0.15, "max_retries": 4}.items() if p in agent_valid_params}
            expected_improvement = 0.10

        if not proposed_changes:
            proposed_changes = {"temperature": 0.15}

        mutation = propose_mutation(
            agent_name=self.agent_name,
            mutation_type=mutation_type,
            description=description,
            rationale=rationale,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            risk_level="medium"
        )
        
        print(f"  Mutation proposed: {mutation.mutation_id}")
        
        await self.telegram.send_mutation_notification(
            mutation_id=mutation.mutation_id,
            status="PROPOSED",
            agent_name=self.agent_name,
            speaker="EVOLUTION"
        )
    
    async def _explore(self, cycle_id: str = None):
        """Exploration creates a real goal and executes it with real rewards."""
        print(f"  [{self.agent_name.upper()}] Exploring based on curiosity")
        
        target = get_exploration_target(self.agent_name)
        
        # Create a real exploration goal instead of logging fake reward
        exploration_goal_description = f"Exploration: {target['description']}"
        goal_id = self.goal_store.create_goal(
            description=exploration_goal_description,
            source="curiosity",
            priority=5,
            assigned_agent=self.agent_name,
            metadata={"type": "exploration", "target": target, "cycle_id": cycle_id}
        )
        
        print(f"  Created exploration goal {goal_id[:12]}...: {target['description']}")
        
        # Execute the exploration goal through the graph
        try:
            from core.graph import app
            
            initial_state = {
                "messages": [("user", exploration_goal_description)],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": "",
                "active_mutation_id": None,
                "proposed_mutation_code": None,
                "mission_rationale": exploration_goal_description,
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
                "rollback_reason": None
            }
            
            config = {"configurable": {"thread_id": goal_id}}
            
            final_state = None
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in chunk.items():
                    final_state = state_update
            
            # Calculate real reward based on exploration outcome
            if final_state and "voting_complete" in final_state.get("completed_nodes", []):
                reward = calculate_reward({"success_rate": 0.8, "speed_bonus": 0.2})  # Successful exploration
            else:
                reward = calculate_reward({"success_rate": 0.4, "speed_bonus": 0.0})  # Partial exploration
            
            # Log trajectory with REAL reward
            log_trajectory(
                agent_name=self.agent_name,
                state={"phase": "exploration", "cycle": self.cycle_count, "cycle_id": cycle_id, "goal_id": goal_id},
                prompt=exploration_goal_description,
                response=f"Exploration executed: {goal_id}, Target: {target['type']}",
                reward=reward,
                session_id=goal_id,
                metadata={"type": "exploration", "target": target, "cycle_id": cycle_id, "goal_id": goal_id}
            )
            
            # Update goal status with real reward
            self.goal_store.update_goal_status(
                goal_id,
                GoalStatus.COMPLETED.value if reward >= 0.7 else GoalStatus.FAILED.value,
                result_summary=f"Exploration by {self.agent_name}, Target: {target['type']}, Reward: {reward:.2f}",
                reward=reward
            )
            
            print(f"  Exploration completed with real reward: {reward:.2f}")
            
        except Exception as e:
            print(f"  [{self.agent_name.upper()}] Exploration execution failed: {e}")
            self.goal_store.update_goal_status(
                goal_id,
                GoalStatus.FAILED.value,
                result_summary=f"Exploration failed: {str(e)}",
                reward=calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0})
            )
            
            # Log failed exploration with real reward
            log_trajectory(
                agent_name=self.agent_name,
                state={"phase": "exploration", "cycle": self.cycle_count, "cycle_id": cycle_id, "goal_id": goal_id},
                prompt=exploration_goal_description,
                response=f"Exploration failed: {str(e)}",
                reward=calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0}),
                session_id=goal_id,
                metadata={"type": "exploration", "target": target, "cycle_id": cycle_id, "goal_id": goal_id, "error": str(e)}
            )
        
        self.curiosity_engine.log_curiosity_event(
            "exploration_completed",
            {"target": target, "cycle_id": cycle_id, "goal_id": goal_id}
        )
    
    async def _consider_spawning(self, cycle_id: str = None):
        performance = get_agent_performance(self.agent_name)
        
        if performance.get("total_trajectories", 0) > 20:
            print(f"  [{self.agent_name.upper()}] Considering container spawning")
            
            dockerfile = self._generate_worker_dockerfile()
            
            deployment_name = f"{self.agent_name}_worker_{self.cycle_count}"
            
            print(f"  Would spawn: {deployment_name}")
            print(f"  (SnapDeploy integration ready but requires API key)")
    
    def _generate_worker_dockerfile(self) -> str:
        return f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY agents/ ./agents/

ENV AGENT_NAME={self.agent_name}

CMD ["python", "-m", "agents.{self.agent_name}"]
"""
    
    async def _check_messages(self):
        messages = self.communication.receive(limit=5)
        
        for msg in messages:
            print(f"  [{self.agent_name.upper()}] Received message: {msg.message_type}")
            
            if msg.message_type == "mutation_approved":
                mutation_id = msg.content.get("mutation_id")
                if mutation_id:
                    result = self.evolution_engine.implement_mutation(mutation_id)
                    if result.get("success"):
                        print(f"  Mutation implemented: {mutation_id}")
                        await self.telegram.send_mutation_notification(
                            mutation_id=mutation_id,
                            status="IMPLEMENTED",
                            agent_name=self.agent_name,
                            speaker="EVOLUTION"
                        )
    
    def _log_cycle(self, performance: Dict, curiosity: float, duration: float, cycle_id: str = None):
        cycle_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "cycle": self.cycle_count,
            "cycle_id": cycle_id,
            "performance": performance,
            "curiosity_score": curiosity,
            "duration_seconds": duration
        }
        
        log_file = self.loop_dir / f"cycle_{self.cycle_count:04d}.json"
        
        # Ensure directory exists before writing
        self.loop_dir.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, "w") as f:
            json.dump(cycle_log, f, indent=2)


import json

_council_loops: Dict[str, AutonomousAgentLoop] = {}

def get_agent_loop(agent_name: str, cycle_interval: int = 60) -> AutonomousAgentLoop:
    if agent_name not in _council_loops:
        _council_loops[agent_name] = AutonomousAgentLoop(agent_name, cycle_interval)
    return _council_loops[agent_name]

async def start_council(cycle_interval: int = 60):
    agents = ["autobot", "alpha_evaluator", "beta_worker"]
    
    loops = [get_agent_loop(agent, cycle_interval) for agent in agents]
    
    tasks = [loop.start() for loop in loops]
    
    await asyncio.gather(*tasks)

async def stop_council():
    for loop in _council_loops.values():
        await loop.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous agent loop")
    parser.add_argument("--agent", help="Run specific agent")
    parser.add_argument("--all", action="store_true", help="Run all agents")
    parser.add_argument("--interval", type=int, default=60, help="Cycle interval in seconds")
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(start_council(args.interval))
    elif args.agent:
        loop = get_agent_loop(args.agent, args.interval)
        asyncio.run(loop.start())
    else:
        parser.print_help()
