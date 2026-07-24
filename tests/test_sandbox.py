import pytest
from unittest.mock import patch, MagicMock
from core.sandbox import (
    execute_in_sandbox,
    execute_python_in_sandbox,
    _is_docker_available,
    _execute_in_docker_sandbox,
    _execute_in_subprocess_sandbox,
    _execute_python_in_docker,
    _execute_python_in_subprocess,
    validate_sandbox_security
)


class TestSandboxSecurity:
    def test_validate_blocks_subclasses(self):
        assert not validate_sandbox_security("().__class__.__base__.__subclasses__()")

    def test_validate_blocks_os_system(self):
        assert not validate_sandbox_security("os.system('rm -rf /')")

    def test_validate_blocks_eval(self):
        assert not validate_sandbox_security("eval('code')")

    def test_validate_blocks_exec(self):
        assert not validate_sandbox_security("exec('code')")

    def test_validate_blocks_import(self):
        assert not validate_sandbox_security("__import__('os')")

    def test_validate_allows_safe_code(self):
        assert validate_sandbox_security("print('hello')")
        assert validate_sandbox_security("x = 1 + 2")


class TestSandboxDockerDetection:
    @patch('core.sandbox.subprocess.run')
    def test_docker_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert _is_docker_available()

    @patch('core.sandbox.subprocess.run')
    def test_docker_not_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert not _is_docker_available()

    @patch('core.sandbox.subprocess.run', side_effect=Exception("not found"))
    def test_docker_exception(self, mock_run):
        assert not _is_docker_available()


class TestSandboxExecution:
    @patch('core.sandbox._is_docker_available', return_value=True)
    @patch('core.sandbox._execute_in_docker_sandbox')
    def test_execute_uses_docker_when_available(self, mock_docker, mock_avail):
        mock_docker.return_value = "output"
        result = execute_in_sandbox("echo test")
        assert result == "output"
        mock_docker.assert_called_once()

    @patch('core.sandbox._is_docker_available', return_value=False)
    @patch('core.sandbox._execute_in_subprocess_sandbox')
    def test_execute_falls_back_to_subprocess(self, mock_subprocess, mock_avail):
        mock_subprocess.return_value = "output"
        result = execute_in_sandbox("echo test")
        assert result == "output"
        mock_subprocess.assert_called_once()

    @patch('core.sandbox._is_docker_available', return_value=True)
    @patch('core.sandbox._execute_python_in_docker')
    def test_python_execute_uses_docker(self, mock_docker, mock_avail):
        mock_docker.return_value = "output"
        result = execute_python_in_sandbox("print('test')")
        assert result == "output"
        mock_docker.assert_called_once()

    @patch('core.sandbox._is_docker_available', return_value=False)
    @patch('core.sandbox._execute_python_in_subprocess')
    def test_python_execute_falls_back(self, mock_subprocess, mock_avail):
        mock_subprocess.return_value = "output"
        result = execute_python_in_sandbox("print('test')")
        assert result == "output"
        mock_subprocess.assert_called_once()


class TestDockerSandbox:
    @patch('core.sandbox.subprocess.run')
    def test_docker_sandbox_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        result = _execute_in_docker_sandbox("echo test", 30)
        assert result == "output"

    @patch('core.sandbox.subprocess.run')
    def test_docker_sandbox_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _execute_in_docker_sandbox("bad command", 30)
        assert "failed" in result.lower()

    @patch('core.sandbox.subprocess.run')
    def test_docker_sandbox_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=30)
        result = _execute_in_docker_sandbox("sleep 100", 30)
        assert "timed out" in result.lower()

    @patch('core.sandbox.subprocess.run')
    def test_docker_sandbox_uses_security_flags(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        _execute_in_docker_sandbox("echo test", 30)
        call_args = mock_run.call_args[0][0]
        assert "--memory" in call_args
        assert "--cpus" in call_args
        assert "--pids-limit" in call_args
        assert "--network" in call_args
        assert "none" in call_args
        assert "--security-opt" in call_args
        assert "no-new-privileges" in call_args
        assert "--read-only" in call_args
