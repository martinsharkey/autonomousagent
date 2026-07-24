import pytest
from typing import get_type_hints
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from core.state import AgentState


class TestAgentStateStructure:
    """Test AgentState TypedDict structure and type validation."""
    
    def test_agent_state_is_typeddict(self):
        """Test that AgentState is a TypedDict."""
        from typing import TypedDict
        assert hasattr(AgentState, '__annotations__')
    
    def test_agent_state_has_required_fields(self):
        """Test that AgentState has all required fields."""
        annotations = get_type_hints(AgentState)
        required_fields = ['messages', 'loop_count', 'recent_tool_invocations', 
                          'completed_nodes', 'codebase_hash']
        
        for field in required_fields:
            assert field in annotations, f"Missing field: {field}"
    
    def test_agent_state_field_types(self):
        """Test that AgentState fields have correct type annotations."""
        annotations = get_type_hints(AgentState)
        
        assert 'loop_count' in annotations
        assert annotations['loop_count'] == int
        
        assert 'codebase_hash' in annotations
        assert annotations['codebase_hash'] == str


class TestAgentStateInitialization:
    """Test AgentState initialization and default values."""
    
    def test_create_empty_state(self):
        """Test creating an empty AgentState."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        assert state['messages'] == []
        assert state['loop_count'] == 0
        assert state['recent_tool_invocations'] == []
        assert state['completed_nodes'] == []
        assert state['codebase_hash'] == ""
    
    def test_create_state_with_messages(self):
        """Test creating AgentState with initial messages."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there")
        ]
        
        state = AgentState(
            messages=messages,
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        assert len(state['messages']) == 2
        assert state['messages'][0].content == "Hello"
        assert state['messages'][1].content == "Hi there"
    
    def test_create_state_with_completed_nodes(self):
        """Test creating AgentState with completed nodes."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=["autobot", "beta_worker"],
            codebase_hash="abc123"
        )
        
        assert len(state['completed_nodes']) == 2
        assert "autobot" in state['completed_nodes']
        assert "beta_worker" in state['completed_nodes']


class TestLoopCountTTL:
    """Test loop_count TTL circuit breaker behavior."""
    
    def test_loop_count_starts_at_zero(self):
        """Test that loop_count starts at zero."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        assert state['loop_count'] == 0
    
    def test_loop_count_increment(self):
        """Test incrementing loop_count."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        state['loop_count'] += 1
        assert state['loop_count'] == 1
        
        state['loop_count'] += 1
        assert state['loop_count'] == 2
    
    def test_loop_count_ttl_check(self):
        """Test TTL check with loop_count."""
        state = AgentState(
            messages=[],
            loop_count=5,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        max_loops = 5
        assert state['loop_count'] >= max_loops
    
    def test_loop_count_below_ttl(self):
        """Test loop_count below TTL threshold."""
        state = AgentState(
            messages=[],
            loop_count=3,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        max_loops = 5
        assert state['loop_count'] < max_loops


class TestMessageReducer:
    """Test add_messages reducer for message list."""
    
    def test_add_messages_empty_to_empty(self):
        """Test adding empty list to empty list."""
        existing = []
        new_messages = []
        result = add_messages(existing, new_messages)
        assert result == []
    
    def test_add_messages_to_empty(self):
        """Test adding messages to empty list."""
        existing = []
        new_messages = [HumanMessage(content="Hello")]
        result = add_messages(existing, new_messages)
        
        assert len(result) == 1
        assert result[0].content == "Hello"
    
    def test_add_messages_to_existing(self):
        """Test adding messages to existing list."""
        existing = [HumanMessage(content="Hello")]
        new_messages = [AIMessage(content="Hi")]
        result = add_messages(existing, new_messages)
        
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi"
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages at once."""
        existing = []
        new_messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
            HumanMessage(content="How are you?")
        ]
        result = add_messages(existing, new_messages)
        
        assert len(result) == 3
    
    def test_add_messages_preserves_order(self):
        """Test that add_messages preserves message order."""
        existing = [HumanMessage(content="First")]
        new_messages = [
            AIMessage(content="Second"),
            HumanMessage(content="Third")
        ]
        result = add_messages(existing, new_messages)
        
        assert result[0].content == "First"
        assert result[1].content == "Second"
        assert result[2].content == "Third"


class TestListReducers:
    """Test operator.add reducer for list fields."""
    
    def test_recent_tool_invocations_add(self):
        """Test adding to recent_tool_invocations list."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=["tool1"],
            completed_nodes=[],
            codebase_hash=""
        )
        
        new_invocations = ["tool2", "tool3"]
        state['recent_tool_invocations'] = state['recent_tool_invocations'] + new_invocations
        
        assert len(state['recent_tool_invocations']) == 3
        assert "tool1" in state['recent_tool_invocations']
        assert "tool2" in state['recent_tool_invocations']
        assert "tool3" in state['recent_tool_invocations']
    
    def test_completed_nodes_add(self):
        """Test adding to completed_nodes list."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=["autobot"],
            codebase_hash=""
        )
        
        new_nodes = ["beta_worker", "alpha_evaluator"]
        state['completed_nodes'] = state['completed_nodes'] + new_nodes
        
        assert len(state['completed_nodes']) == 3
        assert "autobot" in state['completed_nodes']
        assert "beta_worker" in state['completed_nodes']
        assert "alpha_evaluator" in state['completed_nodes']
    
    def test_empty_list_add(self):
        """Test adding empty list to existing list."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=["tool1"],
            completed_nodes=[],
            codebase_hash=""
        )
        
        state['recent_tool_invocations'] = state['recent_tool_invocations'] + []
        assert len(state['recent_tool_invocations']) == 1
    
    def test_add_to_empty_list(self):
        """Test adding to empty list."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        state['completed_nodes'] = state['completed_nodes'] + ["autobot"]
        assert len(state['completed_nodes']) == 1
        assert "autobot" in state['completed_nodes']


class TestStateUpdates:
    """Test state update operations."""
    
    def test_update_loop_count(self):
        """Test updating loop_count."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        state['loop_count'] = 5
        assert state['loop_count'] == 5
    
    def test_update_codebase_hash(self):
        """Test updating codebase_hash."""
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        state['codebase_hash'] = "new_hash_123"
        assert state['codebase_hash'] == "new_hash_123"
    
    def test_update_messages_with_reducer(self):
        """Test updating messages using add_messages reducer."""
        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        new_messages = [AIMessage(content="Hi")]
        state['messages'] = add_messages(state['messages'], new_messages)
        
        assert len(state['messages']) == 2
        assert state['messages'][0].content == "Hello"
        assert state['messages'][1].content == "Hi"


class TestStateValidation:
    """Test state validation and edge cases."""
    
    def test_state_with_system_message(self):
        """Test state with system message."""
        state = AgentState(
            messages=[SystemMessage(content="You are a helpful assistant")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        assert len(state['messages']) == 1
        assert state['messages'][0].content == "You are a helpful assistant"
    
    def test_state_with_mixed_messages(self):
        """Test state with mixed message types."""
        state = AgentState(
            messages=[
                SystemMessage(content="System prompt"),
                HumanMessage(content="User input"),
                AIMessage(content="AI response")
            ],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        assert len(state['messages']) == 3
    
    def test_large_loop_count(self):
        """Test state with large loop_count."""
        state = AgentState(
            messages=[],
            loop_count=1000,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        assert state['loop_count'] == 1000
    
    def test_many_completed_nodes(self):
        """Test state with many completed nodes."""
        nodes = [f"node_{i}" for i in range(100)]
        state = AgentState(
            messages=[],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=nodes,
            codebase_hash=""
        )
        
        assert len(state['completed_nodes']) == 100
