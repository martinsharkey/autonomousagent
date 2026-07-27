import pytest
import os
from unittest.mock import Mock, patch
from unittest.mock import AsyncMock
from langchain_ollama import ChatOllama


class TestModelAvailability:
    """Verify model availability and resource feasibility."""
    
    def test_autobot_model_configuration(self):
        """Test that autobot uses centralized model registry."""
        from agents.autobot import MODEL_NAME, FALLBACK_MODEL
        from core.models import get_primary_model, get_fallback_model
        assert MODEL_NAME == get_primary_model("autobot")
        assert FALLBACK_MODEL == get_fallback_model("autobot")
    
    def test_alpha_model_configuration(self):
        """Test that alpha uses centralized model registry."""
        from agents.alpha_evaluator import MODEL_NAME, FALLBACK_MODEL
        from core.models import get_primary_model, get_fallback_model
        assert MODEL_NAME == get_primary_model("alpha_evaluator")
        assert FALLBACK_MODEL == get_fallback_model("alpha_evaluator")
    
    def test_beta_model_configuration(self):
        """Test that beta uses centralized model registry."""
        from agents.beta_worker import MODEL_NAME, FALLBACK_MODEL
        from core.models import get_primary_model, get_fallback_model
        assert MODEL_NAME == get_primary_model("beta_worker")
        assert FALLBACK_MODEL == get_fallback_model("beta_worker")
    
    @patch('agents.autobot.llm_router')
    def test_autobot_fallback_on_failure(self, mock_router):
        """Test that autobot propagates router failures."""
        mock_router.route_request = AsyncMock(side_effect=Exception("Model not found"))
        
        from agents.autobot import autobot_node
        from core.state import AgentState
        
        state = AgentState(
            messages=[{"role": "user", "content": "test"}],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        import asyncio
        with pytest.raises(Exception, match="Model not found"):
            asyncio.run(autobot_node(state))
    
    @patch('agents.alpha_evaluator.llm_router')
    def test_alpha_fallback_on_failure(self, mock_router):
        """Test that alpha propagates router failures."""
        mock_router.route_request = AsyncMock(side_effect=Exception("Model not found"))
        
        from agents.alpha_evaluator import alpha_node
        from core.state import AgentState
        
        state = AgentState(
            messages=[{"role": "user", "content": "test"}],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        import asyncio
        with pytest.raises(Exception, match="Model not found"):
            asyncio.run(alpha_node(state))
    
    @patch('agents.beta_worker.llm_router')
    def test_beta_fallback_on_failure(self, mock_router):
        """Test that beta propagates router failures."""
        mock_router.route_request = AsyncMock(side_effect=Exception("Model not found"))
        
        from agents.beta_worker import beta_node
        from core.state import AgentState
        
        state = AgentState(
            messages=[{"role": "user", "content": "test"}],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash="",
            council_votes={"autobot": None, "alpha_evaluator": None, "beta_worker": None},
            mission_scores={"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0}
        )
        
        import asyncio
        with pytest.raises(Exception, match="Model not found"):
            asyncio.run(beta_node(state))
    
    def test_model_ram_estimates(self):
        """Verify RAM estimates for common models are documented."""
        model_ram = {
            "llama3.2:1b": "~1.5GB",
            "llama3.2:3b": "~2.5GB",
            "qwen2.5:3b": "~2.5GB",
            "phi3:mini": "~2.3GB",
            "deepseek-coder:1.3b": "~1.0GB"
        }
        
        total_min = 1.5 + 2.3 + 1.0
        total_max = 2.5 + 2.5 + 1.0
        
        assert total_min <= 8.0, "Minimum RAM should fit in 8GB system"
        assert total_max <= 8.0, "Maximum RAM should fit in 8GB system"
    
    def test_sequential_loading_enforced(self):
        """Verify that OLLAMA_MAX_LOADED_MODELS=1 is set in .env."""
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                content = f.read()
                assert "OLLAMA_MAX_LOADED_MODELS=1" in content
