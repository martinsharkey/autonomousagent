"""Tests for core/editor_tool.py — the real file editor for goal execution."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from core.editor_tool import (
    _resolve_path,
    _validate_python_ast,
    _generate_diff,
    editor_read,
    editor_write,
    editor_patch,
    editor_create_file,
    editor_list_dir,
    parse_editor_action,
    execute_editor_action,
    PROJECT_ROOT,
)


# ─── Path Resolution Tests ────────────────────────────────────────────────────

class TestResolveAndSecurity:
    """Test path resolution and security boundaries."""

    def test_normal_path_resolves(self):
        ok, err, resolved = _resolve_path("tools/example.py")
        assert ok is True
        assert err == ""
        assert resolved == PROJECT_ROOT / "tools/example.py"

    def test_path_traversal_blocked(self):
        ok, err, _ = _resolve_path("../../../etc/passwd")
        assert ok is False
        assert "traversal" in err.lower() or "escapes" in err.lower()

    def test_absolute_path_blocked(self):
        ok, err, _ = _resolve_path("/etc/passwd")
        assert ok is False
        assert "traversal" in err.lower()

    def test_denylist_env_blocked(self):
        ok, err, _ = _resolve_path(".env")
        assert ok is False
        assert "denylist" in err.lower()

    def test_denylist_git_blocked(self):
        ok, err, _ = _resolve_path(".git/config")
        assert ok is False
        assert "denylist" in err.lower()

    def test_denylist_secrets_blocked(self):
        ok, err, _ = _resolve_path("secrets/key.pem")
        assert ok is False
        assert "denylist" in err.lower()

    def test_council_daemon_blocked(self):
        ok, err, _ = _resolve_path("council_daemon.py")
        assert ok is False
        assert "denylist" in err.lower()

    def test_normalized_traversal_blocked(self):
        ok, err, _ = _resolve_path("core/../../../etc/passwd")
        assert ok is False


# ─── AST Validation Tests ─────────────────────────────────────────────────────

class TestASTValidation:
    """Test Python AST validation."""

    def test_valid_python(self):
        ok, err = _validate_python_ast("x = 1\nprint(x)\n", "test.py")
        assert ok is True
        assert err == ""

    def test_invalid_python(self):
        ok, err = _validate_python_ast("def broken(\n", "test.py")
        assert ok is False
        assert "SyntaxError" in err

    def test_empty_file_valid(self):
        ok, err = _validate_python_ast("", "test.py")
        assert ok is True

    def test_complex_valid_python(self):
        code = '''
import os
from typing import Dict

class MyClass:
    def __init__(self, x: int = 0):
        self.x = x

    async def do_work(self) -> Dict[str, int]:
        return {"result": self.x}
'''
        ok, err = _validate_python_ast(code, "test.py")
        assert ok is True


# ─── Diff Generation Tests ────────────────────────────────────────────────────

class TestDiffGeneration:
    """Test unified diff generation."""

    def test_generates_diff(self):
        original = "line1\nline2\nline3\n"
        modified = "line1\nmodified\nline3\n"
        diff = _generate_diff(original, modified, "test.py")
        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-line2" in diff
        assert "+modified" in diff

    def test_no_diff_for_identical(self):
        content = "same\n"
        diff = _generate_diff(content, content, "test.py")
        assert diff == ""


# ─── Editor Read Tests ────────────────────────────────────────────────────────

class TestEditorRead:
    """Test file reading operations."""

    def test_read_existing_file(self):
        result = editor_read("requirements.txt")
        assert result["success"] is True
        assert "content" in result
        assert result["lines"] > 0

    def test_read_nonexistent_file(self):
        result = editor_read("nonexistent_file_xyz.py")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_read_denied_path(self):
        result = editor_read(".env")
        assert result["success"] is False
        assert "denylist" in result["error"].lower()


# ─── Editor Write Tests ───────────────────────────────────────────────────────

class TestEditorWrite:
    """Test file writing operations."""

    def test_write_new_python_file(self):
        test_path = "tests/_test_editor_write_temp.py"
        try:
            result = editor_write(test_path, "x = 42\nprint(x)\n")
            assert result["success"] is True
            assert result["is_new_file"] is True
            assert (PROJECT_ROOT / test_path).exists()
            content = (PROJECT_ROOT / test_path).read_text()
            assert "x = 42" in content
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)

    def test_write_invalid_python_rejected(self):
        test_path = "tests/_test_editor_invalid_temp.py"
        result = editor_write(test_path, "def broken(\n")
        assert result["success"] is False
        assert "AST" in result["error"] or "Syntax" in result["error"]
        assert not (PROJECT_ROOT / test_path).exists()

    def test_write_non_python_skips_ast(self):
        test_path = "tests/_test_editor_write_temp.md"
        try:
            result = editor_write(test_path, "# Not Python\nThis is markdown {{{\n")
            assert result["success"] is True
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)

    def test_write_to_denylist_fails(self):
        result = editor_write(".env", "SECRET=bad")
        assert result["success"] is False

    def test_write_generates_diff(self):
        test_path = "tests/_test_editor_diff_temp.py"
        try:
            editor_write(test_path, "x = 1\n")
            result = editor_write(test_path, "x = 2\n")
            assert result["success"] is True
            assert result["is_new_file"] is False
            assert "diff" in result
            assert "-x = 1" in result["diff"]
            assert "+x = 2" in result["diff"]
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)


# ─── Editor Patch Tests ───────────────────────────────────────────────────────

class TestEditorPatch:
    """Test search/replace patch operations."""

    def test_patch_replaces_text(self):
        test_path = "tests/_test_editor_patch_temp.py"
        try:
            editor_write(test_path, "x = 1\ny = 2\nz = 3\n")
            result = editor_patch(test_path, "y = 2", "y = 99")
            assert result["success"] is True
            assert result["occurrences_replaced"] == 1
            content = (PROJECT_ROOT / test_path).read_text()
            assert "y = 99" in content
            assert "y = 2" not in content
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)

    def test_patch_not_found(self):
        test_path = "tests/_test_editor_patch_temp2.py"
        try:
            editor_write(test_path, "x = 1\n")
            result = editor_patch(test_path, "NOT_IN_FILE", "replacement")
            assert result["success"] is False
            assert "not found" in result["error"].lower()
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)

    def test_patch_breaking_syntax_rejected(self):
        test_path = "tests/_test_editor_patch_syntax.py"
        try:
            editor_write(test_path, "def foo():\n    return 1\n")
            result = editor_patch(test_path, "def foo():\n    return 1", "def broken(")
            assert result["success"] is False
            assert "syntax" in result["error"].lower() or "Patch breaks" in result["error"]
            # Original content should be unchanged
            content = (PROJECT_ROOT / test_path).read_text()
            assert "def foo():" in content
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)


# ─── Parser Tests ─────────────────────────────────────────────────────────────

class TestParseEditorAction:
    """Test action string parsing."""

    def test_parse_json_read(self):
        result = parse_editor_action('{"operation": "read", "file_path": "core/planning.py"}')
        assert result["operation"] == "read"
        assert result["file_path"] == "core/planning.py"

    def test_parse_json_write(self):
        result = parse_editor_action('{"operation": "write", "file_path": "test.py", "content": "x = 1"}')
        assert result["operation"] == "write"
        assert result["content"] == "x = 1"

    def test_parse_json_patch(self):
        result = parse_editor_action('{"operation": "patch", "file_path": "test.py", "search": "old", "replace": "new"}')
        assert result["operation"] == "patch"
        assert result["search"] == "old"
        assert result["replace"] == "new"

    def test_parse_text_read(self):
        result = parse_editor_action("READ core/planning.py")
        assert result["operation"] == "read"
        assert result["file_path"] == "core/planning.py"

    def test_parse_text_write(self):
        result = parse_editor_action("WRITE test.py\nx = 1\ny = 2")
        assert result["operation"] == "write"
        assert result["file_path"] == "test.py"
        assert "x = 1" in result["content"]

    def test_parse_text_patch(self):
        result = parse_editor_action("PATCH test.py\nold_text\n---\nnew_text")
        assert result["operation"] == "patch"
        assert result["search"] == "old_text"
        assert result["replace"] == "new_text"

    def test_parse_text_list(self):
        result = parse_editor_action("LIST core/")
        assert result["operation"] == "list"
        assert result["file_path"] == "core/"

    def test_parse_unknown(self):
        result = parse_editor_action("DO SOMETHING WEIRD")
        assert result["operation"] == "unknown"
        assert "error" in result


# ─── Integration Tests ────────────────────────────────────────────────────────

class TestExecuteEditorAction:
    """Test the main execute_editor_action entry point."""

    def test_execute_read_action(self):
        result = execute_editor_action('{"operation": "read", "file_path": "requirements.txt"}')
        assert result["success"] is True
        assert "content" in result

    def test_execute_list_action(self):
        result = execute_editor_action("LIST core/")
        assert result["success"] is True
        assert "files" in result
        assert len(result["files"]) > 0

    def test_execute_write_and_cleanup(self):
        test_path = "tests/_test_integration_editor.py"
        try:
            result = execute_editor_action(f'{{"operation": "write", "file_path": "{test_path}", "content": "# test\\nx = 1\\n"}}')
            assert result["success"] is True
        finally:
            (PROJECT_ROOT / test_path).unlink(missing_ok=True)

    def test_execute_bad_action(self):
        result = execute_editor_action("GIBBERISH nonsense")
        assert result["success"] is False
        assert "error" in result


# ─── List Dir Tests ───────────────────────────────────────────────────────────

class TestEditorListDir:
    """Test directory listing."""

    def test_list_core_directory(self):
        result = editor_list_dir("core")
        assert result["success"] is True
        assert len(result["files"]) > 5
        assert any("planning.py" in f for f in result["files"])

    def test_list_nonexistent(self):
        result = editor_list_dir("nonexistent_directory_xyz")
        assert result["success"] is False

    def test_list_denied_path(self):
        result = editor_list_dir(".git")
        assert result["success"] is False
