import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict

from core.data_logger import get_trajectories, get_training_data
from core.communication import send_message, get_message_bus
from governance.audit_log import log_event

LEARNING_DIR = "learning"

class TrajectoryAnalyzer:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.learning_dir = Path(LEARNING_DIR) / agent_name
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        self.patterns = []
        self.successful_strategies = []
        self.failed_strategies = []
    
    def analyze_trajectories(self, session_id: str, min_reward: float = 0.5) -> Dict[str, Any]:
        trajectories = get_trajectories(session_id, agent_name=self.agent_name)
        
        if not trajectories:
            return {"error": "No trajectories found"}
        
        analysis = {
            "agent": self.agent_name,
            "session_id": session_id,
            "total_trajectories": len(trajectories),
            "successful": [],
            "failed": [],
            "patterns": [],
            "recommendations": []
        }
        
        for traj in trajectories:
            reward = traj.get("reward", 0.0)
            
            if reward >= min_reward:
                analysis["successful"].append(traj)
            else:
                analysis["failed"].append(traj)
        
        patterns = self._extract_patterns(trajectories)
        analysis["patterns"] = patterns
        
        recommendations = self._generate_recommendations(analysis)
        analysis["recommendations"] = recommendations
        
        self._save_analysis(analysis)
        
        return analysis
    
    def _extract_patterns(self, trajectories: List[Dict]) -> List[Dict]:
        patterns = []
        
        prompt_patterns = defaultdict(list)
        for traj in trajectories:
            prompt = traj.get("prompt", "")
            reward = traj.get("reward", 0.0)
            prompt_patterns[prompt[:100]].append(reward)
        
        for prompt_prefix, rewards in prompt_patterns.items():
            if len(rewards) >= 2:
                avg_reward = sum(rewards) / len(rewards)
                patterns.append({
                    "type": "prompt_pattern",
                    "pattern": prompt_prefix,
                    "occurrences": len(rewards),
                    "avg_reward": avg_reward,
                    "consistent": all(r > 0.5 for r in rewards) or all(r < 0.5 for r in rewards)
                })
        
        response_patterns = defaultdict(list)
        for traj in trajectories:
            response = traj.get("response", "")
            reward = traj.get("reward", 0.0)
            response_patterns[response[:100]].append(reward)
        
        for response_prefix, rewards in response_patterns.items():
            if len(rewards) >= 2:
                avg_reward = sum(rewards) / len(rewards)
                patterns.append({
                    "type": "response_pattern",
                    "pattern": response_prefix,
                    "occurrences": len(rewards),
                    "avg_reward": avg_reward,
                    "consistent": all(r > 0.5 for r in rewards) or all(r < 0.5 for r in rewards)
                })
        
        return patterns
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        recommendations = []
        
        successful = analysis["successful"]
        failed = analysis["failed"]
        
        if len(successful) > len(failed):
            recommendations.append(f"Good performance: {len(successful)} successful vs {len(failed)} failed trajectories")
        else:
            recommendations.append(f"Performance needs improvement: {len(successful)} successful vs {len(failed)} failed trajectories")
        
        for pattern in analysis["patterns"]:
            if pattern["type"] == "prompt_pattern" and pattern["avg_reward"] > 0.7:
                recommendations.append(f"Strong pattern detected: {pattern['pattern'][:50]}... (avg reward: {pattern['avg_reward']:.2f})")
            elif pattern["type"] == "response_pattern" and pattern["avg_reward"] < 0.3:
                recommendations.append(f"Avoid response pattern: {pattern['pattern'][:50]}... (avg reward: {pattern['avg_reward']:.2f})")
        
        if len(failed) > 0:
            failed_rewards = [t.get("reward", 0.0) for t in failed]
            avg_failed_reward = sum(failed_rewards) / len(failed_rewards)
            recommendations.append(f"Average reward for failed trajectories: {avg_failed_reward:.2f}")
        
        return recommendations
    
    def _save_analysis(self, analysis: Dict):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        analysis_file = self.learning_dir / f"analysis_{timestamp}.json"
        
        # Ensure directory exists before writing
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)
    
    def get_learning_history(self, limit: int = 10) -> List[Dict]:
        analysis_files = sorted(self.learning_dir.glob("analysis_*.json"), reverse=True)
        
        history = []
        for analysis_file in analysis_files[:limit]:
            with open(analysis_file, "r") as f:
                history.append(json.load(f))
        
        return history


class LearningEngine:
    def __init__(self):
        self.learning_dir = Path(LEARNING_DIR)
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        self.agent_analyzers = {}
    
    def get_analyzer(self, agent_name: str) -> TrajectoryAnalyzer:
        if agent_name not in self.agent_analyzers:
            self.agent_analyzers[agent_name] = TrajectoryAnalyzer(agent_name)
        return self.agent_analyzers[agent_name]
    
    def learn_from_session(self, session_id: str, agents: List[str] = None) -> Dict[str, Any]:
        if agents is None:
            agents = ["autobot", "alpha_evaluator", "beta_worker"]
        
        results = {}
        
        for agent_name in agents:
            analyzer = self.get_analyzer(agent_name)
            analysis = analyzer.analyze_trajectories(session_id)
            results[agent_name] = analysis
            
            self._provide_feedback(agent_name, analysis)
        
        self._save_session_learning(session_id, results)
        
        return results
    
    def _provide_feedback(self, agent_name: str, analysis: Dict):
        recommendations = analysis.get("recommendations", [])
        
        if recommendations:
            feedback_message = {
                "type": "learning_feedback",
                "session_id": analysis.get("session_id"),
                "recommendations": recommendations,
                "patterns_count": len(analysis.get("patterns", [])),
                "successful_count": len(analysis.get("successful", [])),
                "failed_count": len(analysis.get("failed", []))
            }
            
            send_message(
                sender="learning_engine",
                receiver=agent_name,
                message_type="feedback",
                content=feedback_message,
                metadata={"source": "learning_engine"}
            )
            
            log_event(
                "learning_feedback",
                "learning_engine",
                "agent_feedback",
                {"agent": agent_name, "recommendations": len(recommendations)}
            )
    
    def _save_session_learning(self, session_id: str, results: Dict):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        learning_file = self.learning_dir / f"session_{session_id}_{timestamp}.json"
        
        with open(learning_file, "w") as f:
            json.dump({
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }, f, indent=2)
    
    def get_session_learning(self, session_id: str) -> Optional[Dict]:
        learning_files = sorted(self.learning_dir.glob(f"session_{session_id}_*.json"), reverse=True)
        
        if learning_files:
            with open(learning_files[0], "r") as f:
                return json.load(f)
        
        return None
    
    def get_learning_summary(self) -> Dict[str, Any]:
        summary = {
            "total_sessions": 0,
            "agents_learned": {},
            "total_patterns": 0,
            "total_recommendations": 0
        }
        
        for agent_name in ["autobot", "alpha_evaluator", "beta_worker"]:
            analyzer = self.get_analyzer(agent_name)
            history = analyzer.get_learning_history(limit=100)
            
            if history:
                summary["agents_learned"][agent_name] = len(history)
                
                for analysis in history:
                    summary["total_patterns"] += len(analysis.get("patterns", []))
                    summary["total_recommendations"] += len(analysis.get("recommendations", []))
        
        summary["total_sessions"] = len(list(self.learning_dir.glob("session_*.json")))
        
        return summary


_learning_engine = None

def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine

def learn_from_session(session_id: str, agents: List[str] = None) -> Dict[str, Any]:
    engine = get_learning_engine()
    return engine.learn_from_session(session_id, agents)

def analyze_agent_trajectories(agent_name: str, session_id: str, min_reward: float = 0.5) -> Dict[str, Any]:
    engine = get_learning_engine()
    analyzer = engine.get_analyzer(agent_name)
    return analyzer.analyze_trajectories(session_id, min_reward)

def get_learning_summary() -> Dict[str, Any]:
    engine = get_learning_engine()
    return engine.get_learning_summary()

def get_session_learning(session_id: str) -> Optional[Dict]:
    engine = get_learning_engine()
    return engine.get_session_learning(session_id)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Learning engine for trajectory analysis")
    parser.add_argument("--learn", help="Learn from session ID")
    parser.add_argument("--analyze", help="Analyze agent trajectories")
    parser.add_argument("--agent", help="Agent name for analysis")
    parser.add_argument("--summary", action="store_true", help="Show learning summary")
    parser.add_argument("--session", help="Get session learning results")
    
    args = parser.parse_args()
    
    if args.learn:
        result = learn_from_session(args.learn)
        print(json.dumps(result, indent=2))
    elif args.analyze and args.agent:
        result = analyze_agent_trajectories(args.agent, args.analyze)
        print(json.dumps(result, indent=2))
    elif args.summary:
        result = get_learning_summary()
        print(json.dumps(result, indent=2))
    elif args.session:
        result = get_session_learning(args.session)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No learning data found for session")
    else:
        parser.print_help()
