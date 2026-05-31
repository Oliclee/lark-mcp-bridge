"""executor.py 单元测试。"""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from lark_mcp_bridge.config import BridgeSettings
from lark_mcp_bridge.executor import ExecutionResult, check_cli_available, execute
from lark_mcp_bridge.errors import ExecutionError


@pytest.fixture
def settings():
    """测试用配置。"""
    return BridgeSettings(cli_path="lark-cli", timeout=5)


class TestExecute:
    """execute() 函数测试。"""

    def test_success_json_output(self, settings):
        """正常执行，返回 JSON 数据。"""
        mock_output = json.dumps({"code": 0, "msg": "success", "data": {"id": "123"}})
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr="",
            )
            result = execute(["calendar", "+agenda", "--format", "json"], settings=settings)

        assert result.success is True
        assert result.data == {"code": 0, "msg": "success", "data": {"id": "123"}}
        assert result.error_code is None
        assert result.duration_ms >= 0

    def test_success_empty_output(self, settings):
        """正常执行但无输出。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = execute(["calendar", "+agenda"], settings=settings)

        assert result.success is True
        assert result.data == {}

    def test_success_non_json_output(self, settings):
        """正常执行但输出非 JSON。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="some plain text", stderr=""
            )
            result = execute(["calendar", "--help"], settings=settings)

        assert result.success is True
        assert result.data == {"_raw": "some plain text"}

    def test_timeout(self, settings):
        """子进程超时。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="lark-cli", timeout=5)
            result = execute(["calendar", "+agenda"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_TIMEOUT"
        assert "超时" in result.error_message

    def test_cli_not_found(self, settings):
        """lark-cli 不在 PATH 中。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = execute(["calendar", "+agenda"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_CLI_NOT_FOUND"

    def test_auth_expired(self, settings):
        """认证过期错误。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error: token expired, please re-login",
            )
            result = execute(["im", "+messages-send"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_AUTH_EXPIRED"
        assert "认证" in result.recovery_hint

    def test_rate_limited(self, settings):
        """限流错误。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error: 429 rate limit exceeded",
            )
            result = execute(["im", "+messages-send"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_RATE_LIMITED"

    def test_permission_denied(self, settings):
        """权限不足。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error: 403 permission denied",
            )
            result = execute(["drive", "+delete"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_PERMISSION_DENIED"

    def test_destructive_confirm(self, settings):
        """高风险操作需要确认（exit code 10）。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=10,
                stdout="",
                stderr="This is a destructive operation. Use --yes to confirm.",
            )
            result = execute(["drive", "+delete", "--file-id", "abc"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_DESTRUCTIVE_CONFIRM"
        assert "--yes" in result.recovery_hint

    def test_unknown_error(self, settings):
        """未知错误回退到 E_CLI_ERROR。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Something unexpected happened",
            )
            result = execute(["base", "+search"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_CLI_ERROR"

    def test_command_construction(self, settings):
        """验证完整命令构造。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="{}", stderr="")
            execute(["im", "+messages-send", "--chat-id", "oc_123"], settings=settings)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["lark-cli", "im", "+messages-send", "--chat-id", "oc_123"]

    def test_business_error_ok_false(self, settings):
        """lark-cli exit 0 但返回 ok: false 的业务错误。"""
        error_response = json.dumps({
            "ok": False,
            "error": {"code": 91402, "message": "NOTEXIST"},
        })
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=error_response, stderr="")
            result = execute(["base", "+record-search"], settings=settings)

        assert result.success is False
        assert result.error_code == "E_BUSINESS_ERROR"
        assert "NOTEXIST" in result.error_message
        assert result.data is not None  # 原始数据仍保留

    def test_business_error_preserves_data(self, settings):
        """业务错误时保留原始 JSON 数据。"""
        error_response = json.dumps({
            "ok": False,
            "error": {"code": 1, "message": "invalid document token"},
        })
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=error_response, stderr="")
            result = execute(["docs", "+fetch"], settings=settings)

        assert result.success is False
        assert result.data["ok"] is False
        assert result.data["error"]["code"] == 1


class TestCheckCliAvailable:
    """check_cli_available() 测试。"""

    def test_cli_available(self, settings):
        """lark-cli 可用。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="1.0.50", stderr="")
            # 不应抛异常
            check_cli_available(settings)

    def test_cli_not_found(self, settings):
        """lark-cli 未安装。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(ExecutionError) as exc_info:
                check_cli_available(settings)
            assert exc_info.value.error_code == "E_CLI_NOT_FOUND"

    def test_cli_timeout(self, settings):
        """lark-cli --version 超时。"""
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="lark-cli", timeout=10)
            with pytest.raises(ExecutionError) as exc_info:
                check_cli_available(settings)
            assert exc_info.value.error_code == "E_CLI_NOT_FOUND"
