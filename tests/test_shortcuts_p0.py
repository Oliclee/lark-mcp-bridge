"""Phase 5.1 P0 shortcut tools 测试。"""

import json
from unittest.mock import patch

import pytest

from lark_mcp_bridge.executor import ExecutionResult
from lark_mcp_bridge.server import (
    mail_list,
    mail_send,
    sheets_read,
    sheets_write,
    task_create,
    task_list,
)


class TestSheetsRead:
    """lark.sheets.read 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_read(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"values": [["a", "b"], ["c", "d"]]}},
            duration_ms=200,
        )
        output = sheets_read(range="A1:B2", spreadsheet_token="shtcnXXX")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+read" in call_args
        assert "--range" in call_args
        assert "--spreadsheet-token" in call_args
        assert "--format" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_read_with_url(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=100
        )
        sheets_read(range="A1:D10", url="https://example.com/sheets/xxx")
        call_args = mock_execute.call_args[0][0]
        assert "--url" in call_args
        assert "--spreadsheet-token" not in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_read_with_sheet_id(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=100
        )
        sheets_read(range="A1:D10", spreadsheet_token="shtcnXXX", sheet_id="abc123")
        call_args = mock_execute.call_args[0][0]
        assert "--sheet-id" in call_args


class TestSheetsWrite:
    """lark.sheets.write 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_write(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"updated_cells": 4}},
            duration_ms=300,
        )
        values = '[["a","b"],["c","d"]]'
        output = sheets_write(range="A1:B2", values=values, spreadsheet_token="shtcnXXX")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+write" in call_args
        assert "--values" in call_args
        assert values in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_write_no_format_flag(self, mock_execute):
        """sheets +write 不需要 --format（默认 JSON）。"""
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=100
        )
        sheets_write(range="A1", values='[["x"]]', spreadsheet_token="shtcnXXX")
        call_args = mock_execute.call_args[0][0]
        # write 没有 --format flag
        assert "--format" not in call_args


class TestTaskList:
    """lark.task.list 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_list(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"tasks": []}},
            duration_ms=200,
        )
        output = task_list()
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+get-my-tasks" in call_args
        assert "--format" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_with_query(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=100
        )
        task_list(query="报告")
        call_args = mock_execute.call_args[0][0]
        assert "--query" in call_args
        assert "报告" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_completed(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=100
        )
        task_list(complete=True)
        call_args = mock_execute.call_args[0][0]
        assert "--complete" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_with_due_range(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=100
        )
        task_list(due_start="2026-06-01", due_end="2026-06-30")
        call_args = mock_execute.call_args[0][0]
        assert "--due-start" in call_args
        assert "--due-end" in call_args


class TestTaskCreate:
    """lark.task.create 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_create(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"task_id": "t_123"}},
            duration_ms=300,
        )
        output = task_create(summary="完成报告")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+create" in call_args
        assert "--summary" in call_args
        assert "完成报告" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_create_with_all_params(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=200
        )
        task_create(
            summary="写文档",
            description="完成 API 文档",
            due="+3d",
            assignee="ou_xxx",
        )
        call_args = mock_execute.call_args[0][0]
        assert "--description" in call_args
        assert "--due" in call_args
        assert "--assignee" in call_args


class TestMailSend:
    """lark.mail.send 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_send_draft(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"draft_id": "d_123"}},
            duration_ms=400,
        )
        output = mail_send(to="alice@example.com", subject="测试", body="你好")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+send" in call_args
        assert "--to" in call_args
        assert "--subject" in call_args
        assert "--body" in call_args
        assert "--confirm-send" not in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_send_immediately(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=500
        )
        mail_send(to="bob@example.com", subject="紧急", body="请查看", confirm_send=True)
        call_args = mock_execute.call_args[0][0]
        assert "--confirm-send" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_send_with_cc_bcc(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=300
        )
        mail_send(
            to="alice@example.com",
            subject="会议纪要",
            body="附件",
            cc="bob@example.com",
            bcc="charlie@example.com",
        )
        call_args = mock_execute.call_args[0][0]
        assert "--cc" in call_args
        assert "--bcc" in call_args


class TestMailList:
    """lark.mail.list 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_list(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"messages": []}},
            duration_ms=200,
        )
        output = mail_list()
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+triage" in call_args
        assert "--format" in call_args
        assert "--max" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_with_query(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=150
        )
        mail_list(query="budget report")
        call_args = mock_execute.call_args[0][0]
        assert "--query" in call_args
        assert "budget report" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_with_filter(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=150
        )
        filter_str = '{"folder":"INBOX"}'
        mail_list(filter_json=filter_str)
        call_args = mock_execute.call_args[0][0]
        assert "--filter" in call_args
        assert filter_str in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_list_custom_max(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=100
        )
        mail_list(max_count=50)
        call_args = mock_execute.call_args[0][0]
        assert "50" in call_args
