import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import END
from core.graph import deterministic_router, autobot_with_cache, alpha_with_cache, beta_with_cache
from core.state import AgentState


class TestDeterministicRouter:
    """Test deterministic_router function for state-based routing."""
    
    def test_ttl_circuit_breaker_at_5(self):
        """Test TTL circuit breaker triggers at exactly 5 loops."""
        state = AgentState(
            messages=[HumanMessage(content="Some task")],
            loop_count=5,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "terminal_fallback"
    
    def test_ttl_circuit_breaker_above_5(self):
        """Test TTL circuit breaker triggers above 5 loops."""
        state = AgentState(
            messages=[HumanMessage(content="Some task")],
            loop_count=10,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "terminal_fallback"
    
    def test_ttl_circuit_breaker_below_5(self):
        """Test TTL circuit breaker does not trigger below 5 loops."""
        state = AgentState(
            messages=[HumanMessage(content="EXECUTE_CODE something")],
            loop_count=4,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_route_to_beta_worker_on_execute_code(self):
        """Test routing to beta_worker when EXECUTE_CODE is in message."""
        state = AgentState(
            messages=[AIMessage(content="EXECUTE_CODE: Create a function")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_route_to_beta_worker_execute_code_in_middle(self):
        """Test routing to beta_worker when EXECUTE_CODE appears in middle of message."""
        state = AgentState(
            messages=[AIMessage(content="I will EXECUTE_CODE now to solve this")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_route_to_alpha_evaluator_on_review_required(self):
        """Test routing to alpha_evaluator when REVIEW_REQUIRED is in message."""
        state = AgentState(
            messages=[AIMessage(content="REVIEW_REQUIRED: Code needs evaluation")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "alpha_evaluator"
    
    def test_route_to_alpha_evaluator_review_in_middle(self):
        """Test routing to alpha_evaluator when REVIEW_REQUIRED appears in middle."""
        state = AgentState(
            messages=[AIMessage(content="The code is REVIEW_REQUIRED by the team")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "alpha_evaluator"
    
    def test_route_to_end_on_consensus_reached(self):
        """Test routing to END when CONSENSUS_REACHED is in message."""
        state = AgentState(
            messages=[AIMessage(content="CONSENSUS_REACHED: All agents agree")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == END
    
    def test_route_to_end_consensus_in_middle(self):
        """Test routing to END when CONSENSUS_REACHED appears in middle."""
        state = AgentState(
            messages=[AIMessage(content="We have CONSENSUS_REACHED on this approach")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == END
    
    def test_default_route_to_autobot(self):
        """Test default routing to autobot when no special keywords present."""
        state = AgentState(
            messages=[HumanMessage(content="Please help me with a task")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "autobot"
    
    def test_default_route_with_empty_message(self):
        """Test default routing with empty message content."""
        state = AgentState(
            messages=[AIMessage(content="")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "autobot"
    
    def test_priority_execute_code_over_review(self):
        """Test that EXECUTE_CODE takes priority over REVIEW_REQUIRED."""
        state = AgentState(
            messages=[AIMessage(content="EXECUTE_CODE and REVIEW_REQUIRED both present")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_priority_review_over_consensus(self):
        """Test that REVIEW_REQUIRED takes priority over CONSENSUS_REACHED."""
        state = AgentState(
            messages=[AIMessage(content="REVIEW_REQUIRED and CONSENSUS_REACHED both present")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "alpha_evaluator"
    
    def test_ttl_overrides_all_keywords(self):
        """Test that TTL circuit breaker overrides all keyword routing."""
        state = AgentState(
            messages=[AIMessage(content="CONSENSUS_REACHED")],
            loop_count=5,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "terminal_fallback"
    
    def test_multiple_messages_uses_last(self):
        """Test that router uses the last message for routing decision."""
        state = AgentState(
            messages=[
                HumanMessage(content="EXECUTE_CODE first"),
                AIMessage(content="REVIEW_REQUIRED second"),
                AIMessage(content="CONSENSUS_REACHED third")
            ],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == END
    
    def test_case_sensitive_keywords(self):
        """Test that keyword matching is case-sensitive."""
        state = AgentState(
            messages=[AIMessage(content="execute_code lowercase")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "autobot"
    
    def test_loop_count_zero(self):
        """Test routing with loop_count at zero."""
        state = AgentState(
            messages=[HumanMessage(content="Start task")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "autobot"
    
    def test_loop_count_one(self):
        """Test routing with loop_count at one."""
        state = AgentState(
            messages=[AIMessage(content="EXECUTE_CODE task")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"


class TestNodeWrapperFunctions:
    """Test node wrapper functions with cache checking."""
    
    @patch('core.graph.check_duplicate_invocation')
    @patch('core.graph.autobot_node')
    @patch('core.graph.capture_snapshot')
    def test_autobot_with_cache_no_duplicate(self, mock_snapshot, mock_autobot, mock_check):
        """Test autobot_with_cache when no duplicate is detected."""
        mock_check.return_value = False
        mock_autobot.return_value = {"messages": [AIMessage(content="Response")]}
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = autobot_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        mock_autobot.assert_called_once_with(state)
        mock_snapshot.assert_called_once_with(state, "autobot")
        assert result["loop_count"] == 1
    
    @patch('core.graph.check_duplicate_invocation')
    def test_autobot_with_cache_duplicate_detected(self, mock_check):
        """Test autobot_with_cache when duplicate is detected."""
        mock_check.return_value = True
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=2,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = autobot_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        assert result["loop_count"] == 3
        assert len(result["messages"]) == 1
        assert "SYSTEM OVERRIDE" in result["messages"][0]["content"]
    
    @patch('core.graph.check_duplicate_invocation')
    @patch('core.graph.alpha_node')
    @patch('core.graph.capture_snapshot')
    def test_alpha_with_cache_no_duplicate(self, mock_snapshot, mock_alpha, mock_check):
        """Test alpha_with_cache when no duplicate is detected."""
        mock_check.return_value = False
        mock_alpha.return_value = {"messages": [AIMessage(content="Review")]}
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = alpha_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        mock_alpha.assert_called_once_with(state)
        mock_snapshot.assert_called_once_with(state, "alpha_evaluator")
        assert result["loop_count"] == 2
    
    @patch('core.graph.check_duplicate_invocation')
    def test_alpha_with_cache_duplicate_detected(self, mock_check):
        """Test alpha_with_cache when duplicate is detected."""
        mock_check.return_value = True
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=3,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = alpha_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        assert result["loop_count"] == 4
        assert "SYSTEM OVERRIDE" in result["messages"][0]["content"]
    
    @patch('core.graph.check_duplicate_invocation')
    @patch('core.graph.beta_node')
    @patch('core.graph.capture_snapshot')
    def test_beta_with_cache_no_duplicate(self, mock_snapshot, mock_beta, mock_check):
        """Test beta_with_cache when no duplicate is detected."""
        mock_check.return_value = False
        mock_beta.return_value = {"messages": [AIMessage(content="Code")]}
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = beta_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        mock_beta.assert_called_once_with(state)
        mock_snapshot.assert_called_once_with(state, "beta_worker")
        assert result["loop_count"] == 1
    
    @patch('core.graph.check_duplicate_invocation')
    def test_beta_with_cache_duplicate_detected(self, mock_check):
        """Test beta_with_cache when duplicate is detected."""
        mock_check.return_value = True
        
        state = AgentState(
            messages=[HumanMessage(content="Task")],
            loop_count=4,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = beta_with_cache(state)
        
        mock_check.assert_called_once_with(state)
        assert result["loop_count"] == 5
        assert "SYSTEM OVERRIDE" in result["messages"][0]["content"]


class TestGraphConfiguration:
    """Test graph configuration and structure."""
    
    def test_retry_policy_configuration(self):
        """Test that retry policy is configured correctly."""
        from core.graph import local_retry
        
        assert local_retry.initial_interval == 0.5
        assert local_retry.backoff_factor == 2.0
        assert local_retry.max_attempts == 3
        assert local_retry.jitter is True
    
    def test_workflow_has_required_nodes(self):
        """Test that workflow has all required nodes."""
        from core.graph import workflow
        
        node_names = list(workflow.nodes.keys())
        
        assert "autobot" in node_names
        assert "alpha_evaluator" in node_names
        assert "beta_worker" in node_names
        assert "terminal_fallback" in node_names
        assert "error_handler" in node_names
    
    def test_app_is_compiled(self):
        """Test that app is compiled and ready to use."""
        from core.graph import app
        
        assert app is not None
        assert hasattr(app, 'invoke')
        assert hasattr(app, 'stream')


class TestRouterEdgeCases:
    """Test edge cases for deterministic_router."""
    
    def test_whitespace_in_message(self):
        """Test routing with whitespace in message."""
        state = AgentState(
            messages=[AIMessage(content="  EXECUTE_CODE  with spaces  ")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_newlines_in_message(self):
        """Test routing with newlines in message."""
        state = AgentState(
            messages=[AIMessage(content="Line 1\nEXECUTE_CODE\nLine 3")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_special_characters_in_message(self):
        """Test routing with special characters in message."""
        state = AgentState(
            messages=[AIMessage(content="EXECUTE_CODE!@#$%^&*()")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_very_long_message(self):
        """Test routing with very long message."""
        long_content = "EXECUTE_CODE " + "x" * 10000
        state = AgentState(
            messages=[AIMessage(content=long_content)],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
    
    def test_unicode_in_message(self):
        """Test routing with unicode characters in message."""
        state = AgentState(
            messages=[AIMessage(content="EXECUTE_CODE with 日本語 characters")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"
