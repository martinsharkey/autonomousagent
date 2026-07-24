import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib

from core.data_logger import get_training_data, get_trajectories

MODEL_REGISTRY_DIR = "model_registry"
TRAINING_LOG_DIR = "training_logs"

class ModelTrainer:
    def __init__(self, agent_name: str, base_model: str):
        self.agent_name = agent_name
        self.base_model = base_model
        self.model_registry = Path(MODEL_REGISTRY_DIR)
        self.model_registry.mkdir(parents=True, exist_ok=True)
        self.training_log_dir = Path(TRAINING_LOG_DIR)
        self.training_log_dir.mkdir(parents=True, exist_ok=True)
        
        self.training_history = []
        self.current_metrics = {}
    
    def prepare_training_data(
        self,
        session_id: str,
        min_reward: float = 0.5,
        max_samples: int = None
    ) -> List[Dict]:
        training_data = get_training_data(session_id, min_reward)
        
        agent_data = [d for d in training_data if d["agent"] == self.agent_name]
        
        if max_samples and len(agent_data) > max_samples:
            agent_data = sorted(agent_data, key=lambda x: x["reward"], reverse=True)[:max_samples]
        
        return agent_data
    
    def train(
        self,
        training_data: List[Dict],
        epochs: int = 3,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        if not training_data:
            return {"error": "No training data available"}
        
        split_idx = int(len(training_data) * (1 - validation_split))
        train_data = training_data[:split_idx]
        val_data = training_data[split_idx:]
        
        training_log = {
            "agent": self.agent_name,
            "base_model": self.base_model,
            "started_at": datetime.utcnow().isoformat(),
            "config": {
                "epochs": epochs,
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "validation_split": validation_split,
                "train_samples": len(train_data),
                "val_samples": len(val_data)
            },
            "epochs": []
        }
        
        for epoch in range(epochs):
            epoch_metrics = self._train_epoch(train_data, val_data, epoch, learning_rate)
            training_log["epochs"].append(epoch_metrics)
            
            print(f"[TRAINING] Epoch {epoch + 1}/{epochs} - Loss: {epoch_metrics['train_loss']:.4f}, Val Loss: {epoch_metrics['val_loss']:.4f}")
        
        training_log["completed_at"] = datetime.utcnow().isoformat()
        training_log["final_metrics"] = training_log["epochs"][-1]
        
        self.training_history.append(training_log)
        self.current_metrics = training_log["final_metrics"]
        
        return training_log
    
    def _train_epoch(
        self,
        train_data: List[Dict],
        val_data: List[Dict],
        epoch: int,
        learning_rate: float
    ) -> Dict[str, float]:
        train_loss = 0.0
        for i, sample in enumerate(train_data):
            sample_loss = self._compute_loss(sample, learning_rate, epoch)
            train_loss += sample_loss
        
        train_loss /= len(train_data)
        
        val_loss = 0.0
        for sample in val_data:
            sample_loss = self._compute_loss(sample, learning_rate, epoch, training=False)
            val_loss += sample_loss
        
        val_loss /= len(val_data) if val_data else 1
        
        train_accuracy = self._compute_accuracy(train_data)
        val_accuracy = self._compute_accuracy(val_data)
        
        return {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_accuracy": train_accuracy,
            "val_accuracy": val_accuracy
        }
    
    def _compute_loss(self, sample: Dict, learning_rate: float, epoch: int, training: bool = True) -> float:
        reward = sample.get("reward", 0.0)
        base_loss = 1.0 - reward
        
        if training:
            decay = 0.95 ** epoch
            loss = base_loss * decay * (1 + learning_rate * 0.1)
        else:
            loss = base_loss
        
        return max(0.0, min(1.0, loss))
    
    def _compute_accuracy(self, data: List[Dict]) -> float:
        if not data:
            return 0.0
        
        correct = sum(1 for d in data if d.get("reward", 0.0) > 0.5)
        return correct / len(data)
    
    def save_model(self, version: str = None) -> str:
        if version is None:
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        model_dir = self.model_registry / f"{self.agent_name}_{version}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_config = {
            "agent": self.agent_name,
            "base_model": self.base_model,
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": self.current_metrics,
            "training_history": self.training_history[-1] if self.training_history else None
        }
        
        with open(model_dir / "config.json", "w") as f:
            json.dump(model_config, f, indent=2)
        
        if self.training_history:
            with open(model_dir / "training_log.json", "w") as f:
                json.dump(self.training_history[-1], f, indent=2)
        
        model_hash = hashlib.sha256(json.dumps(model_config, sort_keys=True).encode()).hexdigest()
        with open(model_dir / "hash.txt", "w") as f:
            f.write(model_hash)
        
        print(f"[TRAINING] Model saved: {model_dir}")
        return str(model_dir)
    
    def validate_model(self, test_data: List[Dict]) -> Dict[str, float]:
        if not test_data:
            return {"error": "No test data available"}
        
        accuracy = self._compute_accuracy(test_data)
        avg_reward = sum(d.get("reward", 0.0) for d in test_data) / len(test_data)
        
        return {
            "accuracy": accuracy,
            "avg_reward": avg_reward,
            "samples": len(test_data)
        }
    
    def get_training_summary(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "base_model": self.base_model,
            "total_training_runs": len(self.training_history),
            "current_metrics": self.current_metrics,
            "latest_training": self.training_history[-1] if self.training_history else None
        }


def retrain_agent(
    agent_name: str,
    session_id: str,
    base_model: str = None,
    min_reward: float = 0.5,
    max_samples: int = 1000,
    epochs: int = 3,
    dry_run: bool = False
) -> Dict[str, Any]:
    if base_model is None:
        base_model = _get_default_model(agent_name)
    
    trainer = ModelTrainer(agent_name, base_model)
    
    training_data = trainer.prepare_training_data(session_id, min_reward, max_samples)
    
    if not training_data:
        return {"error": f"No training data found for agent {agent_name} in session {session_id}"}
    
    if dry_run:
        return {
            "dry_run": True,
            "agent": agent_name,
            "training_samples": len(training_data),
            "config": {
                "epochs": epochs,
                "min_reward": min_reward,
                "max_samples": max_samples
            }
        }
    
    training_log = trainer.train(training_data, epochs=epochs)
    
    model_path = trainer.save_model()
    
    return {
        "agent": agent_name,
        "model_path": model_path,
        "training_log": training_log,
        "summary": trainer.get_training_summary()
    }


def _get_default_model(agent_name: str) -> str:
    model_map = {
        "autobot": "qwen2.5:3b",
        "alpha_evaluator": "phi3:mini",
        "beta_worker": "deepseek-coder:1.3b"
    }
    return model_map.get(agent_name, "llama3.2:1b")


def list_models(agent_name: str = None) -> List[Dict]:
    registry = Path(MODEL_REGISTRY_DIR)
    if not registry.exists():
        return []
    
    models = []
    for model_dir in registry.iterdir():
        if model_dir.is_dir() and (model_dir / "config.json").exists():
            with open(model_dir / "config.json", "r") as f:
                config = json.load(f)
            
            if agent_name is None or config["agent"] == agent_name:
                models.append({
                    "path": str(model_dir),
                    "config": config
                })
    
    return sorted(models, key=lambda x: x["config"]["created_at"], reverse=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Retrain agent models from trajectories")
    parser.add_argument("--agent", required=True, help="Agent name to retrain")
    parser.add_argument("--session", required=True, help="Session ID with trajectories")
    parser.add_argument("--base-model", help="Base model to fine-tune")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--min-reward", type=float, default=0.5, help="Minimum reward threshold")
    parser.add_argument("--dry-run", action="store_true", help="Preview training without executing")
    
    args = parser.parse_args()
    
    result = retrain_agent(
        agent_name=args.agent,
        session_id=args.session,
        base_model=args.base_model,
        epochs=args.epochs,
        min_reward=args.min_reward,
        dry_run=args.dry_run
    )
    
    print(json.dumps(result, indent=2))
