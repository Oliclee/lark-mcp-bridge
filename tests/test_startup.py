"""startup.py 单元测试。"""

import json
import logging
from unittest.mock import Mock, patch

import pytest

from lark_mcp_bridge.config import BridgeSettings
from lark_mcp_bridge.startup import (
    JsonFormatter,
    preflight_check,
    print_banner,
    setup_logging,
)


@pytest.fixture
def settings():
    return BridgeSettings(cli_path="lark-cli", log_level="DEBUG", log_format="json")


class TestJsonFormatter:
    """JsonFormatter 测试。"""

    def test_format_basic(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello"
        assert "ts" in parsed


class TestSetupLogging:
    """setup_logging() 测试。"""

    def test_configures_logger(self, settings):
        setup_logging(settings)
        logger = logging.getLogger("lark_mcp_bridge")
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

    def test_text_format(self):
        settings = BridgeSettings(log_format="text", log_level="INFO")
        setup_logging(settings)
        logger = logging.getLogger("lark_mcp_bridge")
        assert logger.handlers[0].formatter is not None


class TestPrintBanner:
    """print_banner() 测试。"""

    def test_outputs_to_stderr(self, settings, capsys):
        print_banner(settings)
        captured = capsys.readouterr()
        assert "lark-mcp-bridge" in captured.err
        assert "stdio" in captured.err
        assert captured.out == ""  # stdout 不应有输出


class TestPreflightCheck:
    """preflight_check() 测试。"""

    def test_cli_available_and_auth_ready(self, settings):
        """lark-cli 可用且认证就绪。"""
        auth_output = json.dumps({
            "identity": "user",
            "identities": {
                "user": {"available": True, "status": "ready"},
                "bot": {"available": True, "status": "ready"},
            },
        })
        with patch("lark_mcp_bridge.startup.subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="lark-cli version 1.0.43", stderr=""),
                Mock(returncode=0, stdout=auth_output, stderr=""),
            ]
            result = preflight_check(settings)

        assert result["cli_available"] is True
        assert result["cli_version"] == "lark-cli version 1.0.43"
        assert result["auth_ready"] is True
        assert result["identity"] == "user"
        assert result["warnings"] == []

    def test_cli_not_found(self, settings):
        """lark-cli 不存在。"""
        with patch("lark_mcp_bridge.startup.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = preflight_check(settings)

        assert result["cli_available"] is False
        assert len(result["warnings"]) > 0

    def test_auth_not_ready(self, settings):
        """认证未就绪。"""
        auth_output = json.dumps({
            "identity": "",
            "identities": {
                "user": {"available": False, "status": "not_logged_in"},
            },
        })
        with patch("lark_mcp_bridge.startup.subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="lark-cli version 1.0.43", stderr=""),
                Mock(returncode=0, stdout=auth_output, stderr=""),
            ]
            result = preflight_check(settings)

        assert result["cli_available"] is True
        assert result["auth_ready"] is False
        assert any("auth" in w or "身份" in w for w in result["warnings"])
