"""audit.py 单元测试。"""

import json
from pathlib import Path

import pytest

from lark_mcp_bridge.audit import AuditLogger, _mask_id, _summarize_params
from lark_mcp_bridge.config import BridgeSettings


class TestMaskId:
    """_mask_id() 测试。"""

    def test_normal_id(self):
        assert _mask_id("ou_e9e6a7044aaaeb29939fecc1bcd20e99") == "ou_***e99"

    def test_short_id(self):
        assert _mask_id("abc") == "***"

    def test_exact_8_chars(self):
        assert _mask_id("12345678") == "***"


class TestSummarizeParams:
    """_summarize_params() 测试。"""

    def test_read_operation_masks_ids(self):
        params = {"chat_id": "oc_abcdef123456", "text": "hello world"}
        result = _summarize_params(params, "read")
        assert "***" in result["chat_id"]
        assert result["text"] == "<11 chars>"

    def test_write_operation_keeps_all(self):
        params = {"chat_id": "oc_abcdef123456", "text": "hello world"}
        result = _summarize_params(params, "write")
        assert result["chat_id"] == "oc_abcdef123456"
        assert result["text"] == "hello world"

    def test_destructive_keeps_all(self):
        params = {"userId": "ou_xxx", "content": "secret"}
        result = _summarize_params(params, "destructive")
        assert result == params


class TestAuditLogger:
    """AuditLogger 测试。"""

    @pytest.fixture
    def audit_file(self, tmp_path):
        return tmp_path / "audit.jsonl"

    @pytest.fixture
    def logger(self, audit_file):
        settings = BridgeSettings(
            audit_log=str(audit_file),
            audit_level="all",
        )
        return AuditLogger(settings)

    @pytest.fixture
    def write_only_logger(self, audit_file):
        settings = BridgeSettings(
            audit_log=str(audit_file),
            audit_level="write",
        )
        return AuditLogger(settings)

    def test_enabled(self, logger):
        assert logger.enabled is True

    def test_disabled(self):
        settings = BridgeSettings(audit_log=None)
        logger = AuditLogger(settings)
        assert logger.enabled is False

    def test_log_tool_call(self, logger, audit_file):
        logger.log_tool_call("lark.calendar.agenda", "read", {"start_time": "2026-01-01"})
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event"] == "TOOL_CALL"
        assert event["tool"] == "lark.calendar.agenda"
        assert event["risk_level"] == "read"

    def test_log_tool_result(self, logger, audit_file):
        logger.log_tool_result("lark.im.messages-send", "write", True, 500)
        lines = audit_file.read_text().strip().split("\n")
        event = json.loads(lines[0])
        assert event["event"] == "TOOL_RESULT"
        assert event["success"] is True
        assert event["duration_ms"] == 500

    def test_log_tool_result_with_error(self, logger, audit_file):
        logger.log_tool_result("lark.im.messages-send", "write", False, 100, "E_AUTH_EXPIRED")
        event = json.loads(audit_file.read_text().strip())
        assert event["error_code"] == "E_AUTH_EXPIRED"

    def test_log_tool_blocked(self, logger, audit_file):
        logger.log_tool_blocked("lark.admin.users-list", "黑名单拦截")
        event = json.loads(audit_file.read_text().strip())
        assert event["event"] == "TOOL_BLOCKED"
        assert event["reason"] == "黑名单拦截"

    def test_log_auth_error(self, logger, audit_file):
        logger.log_auth_error("E_AUTH_EXPIRED")
        event = json.loads(audit_file.read_text().strip())
        assert event["event"] == "AUTH_ERROR"

    def test_write_level_skips_read(self, write_only_logger, audit_file):
        """write 级别不记录 read 操作。"""
        write_only_logger.log_tool_call("lark.calendar.agenda", "read", {})
        assert not audit_file.exists() or audit_file.read_text() == ""

    def test_write_level_logs_write(self, write_only_logger, audit_file):
        """write 级别记录 write 操作。"""
        write_only_logger.log_tool_call("lark.im.messages-send", "write", {"text": "hi"})
        assert audit_file.exists()
        event = json.loads(audit_file.read_text().strip())
        assert event["event"] == "TOOL_CALL"

    def test_blocked_always_logged(self, write_only_logger, audit_file):
        """拦截事件始终记录，不受 level 限制。"""
        write_only_logger.log_tool_blocked("lark.admin.delete", "黑名单")
        assert audit_file.exists()

    def test_multiple_events_appended(self, logger, audit_file):
        """多个事件追加写入。"""
        logger.log_tool_call("tool1", "read", {})
        logger.log_tool_call("tool2", "write", {})
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 2
