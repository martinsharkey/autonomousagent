import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

TRAJECTORY_DIR = "trajectories"

class TrajectoryLogger:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.trajectory_dir = Path(TRAJECTORY_DIR) / self.session_id
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)
        self.trajectory_file = self.trajectory_dir / "trajectory.jsonl"
        self.metadata_file = self.trajectory_dir / "metadata.json"
        
        self._write_metadata()
    
    def _write_metadata(self):
        metadata = {
            "session_id": self.session_id,
            "created_at": datetime.utcnow().isoformat(),
            "trajectories": []
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def log_trajectory(
        self,
        agent_name: str,
        state: Dict[str, Any],
        prompt: str,
        response: str,
        reward: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        trajectory_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "state": state,
            "prompt": prompt,
            "response": response,
            "reward": reward,
            "metadata": metadata or {}
        }
        
        with open(self.trajectory_file, "a") as f:
            f.write(json.dumps(trajectory_entry) + "\n")
        
        self._update_metadata(agent_name, trajectory_entry["timestamp"])
        
        return trajectory_entry
    
    def _update_metadata(self, agent_name: str, timestamp: str):
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        
        metadata["trajectories"].append({
            "agent": agent_name,
            "timestamp": timestamp
        })
        
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def get_trajectories(self, agent_name: str = None, limit: int = None) -> List[Dict]:
        if not self.trajectory_file.exists():
            return []
        
        trajectories = []
        with open(self.trajectory_file, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                if agent_name is None or entry["agent"] == agent_name:
                    trajectories.append(entry)
        
        if limit:
            trajectories = trajectories[-limit:]
        
        return trajectories
    
    def get_training_data(self, min_reward: float = None) -> List[Dict]:
        trajectories = self.get_trajectories()
        
        if min_reward is not None:
            trajectories = [t for t in trajectories if t.get("reward") is not None and t["reward"] >= min_reward]
        
        training_data = []
        for t in trajectories:
            training_data.append({
                "input": t["prompt"],
                "output": t["response"],
                "reward": t.get("reward", 0.0),
                "agent": t["agent"],
                "state": t["state"]
            })
        
        return training_data
    
    def export_for_training(self, output_file: str, format: str = "jsonl"):
        training_data = self.get_training_data()
        
        if format == "jsonl":
            with open(output_file, "w") as f:
                for entry in training_data:
                    f.write(json.dumps(entry) + "\n")
        elif format == "json":
            with open(output_file, "w") as f:
                json.dump(training_data, f, indent=2)
        
        return len(training_data)


_logger_instances: Dict[str, TrajectoryLogger] = {}

def get_logger(session_id: str = None) -> TrajectoryLogger:
    if session_id is None:
        session_id = "default"
    
    if session_id not in _logger_instances:
        _logger_instances[session_id] = TrajectoryLogger(session_id)
    
    return _logger_instances[session_id]

def log_trajectory(
    agent_name: str,
    state: Dict[str, Any],
    prompt: str,
    response: str,
    reward: Optional[float] = None,
    session_id: str = None,
    metadata: Optional[Dict[str, Any]] = None
):
    logger = get_logger(session_id)
    return logger.log_trajectory(agent_name, state, prompt, response, reward, metadata)

def get_trajectories(session_id: str = None, agent_name: str = None, limit: int = None) -> List[Dict]:
    logger = get_logger(session_id)
    return logger.get_trajectories(agent_name, limit)

def get_training_data(session_id: str = None, min_reward: float = None) -> List[Dict]:
    logger = get_logger(session_id)
    return logger.get_training_data(min_reward)

def export_for_training(session_id: str, output_file: str, format: str = "jsonl") -> int:
    logger = get_logger(session_id)
    return logger.export_for_training(output_file, format)
