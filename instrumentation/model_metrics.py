import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from governance.decision_logger import DecisionLogger

class ModelMetricsCollector:
    """Collects and analyzes model performance metrics"""
    
    def __init__(self, metrics_dir: Path = Path("./metrics")):
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(exist_ok=True)
        self.decision_logger = DecisionLogger()
        self.metrics_file = self.metrics_dir / "model_metrics.jsonl"
    
    def record_inference(self, model_name: str, input_tokens: int,
                        output_tokens: int, latency_ms: float,
                        mutation_id: str = None,
                        accuracy_score: float = None):
        """Log every model invocation for monitoring"""
        
        metrics_record = {
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "tokens_per_second": (input_tokens + output_tokens) / (latency_ms / 1000) if latency_ms > 0 else 0,
            "accuracy_score": accuracy_score,
            "mutation_id": mutation_id
        }
        
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(metrics_record) + "\n")
        
        self.decision_logger.log(
            decision_type="MODEL_INFERENCE",
            metadata=metrics_record,
            mutation_id=mutation_id,
            model_used=model_name
        )
        
        if accuracy_score is not None and accuracy_score < 0.75:
            self._alert_accuracy_degradation(model_name, accuracy_score)
    
    def _alert_accuracy_degradation(self, model_name: str, accuracy: float):
        """Alert when model accuracy drops below threshold"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": "MODEL_ACCURACY_WARNING",
            "model_name": model_name,
            "accuracy": accuracy,
            "threshold": 0.75,
            "severity": "MEDIUM"
        }
        
        with open(self.metrics_dir / "accuracy_alerts.jsonl", "a") as f:
            f.write(json.dumps(alert) + "\n")
        
        self.decision_logger.log(
            decision_type="MODEL_ACCURACY_WARNING",
            metadata={
                "model_name": model_name,
                "accuracy": accuracy,
                "threshold": 0.75
            }
        )
        
        print(f"[METRICS] WARNING: {model_name} accuracy {accuracy:.2f} below threshold 0.75")
    
    def get_model_performance(self, model_name: str, 
                             days: int = 7) -> Dict[str, float]:
        """Get performance metrics for a model over time period"""
        
        cutoff = datetime.now() - timedelta(days=days)
        
        metrics = []
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    if record["model_name"] == model_name:
                        record_time = datetime.fromisoformat(record["timestamp"])
                        if record_time >= cutoff:
                            metrics.append(record)
        
        if not metrics:
            return {
                "avg_latency_ms": 0,
                "avg_tokens_per_second": 0,
                "total_invocations": 0,
                "avg_accuracy": 0
            }
        
        accuracies = [m["accuracy_score"] for m in metrics if m.get("accuracy_score") is not None]
        
        return {
            "avg_latency_ms": sum(m["latency_ms"] for m in metrics) / len(metrics),
            "avg_tokens_per_second": sum(m["tokens_per_second"] for m in metrics) / len(metrics),
            "total_invocations": len(metrics),
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0
        }
    
    def get_all_model_performance(self, days: int = 7) -> Dict[str, Dict]:
        """Get performance for all models"""
        
        cutoff = datetime.now() - timedelta(days=days)
        model_names = set()
        
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    record_time = datetime.fromisoformat(record["timestamp"])
                    if record_time >= cutoff:
                        model_names.add(record["model_name"])
        
        return {
            model: self.get_model_performance(model, days)
            for model in model_names
        }
    
    def recommend_model_swap(self, model_name: str, 
                            threshold_accuracy: float = 0.75) -> bool:
        """Recommend swapping model if performance degrades"""
        
        performance = self.get_model_performance(model_name, days=7)
        
        if performance["avg_accuracy"] < threshold_accuracy:
            print(f"[METRICS] Recommend swapping {model_name} - accuracy {performance['avg_accuracy']:.2f}")
            return True
        
        return False
    
    def export_metrics(self, output_file: str, days: int = 30):
        """Export metrics to file for analysis"""
        
        cutoff = datetime.now() - timedelta(days=days)
        
        with open(output_file, "w") as out:
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    for line in f:
                        record = json.loads(line)
                        record_time = datetime.fromisoformat(record["timestamp"])
                        if record_time >= cutoff:
                            out.write(line)
