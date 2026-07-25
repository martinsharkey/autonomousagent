import os
import time
from typing import Dict, Optional
from pathlib import Path
from governance.decision_logger import DecisionLogger

MODEL_REGISTRY = {
    "Qwen2.5-7B-Instruct": {
        "model": "qwen2.5:7b",
        "context_size": 32768,
        "memory_gb": 3.8,
        "specialized_for": "mission alignment voting",
        "temperature": 0.3
    },
    "DeepSeek-Coder-6.7B-Instruct": {
        "model": "deepseek-coder:6.7b",
        "context_size": 4096,
        "memory_gb": 3.6,
        "specialized_for": "test result analysis",
        "temperature": 0.2
    },
    "Phi-4-Mini": {
        "model": "phi4-mini",
        "context_size": 8192,
        "memory_gb": 2.5,
        "specialized_for": "security audit",
        "temperature": 0.1
    },
    "Qwen2.5-14B-Instruct": {
        "model": "qwen2.5:14b",
        "context_size": 32768,
        "memory_gb": 7.5,
        "specialized_for": "rollback assessment",
        "temperature": 0.2
    }
}

class MLLMLoader:
    def __init__(self, vram_budget_gb: int = 7):
        self.vram_budget = vram_budget_gb * 1024
        self.loaded_models: Dict[str, Dict] = {}
        self.vram_usage: Dict[str, int] = {}
        self.decision_logger = DecisionLogger()
    
    def load_model(self, model_name: str, force: bool = False):
        if model_name not in MODEL_REGISTRY:
            raise ValueError(f"Model {model_name} not in registry")
        
        model_config = MODEL_REGISTRY[model_name]
        model_footprint = int(model_config["memory_gb"] * 1024)
        current_usage = sum(self.vram_usage.values())
        
        if current_usage + model_footprint > self.vram_budget:
            if self.loaded_models:
                lru_model = min(self.loaded_models, 
                               key=lambda m: self.loaded_models[m]["last_used"])
                print(f"[MLLM] Evicting {lru_model} to free {self.vram_usage[lru_model]}MB")
                self.unload_model(lru_model)
            else:
                raise MemoryError(f"Cannot load {model_name} - insufficient VRAM budget")
        
        if model_name not in self.loaded_models or force:
            print(f"[MLLM] Loading {model_name} ({model_footprint}MB)...")
            from langchain_community.chat_models import ChatOllama
            
            model = ChatOllama(
                model=model_config["model"],
                temperature=model_config["temperature"],
                base_url="http://localhost:11434"
            )
            
            self.loaded_models[model_name] = {
                "model": model,
                "config": model_config,
                "last_used": time.time()
            }
            self.vram_usage[model_name] = model_footprint
        
        self.loaded_models[model_name]["last_used"] = time.time()
        return self.loaded_models[model_name]["model"]
    
    def unload_model(self, model_name: str):
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            del self.vram_usage[model_name]
            print(f"[MLLM] Unloaded {model_name}")
    
    def get_current_usage(self) -> Dict[str, int]:
        return self.vram_usage.copy()
    
    def get_total_usage_mb(self) -> int:
        return sum(self.vram_usage.values())
    
    def log_inference(self, model_name: str, input_tokens: int, 
                     output_tokens: int, latency_ms: float, 
                     mutation_id: str = None):
        self.decision_logger.log(
            decision_type="MODEL_INFERENCE",
            metadata={
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "tokens_per_second": (input_tokens + output_tokens) / (latency_ms / 1000) if latency_ms > 0 else 0
            },
            mutation_id=mutation_id,
            model_used=model_name
        )

_mllm_loader = None

def get_mllm_loader() -> MLLMLoader:
    global _mllm_loader
    if _mllm_loader is None:
        _mllm_loader = MLLMLoader()
    return _mllm_loader

def load_mllm(model_name: str) -> any:
    loader = get_mllm_loader()
    return loader.load_model(model_name)
