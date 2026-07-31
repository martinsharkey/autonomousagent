"""Tests for goal verification and post-goal test runner in core/planning.py."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from core.planning import AgentPlanner


@pytest.fixture
def planner():
    """Create a planner instance with mocked dependencies."""
    with patch("core.planning.get_config_store") as mock_cs, \
         patch("core.planning.get_llm_router") as mock_lr:
        mock_cs.return_value = MagicMock()
        mock_cs.return_value.get_active.return_value = {"system_prompt": "test"}
        mock_cs.return_value.get_active_with_defaults.return_value = {
            "system_prompt": "test",
            "allowed_tools": ["editor", "shell_exec"],
        }
        mock_lr.return_value = AsyncMock()
        p = AgentPlanner("test_agent")
        yield p


class TestGetModifiedFiles:
    """Test _get_modified_files extraction from results."""

    def test_extracts_file_paths_from_editor_results(self, planner):
        results = [
            {
                "step": 1,
                "tool": "editor",
                "status": "completed",
                "output": json.dumps({"success": True, "file_path": "core/test.py", "diff": "+x=1"}),
            },
            {
                "step": 2,
                "tool": "editor",
                "status": "completed",
                "output": json.dumps({"success": True, "file_path": "tools/helper.py", "diff": "+y=2"}),
            },
        ]
        files = planner._get_modified_files(results)
        assert files == ["core/test.py", "tools/helper.py"]

    def test_ignores_non_editor_steps(self, planner):
        results = [
            {"step": 1, "tool": "shell_exec", "status": "completed", "output": "ok"},
            {"step": 2, "tool": None, "status": "completed", "output": "text"},
        ]
        files = planner._get_modified_files(results)
        assert files == []

    def test_ignores_failed_editor_steps(self, planner):
        results = [
            {
                "step": 1,
                "tool": "editor",
                "status": "failed",
                "output": json.dumps({"success": False, "error": "denied"}),
            },
        ]
        files = planner._get_modified_files(results)
        assert files == []

    def test_handles_malformed_output(self, planner):
        results = [
            {"step": 1, "tool": "editor", "status": "completed", "output": "not json"},
        ]
        files = planner._get_modified_files(results)
        assert files == []


class TestPostGoalTests:
    """Test _run_post_goal_tests method."""

    @patch("core.planning.subprocess.run")
    def test_returns_passed_on_success(self, mock_run, planner):
        mock_run.return_value = MagicMock(returncode=0, stdout="4 passed", stderr="")
        result = planner._run_post_goal_tests()
        assert result["passed"] is True
        assert "4 passed" in result["output"]

    @patch("core.planning.subprocess.run")
    def test_returns_failed_on_test_failure(self, mock_run, planner):
        mock_run.return_value = MagicMock(returncode=1, stdout="1 failed", stderr="AssertionError")
        result = planner._run_post_goal_tests()
        assert result["passed"] is False

    @patch("core.planning.subprocess.run")
    def test_handles_timeout(self, mock_run, planner):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=90)
        result = planner._run_post_goal_tests()
        assert result["passed"] is False
        assert "timed out" in result["errors"].lower()

    @patch("core.planning.subprocess.run")
    def test_handles_missing_pytest(self, mock_run, planner):
        mock_run.side_effect = FileNotFoundError("pytest not found")
        result = planner._run_post_goal_tests()
        # Should not block on missing tools
        assert result["passed"] is True
        assert "skipped" in result["errors"].lower()


class TestVerifyGoal:
    """Test verify_goal LLM-based verification."""

    @pytest.mark.asyncio
    async def test_failed_execution_not_verified(self, planner):
        execution_result = {"status": "failed", "failed_reason": "step 2 error"}
        result = await planner.verify_goal("Improve tests", execution_result)
        assert result["verified"] is False
        assert result["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_verified_on_positive_llm_response(self, planner):
        planner.llm_router.route_request = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"verified": true, "confidence": 0.85, "reason": "Files were modified correctly"}'}}]
        })
        execution_result = {
            "status": "completed",
            "results": [
                {"step": 1, "action": "write test file", "status": "completed", "output": '{"success": true, "file_path": "test.py"}', "tool": "editor"}
            ],
            "files_modified": ["test.py"],
            "test_result": {"passed": True},
        }
        result = await planner.verify_goal("Create a test file", execution_result)
        assert result["verified"] is True
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_not_verified_on_negative_llm_response(self, planner):
        planner.llm_router.route_request = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"verified": false, "confidence": 0.9, "reason": "No real changes were made"}'}}]
        })
        execution_result = {
            "status": "completed",
            "results": [
                {"step": 1, "action": "think about it", "status": "completed", "output": "I thought about it", "tool": None}
            ],
            "files_modified": [],
            "test_result": None,
        }
        result = await planner.verify_goal("Implement feature X", execution_result)
        assert result["verified"] is False
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_handles_llm_error_conservatively(self, planner):
        planner.llm_router.route_request = AsyncMock(side_effect=Exception("API down"))
        execution_result = {
            "status": "completed",
            "results": [],
            "files_modified": [],
            "test_result": None,
        }
        result = await planner.verify_goal("Do something", execution_result)
        # Conservative: don't verify if we can't check
        assert result["verified"] is False
        assert "failed" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_handles_malformed_llm_json(self, planner):
        planner.llm_router.route_request = AsyncMock(return_value={
            "choices": [{"message": {"content": "Sure, the goal was achieved!"}}]
        })
        execution_result = {
            "status": "completed",
            "results": [],
            "files_modified": [],
            "test_result": None,
        }
        result = await planner.verify_goal("Do something", execution_result)
        # Can't parse → conservative
        assert result["verified"] is False


class TestExecutePlanWithTests:
    """Test that execute_plan runs post-goal tests when files are modified."""

    @pytest.mark.asyncio
    async def test_plan_fails_if_tests_fail(self, planner):
        """If tests fail after file modifications, the plan should fail."""
        # Mock execute_step to simulate a file edit
        async def mock_execute_step(step, context):
            return {
                "step": 1,
                "action": "write file",
                "tool": "editor",
                "status": "completed",
                "output": json.dumps({"success": True, "file_path": "test_file.py"}),
            }

        planner.execute_step = mock_execute_step

        # Mock test runner to fail
        with patch.object(planner, "_run_post_goal_tests", return_value={"passed": False, "output": "FAILED", "errors": "AssertionError"}):
            plan = {
                "status": "created",
                "plan": {"steps": [{"step": 1, "action": "write file", "tool": "editor"}]},
            }
            result = await planner.execute_plan(plan)
            assert result["status"] == "failed"
            assert result["failed_reason"] == "post_goal_tests_failed"

    @pytest.mark.asyncio
    async def test_plan_succeeds_if_tests_pass(self, planner):
        """If tests pass after file modifications, the plan should succeed."""
        async def mock_execute_step(step, context):
            return {
                "step": 1,
                "action": "write file",
                "tool": "editor",
                "status": "completed",
                "output": json.dumps({"success": True, "file_path": "test_file.py"}),
            }

        planner.execute_step = mock_execute_step

        with patch.object(planner, "_run_post_goal_tests", return_value={"passed": True, "output": "1 passed", "errors": ""}):
            plan = {
                "status": "created",
                "plan": {"steps": [{"step": 1, "action": "write file", "tool": "editor"}]},
            }
            result = await planner.execute_plan(plan)
            assert result["status"] == "completed"
            assert result["files_modified"] == ["test_file.py"]

    @pytest.mark.asyncio
    async def test_plan_skips_tests_when_no_files_modified(self, planner):
        """If no files were modified, tests should not run."""
        async def mock_execute_step(step, context):
            return {
                "step": 1,
                "action": "think about design",
                "tool": None,
                "status": "completed",
                "output": "Thought about it",
            }

        planner.execute_step = mock_execute_step

        with patch.object(planner, "_run_post_goal_tests") as mock_tests:
            plan = {
                "status": "created",
                "plan": {"steps": [{"step": 1, "action": "think", "tool": None}]},
            }
            result = await planner.execute_plan(plan)
            assert result["status"] == "completed"
            mock_tests.assert_not_called()
