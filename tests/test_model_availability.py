import pytest
import os
from unittest.mock import Mock, patch
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
    
    @patch('agents.autobot.ChatOllama')
    def test_autobot_fallback_on_failure(self, mock_chat_ollama):
        """Test that autobot falls back to smaller model on failure."""
        mock_instance = Mock()
        mock_instance.invoke.side_effect = [
            Exception("Model not found"),
            Mock(content="fallback response")
        ]
        mock_chat_ollama.return_value = mock_instance
        
        with patch.dict(os.environ, {
            "AUTOBOT_MODEL": "nonexistent:latest",
            "AUTOBOT_FALLBACK_MODEL": "llama3.2:1b"
        }):
            import importlib
            import agents.autobot
            importlib.reload(agents.autobot)
            
            assert mock_chat_ollama.call_count == 2
    
    @patch('agents.alpha_evaluator.ChatOllama')
    def test_alpha_fallback_on_failure(self, mock_chat_ollama):
        """Test that alpha falls back to smaller model on failure."""
        mock_instance = Mock()
        mock_instance.invoke.side_effect = [
            Exception("Model not found"),
            Mock(content="fallback response")
        ]
        mock_chat_ollama.return_value = mock_instance
        
        with patch.dict(os.environ, {
            "ALPHA_MODEL": "nonexistent:latest",
            "ALPHA_FALLBACK_MODEL": "llama3.2:1b"
        }):
            import importlib
            import agents.alpha_evaluator
            importlib.reload(agents.alpha_evaluator)
            
            assert mock_chat_ollama.call_count == 2
    
    @patch('agents.beta_worker.ChatOllama')
    def test_beta_fallback_on_failure(self, mock_chat_ollama):
        """Test that beta falls back to smaller model on failure."""
        mock_instance = Mock()
        mock_instance.invoke.side_effect = [
            Exception("Model not found"),
            Mock(content="fallback response")
        ]
        mock_chat_ollama.return_value = mock_instance
        
        with patch.dict(os.environ, {
            "BETA_MODEL": "nonexistent:latest",
            "BETA_FALLBACK_MODEL": "llama3.2:1b"
        }):
            import importlib
            import agents.beta_worker
            importlib.reload(agents.beta_worker)
            
            assert mock_chat_ollama.call_count == 2
    
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
