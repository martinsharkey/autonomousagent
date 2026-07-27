import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict

from core.data_logger import get_trajectories, log_trajectory
from core.communication import send_message, get_message_bus
from core.evolution import propose_mutation, MutationType, get_evolution_engine
from governance.audit_log import log_event


class PerformanceMetrics:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.metrics_history: List[Dict] = []
        self.current_metrics = {
            "success_rate": 0.0,
            "avg_reward": 0.0,
            "total_trajectories": 0,
            "recent_performance": 0.0,
            "trend": "stable",
            "last_updated": None
        }
    
    def update_from_trajectories(self, trajectories: List[Dict], window_size: int = 10):
        if not trajectories:
            return
        
        self.current_metrics["total_trajectories"] = len(trajectories)
        
        rewards = [t.get("reward", 0.0) for t in trajectories if t.get("reward") is not None]
        
        if rewards:
            self.current_metrics["avg_reward"] = sum(rewards) / len(rewards)
            self.current_metrics["success_rate"] = len([r for r in rewards if r > 0.5]) / len(rewards)
        
        recent_trajectories = trajectories[-window_size:]
        recent_rewards = [t.get("reward", 0.0) for t in recent_trajectories if t.get("reward") is not None]
        
        if recent_rewards:
            self.current_metrics["recent_performance"] = sum(recent_rewards) / len(recent_rewards)
        
        if len(self.metrics_history) >= 2:
            prev_perf = self.metrics_history[-1].get("recent_performance", 0.0)
            curr_perf = self.current_metrics["recent_performance"]
            
            if curr_perf > prev_perf + 0.05:
                self.current_metrics["trend"] = "improving"
            elif curr_perf < prev_perf - 0.05:
                self.current_metrics["trend"] = "declining"
            else:
                self.current_metrics["trend"] = "stable"
        
        self.current_metrics["last_updated"] = datetime.utcnow().isoformat()
        
        self.metrics_history.append(self.current_metrics.copy())
    
    def get_metrics(self) -> Dict[str, Any]:
        return self.current_metrics.copy()
    
    def needs_evolution(self) -> bool:
        if self.current_metrics["trend"] == "declining":
            return True
        
        if self.current_metrics["recent_performance"] < 0.4:
            return True
        
        if self.current_metrics["success_rate"] < 0.3:
            return True
        
        return False


class FeedbackLoop:
    def __init__(self):
        self.feedback_dir = Path("feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.agent_metrics: Dict[str, PerformanceMetrics] = {}
        self.feedback_history: List[Dict] = []
        self._last_evolution_proposal: Dict[str, float] = {}
        self._evolution_cooldown_seconds = 300
        
        self._initialize_agents()
    
    def _initialize_agents(self):
        agents = ["autobot", "alpha_evaluator", "beta_worker"]
        for agent in agents:
            self.agent_metrics[agent] = PerformanceMetrics(agent)
    
    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        results = {}
        
        for agent_name in self.agent_metrics.keys():
            trajectories = get_trajectories(session_id, agent_name=agent_name)
            
            if trajectories:
                self.agent_metrics[agent_name].update_from_trajectories(trajectories)
                
                metrics = self.agent_metrics[agent_name].get_metrics()
                results[agent_name] = metrics
                
                self._provide_feedback(agent_name, metrics)
                
                if self.agent_metrics[agent_name].needs_evolution():
                    self._trigger_evolution_proposal(agent_name, metrics)
        
        self._save_analysis(session_id, results)
        
        return results
    
    def _provide_feedback(self, agent_name: str, metrics: Dict[str, Any]):
        feedback_message = {
            "type": "performance_feedback",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        send_message(
            sender="feedback_engine",
            receiver=agent_name,
            message_type="feedback",
            content=feedback_message,
            metadata={"source": "feedback_loop"}
        )
        
        log_event(
            "performance_feedback",
            "feedback_engine",
            "feedback",
            {
                "agent": agent_name,
                "success_rate": metrics.get("success_rate", 0.0),
                "trend": metrics.get("trend", "unknown")
            }
        )
        
        self.feedback_history.append({
            "agent": agent_name,
            "metrics": metrics,
            "timestamp": feedback_message["timestamp"]
        })
    
    def _trigger_evolution_proposal(self, agent_name: str, metrics: Dict[str, Any]):
        from datetime import datetime
        
        now = datetime.utcnow().timestamp()
        last_time = self._last_evolution_proposal.get(agent_name, 0.0)
        if (now - last_time) < self._evolution_cooldown_seconds:
            return
        self._last_evolution_proposal[agent_name] = now
        
        trend = metrics.get("trend", "stable")
        success_rate = metrics.get("success_rate", 0.0)
        recent_performance = metrics.get("recent_performance", 0.0)
        
        if trend != "declining" and recent_performance >= 0.4 and success_rate >= 0.3:
            return
        
        try:
            from core.mutation_proposer import propose_mutation as llm_propose_mutation
            from core.data_logger import get_trajectories
            
            recent_trajectories = []
            for entry in get_trajectories(agent_name=agent_name, limit=20):
                prompt = entry.get("prompt", "")
                response = entry.get("response", "")
                if prompt or response:
                    recent_trajectories.append(f"{prompt} | {response}")
            
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(llm_propose_mutation(
                    agent_name=agent_name,
                    performance=metrics,
                    recent_trajectories=recent_trajectories or None,
                ))
                task.add_done_callback(lambda t: self._log_evolution_proposal(agent_name, t.result()))
        except Exception as exc:
            print(f"[FEEDBACK] Evolution proposal skipped: {exc}")
    
    def _log_evolution_proposal(self, agent_name: str, proposal):
        if not proposal:
            return
        log_event(
            "evolution_triggered",
            agent_name,
            "feedback",
            {
                "mutation_type": proposal.get("mutation_type"),
                "description": proposal.get("description"),
                "source": "feedback_loop"
            }
        )
    
    def _save_analysis(self, session_id: str, results: Dict[str, Any]):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        analysis_file = self.feedback_dir / f"analysis_{session_id}_{timestamp}.json"
        
        # Ensure directory exists before writing
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        with open(analysis_file, "w") as f:
            json.dump({
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }, f, indent=2)
    
    def get_agent_performance(self, agent_name: str) -> Dict[str, Any]:
        if agent_name in self.agent_metrics:
            return self.agent_metrics[agent_name].get_metrics()
        return {}
    
    def get_all_performance(self) -> Dict[str, Dict]:
        return {agent: metrics.get_metrics() for agent, metrics in self.agent_metrics.items()}
    
    def get_feedback_history(self, agent_name: str = None, limit: int = 10) -> List[Dict]:
        if agent_name:
            history = [f for f in self.feedback_history if f["agent"] == agent_name]
        else:
            history = self.feedback_history
        
        return history[-limit:]


_feedback_loop = None

def get_feedback_loop() -> FeedbackLoop:
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackLoop()
    return _feedback_loop

def analyze_session(session_id: str) -> Dict[str, Any]:
    loop = get_feedback_loop()
    return loop.analyze_session(session_id)

def get_agent_performance(agent_name: str) -> Dict[str, Any]:
    loop = get_feedback_loop()
    return loop.get_agent_performance(agent_name)

def get_all_performance() -> Dict[str, Dict]:
    loop = get_feedback_loop()
    return loop.get_all_performance()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Feedback loop for performance tracking")
    parser.add_argument("--analyze", help="Analyze session ID")
    parser.add_argument("--performance", action="store_true", help="Show all agent performance")
    parser.add_argument("--agent", help="Show performance for specific agent")
    
    args = parser.parse_args()
    
    if args.analyze:
        results = analyze_session(args.analyze)
        print(json.dumps(results, indent=2))
    elif args.performance:
        perf = get_all_performance()
        print(json.dumps(perf, indent=2))
    elif args.agent:
        perf = get_agent_performance(args.agent)
        print(json.dumps(perf, indent=2))
    else:
        parser.print_help()
