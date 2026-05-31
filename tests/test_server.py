"""server.py 集成测试：验证 tool 注册和基本调用。"""

import json
from unittest.mock import patch

import pytest

from lark_mcp_bridge.server import (
    _check_permission,
    _format_result,
    calendar_agenda,
    contact_search_user,
    docs_fetch,
    im_messages_send,
    base_record_search,
)
from lark_mcp_bridge.executor import ExecutionResult


class TestFormatResult:
    """_format_result() 测试。"""

    def test_success_result(self):
        """成功结果格式化。"""
        result = ExecutionResult(
            success=True,
            data={"code": 0, "data": {"id": "123"}},
            duration_ms=100,
        )
        output = _format_result(result)
        parsed = json.loads(output)
        assert parsed["code"] == 0
        assert parsed["data"]["id"] == "123"

    def test_error_result(self):
        """错误结果格式化。"""
        result = ExecutionResult(
            success=False,
            error_code="E_AUTH_EXPIRED",
            error_message="OAuth token 已过期",
            recovery_hint="请运行 lark-cli auth login 重新认证",
            duration_ms=50,
        )
        output = _format_result(result)
        parsed = json.loads(output)
        assert parsed["error_code"] == "E_AUTH_EXPIRED"
        assert "过期" in parsed["message"]
        assert "认证" in parsed["recovery_hint"]


class TestCheckPermission:
    """_check_permission() 测试。"""

    def test_allowed_tool(self):
        """允许的 tool 返回 None。"""
        assert _check_permission("lark.calendar.agenda") is None
        assert _check_permission("lark.docs.fetch") is None
        assert _check_permission("lark.contact.search-user") is None

    def test_blocked_tool(self):
        """被拒绝的 tool 返回错误 JSON。"""
        result = _check_permission("lark.admin.users-list")
        assert result is not None
        parsed = json.loads(result)
        assert parsed["error_code"] == "E_BLOCKED"


class TestToolCalls:
    """Tool 函数集成测试（mock executor）。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_calendar_agenda(self, mock_execute):
        """calendar_agenda 正常调用。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": []},
            duration_ms=200,
        )
        output = calendar_agenda()
        parsed = json.loads(output)
        assert parsed["ok"] is True
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert "calendar" in call_args
        assert "+agenda" in call_args
        assert "--format" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_calendar_agenda_with_time(self, mock_execute):
        """calendar_agenda 带时间参数。"""
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": []}, duration_ms=100
        )
        calendar_agenda(start_time="2026-01-01T00:00:00", end_time="2026-01-02T00:00:00")
        call_args = mock_execute.call_args[0][0]
        assert "--start-time" in call_args
        assert "--end-time" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_im_messages_send_with_chat_id(self, mock_execute):
        """im_messages_send 通过 chat_id 发送。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"message_id": "om_123"}},
            duration_ms=300,
        )
        output = im_messages_send(text="hello", chat_id="oc_123")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "--chat-id" in call_args
        assert "oc_123" in call_args
        assert "--text" in call_args
        # messages-send 不支持 --format flag
        assert "--format" not in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_im_messages_send_with_user_id(self, mock_execute):
        """im_messages_send 通过 user_id 发送。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True},
            duration_ms=200,
        )
        im_messages_send(text="hi", user_id="ou_abc")
        call_args = mock_execute.call_args[0][0]
        assert "--user-id" in call_args
        assert "ou_abc" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_im_messages_send_markdown(self, mock_execute):
        """im_messages_send 发送 markdown。"""
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=200
        )
        im_messages_send(text="", chat_id="oc_123", markdown="**bold**")
        call_args = mock_execute.call_args[0][0]
        assert "--markdown" in call_args
        assert "**bold**" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_contact_search_user(self, mock_execute):
        """contact_search_user 正常调用。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"users": []}},
            duration_ms=150,
        )
        output = contact_search_user(query="张三")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "--query" in call_args
        assert "张三" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_docs_fetch(self, mock_execute):
        """docs_fetch 正常调用。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"content": "..."}},
            duration_ms=250,
        )
        output = docs_fetch(doc="doccnXXXXXX")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "--doc" in call_args
        assert "--api-version" in call_args
        assert "v2" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_base_record_search(self, mock_execute):
        """base_record_search 正常调用。"""
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"records": []}},
            duration_ms=300,
        )
        output = base_record_search(
            base_token="bascXXX", table_id="tblYYY", keyword="test"
        )
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "--base-token" in call_args
        assert "--table-id" in call_args
        assert "--json" in call_args
        # 验证 JSON 参数包含 keyword
        json_idx = call_args.index("--json") + 1
        json_arg = json.loads(call_args[json_idx])
        assert json_arg["keyword"] == "test"
        assert json_arg["limit"] == 10

    @patch("lark_mcp_bridge.server.execute")
    def test_base_record_search_with_fields(self, mock_execute):
        """base_record_search 带字段过滤。"""
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=100
        )
        base_record_search(
            base_token="bascXXX",
            table_id="tblYYY",
            keyword="alice",
            search_fields="Name,Email",
            select_fields="Name,Status",
            limit=50,
        )
        call_args = mock_execute.call_args[0][0]
        json_idx = call_args.index("--json") + 1
        json_arg = json.loads(call_args[json_idx])
        assert json_arg["search_fields"] == ["Name", "Email"]
        assert json_arg["select_fields"] == ["Name", "Status"]
        assert json_arg["limit"] == 50

    @patch("lark_mcp_bridge.server.execute")
    def test_tool_error_propagation(self, mock_execute):
        """tool 执行错误正确传播。"""
        mock_execute.return_value = ExecutionResult(
            success=False,
            error_code="E_AUTH_EXPIRED",
            error_message="token expired",
            recovery_hint="请重新认证",
            duration_ms=50,
        )
        output = calendar_agenda()
        parsed = json.loads(output)
        assert parsed["error_code"] == "E_AUTH_EXPIRED"
