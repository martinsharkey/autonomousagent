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
from core.telegram import get_telegram_bot
from governance.audit_log import log_event


class AutonomousAgentLoop:
    def __init__(self, agent_name: str, cycle_interval: int = 60):
        self.agent_name = agent_name
        self.cycle_interval = cycle_interval
        self.running = False
        self.cycle_count = 0
        
        self.curiosity_engine = get_curiosity_engine(agent_name)
        self.feedback_loop = get_feedback_loop()
        self.evolution_engine = get_evolution_engine()
        self.communication = get_agent_communication(agent_name)
        self.snapdeploy = SnapDeployManager()
        self.telegram = get_telegram_bot()
        
        self.loop_dir = Path("autonomous_loops") / agent_name
        self.loop_dir.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        self.running = True
        print(f"[{self.agent_name.upper()}] Autonomous loop started")
        
        await self.telegram.send_message(
            f"🤖 {self.agent_name} autonomous loop started\n"
            f"Cycle interval: {self.cycle_interval}s"
        )
        
        while self.running:
            try:
                await self.run_cycle()
                self.cycle_count += 1
                await asyncio.sleep(self.cycle_interval)
            except Exception as e:
                print(f"[{self.agent_name.upper()}] Error in cycle: {e}")
                await asyncio.sleep(10)
    
    async def stop(self):
        self.running = False
        print(f"[{self.agent_name.upper()}] Autonomous loop stopped after {self.cycle_count} cycles")
    
    async def run_cycle(self):
        cycle_start = datetime.utcnow()
        print(f"\n[{self.agent_name.upper()}] === Cycle {self.cycle_count + 1} ===")
        
        performance = get_agent_performance(self.agent_name)
        curiosity_score = self.curiosity_engine.calculate_curiosity_score()
        
        print(f"  Performance: {performance.get('success_rate', 0):.2f}")
        print(f"  Curiosity: {curiosity_score:.2f}")
        
        if performance.get("trend") == "declining" or performance.get("success_rate", 0) < 0.4:
            await self._trigger_evolution(performance)
        
        if should_agent_explore(self.agent_name):
            await self._explore()
        
        if performance.get("total_trajectories", 0) > 10:
            await self._consider_spawning()
        
        await self._check_messages()
        
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        print(f"  Cycle completed in {cycle_duration:.2f}s")
        
        self._log_cycle(performance, curiosity_score, cycle_duration)
    
    async def _trigger_evolution(self, performance: Dict[str, Any]):
        print(f"  [{self.agent_name.upper()}] Triggering evolution due to poor performance")
        
        success_rate = performance.get("success_rate", 0)
        
        if success_rate < 0.3:
            mutation_type = MutationType.STRATEGY_EVOLUTION
            description = "Strategy evolution to improve success rate"
            rationale = f"Current success rate: {success_rate:.2f}"
            proposed_changes = {
                "strategy": "adaptive",
                "learning_rate": 0.15,
                "exploration_factor": 0.25
            }
            expected_improvement = 0.20
        else:
            mutation_type = MutationType.PARAMETER_ADJUSTMENT
            description = "Parameter tuning for performance optimization"
            rationale = f"Optimizing based on metrics"
            proposed_changes = {
                "temperature": 0.15,
                "max_retries": 4
            }
            expected_improvement = 0.10
        
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
        
        await self.telegram.send_message(
            f"🧬 {self.agent_name} proposed evolution\n"
            f"Type: {mutation_type.value}\n"
            f"Expected improvement: {expected_improvement:.0%}\n"
            f"ID: {mutation.mutation_id}"
        )
    
    async def _explore(self):
        print(f"  [{self.agent_name.upper()}] Exploring based on curiosity")
        
        target = get_exploration_target(self.agent_name)
        
        log_trajectory(
            agent_name=self.agent_name,
            state={"phase": "exploration", "cycle": self.cycle_count},
            prompt=f"Exploration: {target['description']}",
            response=f"Exploring: {target['type']}",
            reward=0.5,
            session_id=f"exploration_{self.agent_name}_{self.cycle_count}",
            metadata={"type": "exploration", "target": target}
        )
        
        self.curiosity_engine.log_curiosity_event(
            "exploration_initiated",
            {"target": target}
        )
        
        print(f"  Exploration target: {target['description']}")
    
    async def _consider_spawning(self):
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
                        await self.telegram.send_message(
                            f"✅ {self.agent_name} mutation implemented\n"
                            f"ID: {mutation_id}"
                        )
    
    def _log_cycle(self, performance: Dict, curiosity: float, duration: float):
        cycle_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "cycle": self.cycle_count,
            "performance": performance,
            "curiosity_score": curiosity,
            "duration_seconds": duration
        }
        
        log_file = self.loop_dir / f"cycle_{self.cycle_count:04d}.json"
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
