import json
import os
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

METRICS_DIR = "metrics"

class SystemMonitor:
    def __init__(self):
        self.metrics_dir = Path(METRICS_DIR)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history = []
    
    def get_system_metrics(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count()
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent,
                "used_gb": memory.used / (1024**3)
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent
            }
        }
        
        return metrics
    
    def check_health(self) -> Dict[str, Any]:
        metrics = self.get_system_metrics()
        
        health_status = "healthy"
        alerts = []
        
        if metrics["cpu"]["percent"] > 80:
            alerts.append({
                "level": "warning",
                "message": f"High CPU usage: {metrics['cpu']['percent']}%"
            })
            health_status = "degraded"
        
        if metrics["memory"]["percent"] > 85:
            alerts.append({
                "level": "warning",
                "message": f"High memory usage: {metrics['memory']['percent']}%"
            })
            health_status = "degraded"
        
        if metrics["disk"]["percent"] > 90:
            alerts.append({
                "level": "critical",
                "message": f"Disk space critical: {metrics['disk']['percent']}% used"
            })
            health_status = "critical"
        
        if metrics["memory"]["available_gb"] < 2.0:
            alerts.append({
                "level": "critical",
                "message": f"Low available memory: {metrics['memory']['available_gb']:.2f}GB"
            })
            health_status = "critical"
        
        return {
            "status": health_status,
            "metrics": metrics,
            "alerts": alerts,
            "timestamp": metrics["timestamp"]
        }
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        from deploy.deploy_model import get_active_model, get_deployment_status
        
        active_model = get_active_model(agent_name)
        deployment_status = get_deployment_status(agent_name)
        
        status = {
            "agent": agent_name,
            "active_model": str(active_model) if active_model else None,
            "deployment_status": deployment_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return status
    
    def get_all_agents_status(self) -> Dict[str, Dict]:
        agents = ["autobot", "alpha_evaluator", "beta_worker"]
        return {agent: self.get_agent_status(agent) for agent in agents}
    
    def save_metrics_snapshot(self):
        metrics = self.get_system_metrics()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_file = self.metrics_dir / f"metrics_{timestamp}.json"
        
        with open(snapshot_file, "w") as f:
            json.dump(metrics, f, indent=2)
        
        self.metrics_history.append(metrics)
        return str(snapshot_file)
    
    def get_metrics_history(self, limit: int = 10) -> List[Dict]:
        metric_files = sorted(self.metrics_dir.glob("metrics_*.json"), reverse=True)
        
        history = []
        for metric_file in metric_files[:limit]:
            with open(metric_file, "r") as f:
                history.append(json.load(f))
        
        return history
    
    def export_metrics(self, output_file: str, format: str = "json"):
        history = self.get_metrics_history(limit=1000)
        
        if format == "json":
            with open(output_file, "w") as f:
                json.dump(history, f, indent=2)
        elif format == "csv":
            import csv
            if history:
                with open(output_file, "w", newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=history[0].keys())
                    writer.writeheader()
                    for row in history:
                        writer.writerow(row)
        
        return len(history)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        history = self.get_metrics_history(limit=100)
        
        if not history:
            return {"error": "No metrics history available"}
        
        avg_cpu = sum(m["cpu"]["percent"] for m in history) / len(history)
        avg_memory = sum(m["memory"]["percent"] for m in history) / len(history)
        avg_disk = sum(m["disk"]["percent"] for m in history) / len(history)
        
        return {
            "period": f"Last {len(history)} snapshots",
            "avg_cpu_percent": avg_cpu,
            "avg_memory_percent": avg_memory,
            "avg_disk_percent": avg_disk,
            "min_available_memory_gb": min(m["memory"]["available_gb"] for m in history),
            "max_cpu_percent": max(m["cpu"]["percent"] for m in history),
            "timestamp": datetime.utcnow().isoformat()
        }


class AgentMonitor:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.metrics_dir = Path(METRICS_DIR) / agent_name
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def log_agent_metric(self, metric_type: str, value: Any, metadata: Dict = None):
        metric = {
            "agent": self.agent_name,
            "metric_type": metric_type,
            "value": value,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        metric_file = self.metrics_dir / f"{metric_type}_{timestamp}.json"
        
        with open(metric_file, "w") as f:
            json.dump(metric, f, indent=2)
        
        return metric
    
    def get_agent_metrics(self, metric_type: str = None, limit: int = 10) -> List[Dict]:
        if metric_type:
            pattern = f"{metric_type}_*.json"
        else:
            pattern = "*.json"
        
        metric_files = sorted(self.metrics_dir.glob(pattern), reverse=True)
        
        metrics = []
        for metric_file in metric_files[:limit]:
            with open(metric_file, "r") as f:
                metrics.append(json.load(f))
        
        return metrics
    
    def get_agent_summary(self) -> Dict[str, Any]:
        from core.data_logger import get_trajectories
        from deploy.deploy_model import get_active_model
        
        trajectories = get_trajectories(agent_name=self.agent_name, limit=100)
        active_model = get_active_model(self.agent_name)
        
        if trajectories:
            avg_reward = sum(t.get("reward", 0.0) for t in trajectories) / len(trajectories)
            total_trajectories = len(trajectories)
        else:
            avg_reward = 0.0
            total_trajectories = 0
        
        return {
            "agent": self.agent_name,
            "active_model": str(active_model) if active_model else None,
            "total_trajectories": total_trajectories,
            "average_reward": avg_reward,
            "timestamp": datetime.utcnow().isoformat()
        }


def get_system_health() -> Dict[str, Any]:
    monitor = SystemMonitor()
    return monitor.check_health()


def get_system_metrics() -> Dict[str, Any]:
    monitor = SystemMonitor()
    return monitor.get_system_metrics()


def get_agent_status(agent_name: str) -> Dict[str, Any]:
    monitor = SystemMonitor()
    return monitor.get_agent_status(agent_name)


def get_all_agents_status() -> Dict[str, Dict]:
    monitor = SystemMonitor()
    return monitor.get_all_agents_status()


def log_agent_metric(agent_name: str, metric_type: str, value: Any, metadata: Dict = None):
    monitor = AgentMonitor(agent_name)
    return monitor.log_agent_metric(metric_type, value, metadata)


def get_agent_metrics(agent_name: str, metric_type: str = None, limit: int = 10) -> List[Dict]:
    monitor = AgentMonitor(agent_name)
    return monitor.get_agent_metrics(metric_type, limit)


def get_performance_summary() -> Dict[str, Any]:
    monitor = SystemMonitor()
    return monitor.get_performance_summary()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor system and agent health")
    parser.add_argument("--health", action="store_true", help="Check system health")
    parser.add_argument("--metrics", action="store_true", help="Get current system metrics")
    parser.add_argument("--agents", action="store_true", help="Get all agents status")
    parser.add_argument("--agent", help="Get specific agent status")
    parser.add_argument("--summary", action="store_true", help="Get performance summary")
    parser.add_argument("--save", action="store_true", help="Save metrics snapshot")
    
    args = parser.parse_args()
    
    if args.health:
        result = get_system_health()
        print(json.dumps(result, indent=2))
    elif args.metrics:
        result = get_system_metrics()
        print(json.dumps(result, indent=2))
    elif args.agents:
        result = get_all_agents_status()
        print(json.dumps(result, indent=2))
    elif args.agent:
        result = get_agent_status(args.agent)
        print(json.dumps(result, indent=2))
    elif args.summary:
        result = get_performance_summary()
        print(json.dumps(result, indent=2))
    elif args.save:
        monitor = SystemMonitor()
        snapshot = monitor.save_metrics_snapshot()
        print(f"Metrics saved to: {snapshot}")
    else:
        parser.print_help()
