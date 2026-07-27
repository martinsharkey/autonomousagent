"""Tests for ReAct reasoning upgrade."""
from __future__ import annotations

import json
import pytest

from core.react import (
    extract_react_parts,
    build_react_system_prompt,
    build_react_voter_prompt,
    build_error_feedback,
)


class TestExtractReactParts:
    def test_extracts_think_and_action(self):
        text = "prefix <think>reasoning here</think> middle <action>{\"vote\": \"APPROVE\"}</action> suffix"
        reasoning, action = extract_react_parts(text)
        assert reasoning == "reasoning here"
        assert action == '{"vote": "APPROVE"}'

    def test_case_insensitive_tags(self):
        text = "<think>Reasoning</think><ACTION>payload</ACTION>"
        reasoning, action = extract_react_parts(text)
        assert reasoning == "Reasoning"
        assert action == "payload"

    def test_missing_action_returns_raw_text(self):
        text = "just some plain text without tags"
        reasoning, action = extract_react_parts(text)
        assert reasoning == ""
        assert action == text

    def test_missing_think_returns_empty_reasoning(self):
        text = "<action>payload</action>"
        reasoning, action = extract_react_parts(text)
        assert reasoning == ""
        assert action == "payload"

    def test_multiple_think_blocks_uses_first(self):
        text = "<think>first</think><action>a</action><think>second</think>"
        reasoning, action = extract_react_parts(text)
        assert reasoning == "first"


class TestBuildReactSystemPrompt:
    def test_wraps_base_prompt(self):
        base = "You are a helpful assistant."
        result = build_react_system_prompt(base, "TestBot")
        assert base in result
        assert "ReAct Reasoning Protocol" in result
        assert "</think>" in result
        assert "<action>" in result

    def test_preserves_mission_context_markers(self):
        base = "# Council Architecture\nYou are one of three agents."
        result = build_react_system_prompt(base, "TestBot")
        assert "# Council Architecture" in result
        assert "ReAct" in result


class TestBuildReactVoterPrompt:
    def test_returns_structured_prompt(self):
        prompt = build_react_voter_prompt("Autobot", "Add logging", "Mission: self-evolve")
        assert "Autobot" in prompt
        assert "Add logging" in prompt
        assert "Mission: self-evolve" in prompt
        assert "<think>" in prompt
        assert "<action>" in prompt
        assert "APPROVE" in prompt
        assert "REJECT" in prompt


class TestBuildErrorFeedback:
    def test_creates_structured_error(self):
        err = ValueError("tool broke")
        feedback = build_error_feedback("autobot", err, {"mutation_id": "abc"})
        assert feedback["node"] == "autobot"
        assert feedback["error_type"] == "ValueError"
        assert feedback["error_message"] == "tool broke"
        assert feedback["context"] == {"mutation_id": "abc"}

    def test_empty_context_defaults_to_empty_dict(self):
        err = RuntimeError("boom")
        feedback = build_error_feedback("beta_worker", err)
        assert feedback["node"] == "beta_worker"
        assert feedback["context"] == {}


class TestReactGraphIntegration:
    def test_reasoning_trace_appended_in_node(self):
        from agents.autobot import autobot_node
        from core.state import AgentState

        state: AgentState = {
            "messages": [{"role": "user", "content": "Say hello"}],
            "loop_count": 0,
            "completed_nodes": [],
            "recent_tool_invocations": [],
            "codebase_hash": "",
            "reasoning_traces": [],
            "error_feedback": [],
            "active_mutation_id": None,
            "proposed_mutation_code": None,
            "mission_rationale": None,
            "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},
            "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},
            "operator_override": None,
            "operator_override_rationale": None,
            "operator_override_timestamp": None,
            "escalation_reason": None,
            "requires_operator_approval": False,
            "proposed_version": None,
            "current_version": "v1.0.0",
            "rollback_pending": False,
            "rollback_target_version": None,
            "rollback_approved": False,
            "rollback_reason": None,
        }

        result = autobot_node(state)
        assert "reasoning_traces" in result
        assert isinstance(result["reasoning_traces"], list)

    def test_error_feedback_populated_on_llm_failure(self, monkeypatch):
        from agents.autobot import autobot_node
        from core.state import AgentState

        def bad_invoke(*args, **kwargs):
            raise RuntimeError("LLM down")

        monkeypatch.setattr("agents.autobot._invoke_cloud", bad_invoke)

        state: AgentState = {
            "messages": [{"role": "user", "content": "Say hello"}],
            "loop_count": 0,
            "completed_nodes": [],
            "recent_tool_invocations": [],
            "codebase_hash": "",
            "reasoning_traces": [],
            "error_feedback": [],
            "active_mutation_id": None,
            "proposed_mutation_code": None,
            "mission_rationale": None,
            "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},
            "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},
            "operator_override": None,
            "operator_override_rationale": None,
            "operator_override_timestamp": None,
            "escalation_reason": None,
            "requires_operator_approval": False,
            "proposed_version": None,
            "current_version": "v1.0.0",
            "rollback_pending": False,
            "rollback_target_version": None,
            "rollback_approved": False,
            "rollback_reason": None,
        }

        result = autobot_node(state)
        assert len(result["error_feedback"]) == 1
        assert result["error_feedback"][0]["node"] == "autobot"
        assert result["error_feedback"][0]["error_type"] == "RuntimeError"
