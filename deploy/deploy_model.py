import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil

from governance.audit_log import log_event
from governance.consensus import ConsensusEngine

DEPLOYMENT_DIR = "deployments"
ACTIVE_MODELS_DIR = "active_models"

class ModelDeployer:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.deployment_dir = Path(DEPLOYMENT_DIR) / agent_name
        self.deployment_dir.mkdir(parents=True, exist_ok=True)
        self.active_models_dir = Path(ACTIVE_MODELS_DIR)
        self.active_models_dir.mkdir(parents=True, exist_ok=True)
        self.active_model_link = self.active_models_dir / f"{agent_name}_active"
        
        self.deployment_history = []
    
    def validate_model(self, model_path: str) -> Dict[str, Any]:
        model_path = Path(model_path)
        
        if not model_path.exists():
            return {"valid": False, "error": "Model path does not exist"}
        
        config_file = model_path / "config.json"
        if not config_file.exists():
            return {"valid": False, "error": "Model config.json not found"}
        
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except Exception as e:
            return {"valid": False, "error": f"Failed to load config: {str(e)}"}
        
        if config.get("agent") != self.agent_name:
            return {"valid": False, "error": f"Model agent mismatch: expected {self.agent_name}, got {config.get('agent')}"}
        
        hash_file = model_path / "hash.txt"
        if not hash_file.exists():
            return {"valid": False, "error": "Model hash.txt not found"}
        
        import hashlib
        with open(config_file, "r") as f:
            config_content = f.read()
        computed_hash = hashlib.sha256(config_content.encode()).hexdigest()
        
        with open(hash_file, "r") as f:
            stored_hash = f.read().strip()
        
        if computed_hash != stored_hash:
            return {"valid": False, "error": "Model hash verification failed"}
        
        return {
            "valid": True,
            "model_name": config.get("version"),
            "base_model": config.get("base_model"),
            "metrics": config.get("metrics", {})
        }
    
    def check_governance(self, model_path: str) -> Dict[str, Any]:
        validation = self.validate_model(model_path)
        if not validation["valid"]:
            return {
                "approved": False,
                "reason": "Model validation failed",
                "details": validation
            }
        
        metrics = validation.get("metrics", {})
        min_accuracy = 0.7
        min_reward = 0.6
        
        accuracy = metrics.get("val_accuracy", 0.0)
        avg_reward = metrics.get("avg_reward", 0.0)
        
        if accuracy < min_accuracy:
            return {
                "approved": False,
                "reason": f"Model accuracy {accuracy:.2f} below threshold {min_accuracy}",
                "metrics": metrics
            }
        
        if avg_reward < min_reward:
            return {
                "approved": False,
                "reason": f"Model reward {avg_reward:.2f} below threshold {min_reward}",
                "metrics": metrics
            }
        
        return {
            "approved": True,
            "reason": "Model passed governance checks",
            "metrics": metrics
        }
    
    def deploy(self, model_path: str, force: bool = False) -> Dict[str, Any]:
        governance = self.check_governance(model_path)
        
        if not governance["approved"] and not force:
            deployment_record = {
                "status": "rejected",
                "model_path": model_path,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": governance["reason"],
                "governance": governance
            }
            self._save_deployment_record(deployment_record)
            
            log_event(
                "deployment_rejected",
                "system",
                "model_deployment",
                {"agent": self.agent_name, "model": model_path, "reason": governance["reason"]}
            )
            
            return deployment_record
        
        previous_active = self.get_active_model()
        
        try:
            model_path = Path(model_path)
            
            if self.active_model_link.exists() or self.active_model_link.is_symlink():
                self.active_model_link.unlink()
            
            self.active_model_link.symlink_to(model_path.resolve(), target_is_directory=True)
            
            deployment_record = {
                "status": "success",
                "model_path": str(model_path),
                "previous_model": str(previous_active) if previous_active else None,
                "timestamp": datetime.utcnow().isoformat(),
                "governance": governance
            }
            
            self._save_deployment_record(deployment_record)
            self.deployment_history.append(deployment_record)
            
            log_event(
                "deployment_success",
                "system",
                "model_deployment",
                {
                    "agent": self.agent_name,
                    "model": str(model_path),
                    "previous": str(previous_active) if previous_active else None
                }
            )
            
            return deployment_record
        
        except Exception as e:
            deployment_record = {
                "status": "failed",
                "model_path": model_path,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            self._save_deployment_record(deployment_record)
            
            log_event(
                "deployment_failed",
                "system",
                "model_deployment",
                {"agent": self.agent_name, "model": model_path, "error": str(e)}
            )
            
            return deployment_record
    
    def rollback(self) -> Dict[str, Any]:
        if len(self.deployment_history) < 2:
            return {"status": "failed", "error": "No previous deployment to rollback to"}
        
        previous_deployment = self.deployment_history[-2]
        
        if previous_deployment["status"] != "success":
            return {"status": "failed", "error": "Previous deployment was not successful"}
        
        previous_model = previous_deployment["model_path"]
        
        return self.deploy(previous_model, force=True)
    
    def get_active_model(self) -> Optional[Path]:
        if self.active_model_link.exists() and self.active_model_link.is_symlink():
            return Path(os.readlink(self.active_model_link))
        return None
    
    def _save_deployment_record(self, record: Dict):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        record_file = self.deployment_dir / f"deployment_{timestamp}.json"
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)
    
    def list_deployments(self) -> List[Dict]:
        deployments = []
        for record_file in sorted(self.deployment_dir.glob("deployment_*.json"), reverse=True):
            with open(record_file, "r") as f:
                deployments.append(json.load(f))
        return deployments
    
    def get_deployment_status(self) -> Dict[str, Any]:
        active_model = self.get_active_model()
        
        status = {
            "agent": self.agent_name,
            "active_model": str(active_model) if active_model else None,
            "total_deployments": len(self.deployment_history),
            "latest_deployment": self.deployment_history[-1] if self.deployment_history else None
        }
        
        return status


def deploy_model(
    agent_name: str,
    model_path: str,
    force: bool = False
) -> Dict[str, Any]:
    deployer = ModelDeployer(agent_name)
    return deployer.deploy(model_path, force)


def rollback_deployment(agent_name: str) -> Dict[str, Any]:
    deployer = ModelDeployer(agent_name)
    return deployer.rollback()


def get_active_model(agent_name: str) -> Optional[str]:
    deployer = ModelDeployer(agent_name)
    active = deployer.get_active_model()
    return str(active) if active else None


def list_deployments(agent_name: str) -> List[Dict]:
    deployer = ModelDeployer(agent_name)
    return deployer.list_deployments()


def get_deployment_status(agent_name: str) -> Dict[str, Any]:
    deployer = ModelDeployer(agent_name)
    return deployer.get_deployment_status()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy trained models with governance gates")
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--deploy", help="Deploy model from path")
    parser.add_argument("--rollback", action="store_true", help="Rollback to previous deployment")
    parser.add_argument("--status", action="store_true", help="Show deployment status")
    parser.add_argument("--list", action="store_true", help="List all deployments")
    parser.add_argument("--force", action="store_true", help="Force deployment bypassing governance")
    
    args = parser.parse_args()
    
    if args.deploy:
        result = deploy_model(args.agent, args.deploy, args.force)
        print(json.dumps(result, indent=2))
    elif args.rollback:
        result = rollback_deployment(args.agent)
        print(json.dumps(result, indent=2))
    elif args.status:
        result = get_deployment_status(args.agent)
        print(json.dumps(result, indent=2))
    elif args.list:
        result = list_deployments(args.agent)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
