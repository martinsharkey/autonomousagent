import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict

from core.data_logger import get_trajectories, log_trajectory
from core.communication import send_message, get_message_bus
from governance.audit_log import log_event


class CuriosityEngine:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.curiosity_dir = Path("curiosity") / agent_name
        self.curiosity_dir.mkdir(parents=True, exist_ok=True)
        
        self.curiosity_history: List[Dict] = []
        self.knowledge_gaps: List[str] = []
        self.exploration_targets: List[str] = []
        
        self.current_curiosity_score = 0.5
        self.exploration_rate = 0.3
        
        self._initialize_curiosity()
    
    def _initialize_curiosity(self):
        default_gaps = [
            "understanding_agent_behavior",
            "optimizing_response_quality",
            "learning_from_failures",
            "discovering_new_strategies",
            "improving_coordination"
        ]
        self.knowledge_gaps = default_gaps.copy()
    
    def calculate_curiosity_score(self, recent_trajectories: List[Dict] = None) -> float:
        score = 0.5
        
        if recent_trajectories:
            rewards = [t.get("reward", 0.5) for t in recent_trajectories if t.get("reward") is not None]
            
            if rewards:
                avg_reward = sum(rewards) / len(rewards)
                variance = sum((r - avg_reward) ** 2 for r in rewards) / len(rewards)
                
                if avg_reward < 0.5:
                    score += 0.2
                if variance > 0.1:
                    score += 0.15
                if len(self.knowledge_gaps) > 0:
                    score += 0.1 * min(len(self.knowledge_gaps) / 5, 1.0)
        
        score = min(max(score, 0.0), 1.0)
        self.current_curiosity_score = score
        
        return score
    
    def should_explore(self) -> bool:
        return random.random() < self.exploration_rate or self.current_curiosity_score > 0.7
    
    def identify_knowledge_gaps(self, trajectories: List[Dict]) -> List[str]:
        gaps = []
        
        failed_trajectories = [t for t in trajectories if t.get("reward", 0) < 0.5]
        
        if len(failed_trajectories) > len(trajectories) * 0.3:
            gaps.append("improving_failure_handling")
        
        unique_prompts = set(t.get("prompt", "")[:50] for t in trajectories)
        if len(unique_prompts) < 3:
            gaps.append("limited_task_diversity")
        
        recent_rewards = [t.get("reward", 0) for t in trajectories[-5:]]
        if recent_rewards and sum(recent_rewards) / len(recent_rewards) < 0.4:
            gaps.append("performance_degradation")
        
        self.knowledge_gaps = list(set(self.knowledge_gaps + gaps))
        
        return gaps
    
    def generate_exploration_target(self) -> Dict[str, Any]:
        if not self.knowledge_gaps:
            return {
                "type": "general_exploration",
                "description": "Explore new task types",
                "priority": "medium"
            }
        
        gap = random.choice(self.knowledge_gaps)
        
        targets = {
            "improving_failure_handling": {
                "type": "failure_analysis",
                "description": "Analyze recent failures to identify patterns",
                "priority": "high"
            },
            "limited_task_diversity": {
                "type": "task_exploration",
                "description": "Try different types of tasks",
                "priority": "medium"
            },
            "performance_degradation": {
                "type": "performance_optimization",
                "description": "Investigate and fix performance issues",
                "priority": "high"
            },
            "understanding_agent_behavior": {
                "type": "behavior_analysis",
                "description": "Analyze coordination patterns",
                "priority": "medium"
            }
        }
        
        target = targets.get(gap, {
            "type": "general_exploration",
            "description": f"Explore: {gap}",
            "priority": "medium"
        })
        
        return target
    
    def log_curiosity_event(self, event_type: str, details: Dict[str, Any]):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "event_type": event_type,
            "curiosity_score": self.current_curiosity_score,
            "details": details
        }
        
        self.curiosity_history.append(event)
        
        # Ensure directory exists before writing
        self.curiosity_dir.mkdir(parents=True, exist_ok=True)
        
        event_file = self.curiosity_dir / f"curiosity_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(event_file, "w") as f:
            json.dump(event, f, indent=2)
        
        log_event(
            "curiosity_event",
            self.agent_name,
            "curiosity",
            {
                "event_type": event_type,
                "curiosity_score": self.current_curiosity_score
            }
        )
    
    def get_curiosity_summary(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "current_score": self.current_curiosity_score,
            "exploration_rate": self.exploration_rate,
            "knowledge_gaps": len(self.knowledge_gaps),
            "total_events": len(self.curiosity_history),
            "should_explore": self.should_explore()
        }
    
    def update_exploration_rate(self, performance_trend: str):
        if performance_trend == "declining":
            self.exploration_rate = min(self.exploration_rate + 0.1, 0.8)
        elif performance_trend == "improving":
            self.exploration_rate = max(self.exploration_rate - 0.05, 0.1)


_curiosity_engines: Dict[str, CuriosityEngine] = {}

def get_curiosity_engine(agent_name: str) -> CuriosityEngine:
    if agent_name not in _curiosity_engines:
        _curiosity_engines[agent_name] = CuriosityEngine(agent_name)
    return _curiosity_engines[agent_name]

def calculate_curiosity(agent_name: str, trajectories: List[Dict] = None) -> float:
    engine = get_curiosity_engine(agent_name)
    return engine.calculate_curiosity_score(trajectories)

def should_agent_explore(agent_name: str) -> bool:
    engine = get_curiosity_engine(agent_name)
    return engine.should_explore()

def get_exploration_target(agent_name: str) -> Dict[str, Any]:
    engine = get_curiosity_engine(agent_name)
    return engine.generate_exploration_target()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Curiosity engine for autonomous exploration")
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--score", action="store_true", help="Show curiosity score")
    parser.add_argument("--explore", action="store_true", help="Check if should explore")
    parser.add_argument("--target", action="store_true", help="Get exploration target")
    
    args = parser.parse_args()
    
    if args.score:
        score = calculate_curiosity(args.agent)
        print(f"Curiosity score for {args.agent}: {score:.2f}")
    elif args.explore:
        should = should_agent_explore(args.agent)
        print(f"Should {args.agent} explore: {should}")
    elif args.target:
        target = get_exploration_target(args.agent)
        print(json.dumps(target, indent=2))
    else:
        parser.print_help()
