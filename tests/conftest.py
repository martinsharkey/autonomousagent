"""pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ollama():
    """Mock ChatOllama for tests."""
    with patch('core.ollama_client.ChatOllama') as mock_class:
        # Create a mock instance
        mock_instance = MagicMock()
        
        # When invoke() is called, return a mock response
        mock_response = MagicMock()
        mock_response.content = "test response from mocked model"
        mock_instance.invoke.return_value = mock_response
        
        # When the class is instantiated, return the mock instance
        mock_class.return_value = mock_instance
        
        yield mock_instance


@pytest.fixture
def mock_goals_store():
    """Mock goal store for tests."""
    mock_store = MagicMock()
    mock_store.create_goal.return_value = "goal_123"
    mock_store.get_status.return_value = {"status": "pending"}
    yield mock_store


@pytest.fixture
def mock_ollama_for_all_agents():
    """Patch ChatOllama for all agent imports."""
    with patch('core.ollama_client.ChatOllama') as mock_class:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "mocked agent response"
        mock_instance.invoke.return_value = mock_response
        mock_class.return_value = mock_instance
        yield mock_instance
