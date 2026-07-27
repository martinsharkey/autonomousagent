import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.messages import AIMessage, HumanMessage
from core.graph import app, deterministic_router
from core.state import AgentState
from core.snapshots import load_snapshots, verify_snapshot_chain
from governance.audit_log import read_audit_log, verify_log_integrity
import os
import shutil


class TestCouncilIntegration:
    def setup_method(self):
        self.snapshot_dir = "reasoning_snapshots"
        self.audit_dir = "audit_logs"
        
        try:
            if os.path.exists(self.snapshot_dir):
                shutil.rmtree(self.snapshot_dir, ignore_errors=True)
            if os.path.exists(self.audit_dir):
                shutil.rmtree(self.audit_dir, ignore_errors=True)
        except Exception:
            pass
        
        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.audit_dir, exist_ok=True)

    def teardown_method(self):
        try:
            if os.path.exists(self.snapshot_dir):
                shutil.rmtree(self.snapshot_dir, ignore_errors=True)
            if os.path.exists(self.audit_dir):
                shutil.rmtree(self.audit_dir, ignore_errors=True)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_council_basic_flow(self):
        mock_responses = [
            AIMessage(content="EXECUTE_CODE: Write a simple function"),
            AIMessage(content="Code executed successfully"),
            AIMessage(content="REVIEW_REQUIRED: Code review needed"),
            AIMessage(content="Code looks good"),
            AIMessage(content="CONSENSUS_REACHED: Task complete")
        ]
        
        with patch('agents.autobot.autobot_llm') as mock_autobot, \
             patch('agents.alpha_evaluator.alpha_llm') as mock_alpha, \
             patch('agents.beta_worker.beta_llm') as mock_beta:
            
            mock_autobot.ainvoke = AsyncMock(side_effect=mock_responses[:2])
            mock_alpha.ainvoke = AsyncMock(side_effect=mock_responses[2:4])
            mock_beta.ainvoke = AsyncMock(side_effect=mock_responses[4:])
            
            config = {"configurable": {"thread_id": "test_session_001"}}
            initial_state = {
                "messages": [("user", "Write a simple function")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            updates = []
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                updates.append(chunk)
                
                if len(updates) >= 5:
                    break
            
            assert len(updates) > 0
            
            node_names = [list(chunk.keys())[0] for chunk in updates]
            assert "autobot" in node_names

    @pytest.mark.asyncio
    async def test_council_ttl_circuit_breaker(self):
        mock_response = AIMessage(content="Still working on it")
        
        with patch('agents.autobot.autobot_llm') as mock_autobot, \
             patch('agents.alpha_evaluator.alpha_llm') as mock_alpha, \
             patch('agents.beta_worker.beta_llm') as mock_beta:
            
            mock_autobot.ainvoke = AsyncMock(return_value=mock_response)
            mock_alpha.ainvoke = AsyncMock(return_value=mock_response)
            mock_beta.ainvoke = AsyncMock(return_value=mock_response)
            
            config = {"configurable": {"thread_id": "test_session_002"}}
            initial_state = {
                "messages": [("user", "Complex task")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            updates = []
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                updates.append(chunk)
                
                for node_name, state_update in chunk.items():
                    if "loop_count" in state_update and state_update["loop_count"] >= 5:
                        break
                
                if len(updates) >= 10:
                    break
            
            final_loop_count = 0
            for chunk in updates:
                for node_name, state_update in chunk.items():
                    if "loop_count" in state_update:
                        final_loop_count = state_update["loop_count"]
            
            assert final_loop_count <= 6

    @pytest.mark.asyncio
    async def test_council_creates_snapshots(self):
        mock_responses = [
            AIMessage(content="EXECUTE_CODE: Task 1"),
            AIMessage(content="Task 1 complete"),
            AIMessage(content="REVIEW_REQUIRED: Review task 1"),
            AIMessage(content="CONSENSUS_REACHED")
        ]
        
        with patch('agents.autobot.autobot_llm') as mock_autobot, \
             patch('agents.alpha_evaluator.alpha_llm') as mock_alpha, \
             patch('agents.beta_worker.beta_llm') as mock_beta:
            
            mock_autobot.ainvoke = AsyncMock(side_effect=mock_responses[:2])
            mock_alpha.ainvoke = AsyncMock(side_effect=mock_responses[2:3])
            mock_beta.ainvoke = AsyncMock(side_effect=mock_responses[3:])
            
            config = {"configurable": {"thread_id": "test_session_003"}}
            initial_state = {
                "messages": [("user", "Test task")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                pass
            
            snapshots = load_snapshots()
            assert len(snapshots) > 0
            
            for snapshot in snapshots:
                assert "snapshot_hash" in snapshot
                assert "hmac" in snapshot

    @pytest.mark.asyncio
    async def test_council_creates_audit_log(self):
        mock_response = AIMessage(content="CONSENSUS_REACHED")
        
        with patch('agents.autobot.autobot_llm') as mock_autobot:
            mock_autobot.ainvoke = AsyncMock(return_value=mock_response)
            
            config = {"configurable": {"thread_id": "test_session_004"}}
            initial_state = {
                "messages": [("user", "Test task")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                pass
            
            audit_entries = read_audit_log()
            assert len(audit_entries) > 0
            
            for entry in audit_entries:
                assert "entry_hash" in entry
                assert "hmac" in entry
            
            integrity_result = verify_log_integrity()
            assert integrity_result["valid"] is True

    def test_deterministic_router_execution_code(self):
        state = AgentState(
            messages=[HumanMessage(content="EXECUTE_CODE: Write function")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "beta_worker"

    def test_deterministic_router_review_required(self):
        state = AgentState(
            messages=[HumanMessage(content="REVIEW_REQUIRED: Check code")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "alpha_evaluator"

    def test_deterministic_router_consensus_reached(self):
        state = AgentState(
            messages=[HumanMessage(content="CONSENSUS_REACHED")],
            loop_count=0,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "__end__"

    def test_deterministic_router_ttl_breach(self):
        state = AgentState(
            messages=[HumanMessage(content="Still working")],
            loop_count=5,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        result = deterministic_router(state)
        assert result == "terminal_fallback"

    @pytest.mark.asyncio
    async def test_council_handles_node_failure(self):
        with patch('agents.autobot.autobot_llm') as mock_autobot:
            mock_autobot.ainvoke = AsyncMock(side_effect=Exception("LLM failed"))
            
            config = {"configurable": {"thread_id": "test_session_005"}}
            initial_state = {
                "messages": [("user", "Test task")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            with pytest.raises(Exception):
                async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                    pass

    @pytest.mark.asyncio
    async def test_council_snapshot_chain_integrity(self):
        mock_responses = [
            AIMessage(content="Task 1"),
            AIMessage(content="Task 2"),
            AIMessage(content="Task 3")
        ]
        
        with patch('agents.autobot.autobot_llm') as mock_autobot:
            mock_autobot.ainvoke = AsyncMock(side_effect=mock_responses)
            
            config = {"configurable": {"thread_id": "test_session_006"}}
            initial_state = {
                "messages": [("user", "Test task")],
                "loop_count": 0,
                "completed_nodes": [],
                "recent_tool_invocations": [],
                "codebase_hash": ""
            }
            
            update_count = 0
            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
                update_count += 1
                if update_count >= 3:
                    break
            
            snapshots = load_snapshots()
            if len(snapshots) > 1:
                node_name = snapshots[0]["node"]
                chain_result = verify_snapshot_chain(node_name)
                assert chain_result["valid"] is True
