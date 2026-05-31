"""Phase 5.1 P2 shortcut tools 测试（vc / minutes）。"""

import json
from unittest.mock import patch

import pytest

from lark_mcp_bridge.executor import ExecutionResult
from lark_mcp_bridge.server import (
    minutes_search,
    vc_notes,
    vc_search,
)


class TestVcSearch:
    """lark.vc.search 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_search(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"meetings": []}},
            duration_ms=300,
        )
        output = vc_search(query="周会")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+search" in call_args
        assert "--query" in call_args
        assert "周会" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_with_time_range(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        vc_search(start="2026-06-01", end="2026-06-30")
        call_args = mock_execute.call_args[0][0]
        assert "--start" in call_args
        assert "--end" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_with_participants(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        vc_search(participant_ids="ou_aaa,ou_bbb")
        call_args = mock_execute.call_args[0][0]
        assert "--participant-ids" in call_args
        assert "ou_aaa,ou_bbb" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_no_filters(self, mock_execute):
        """无过滤条件时仍能调用。"""
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        vc_search()
        call_args = mock_execute.call_args[0][0]
        assert "+search" in call_args
        assert "--format" in call_args


class TestVcNotes:
    """lark.vc.notes 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_by_meeting_ids(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"notes": []}},
            duration_ms=400,
        )
        output = vc_notes(meeting_ids="m_123,m_456")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+notes" in call_args
        assert "--meeting-ids" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_by_minute_tokens(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=300
        )
        vc_notes(minute_tokens="obcnXXX")
        call_args = mock_execute.call_args[0][0]
        assert "--minute-tokens" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_by_calendar_event_ids(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=300
        )
        vc_notes(calendar_event_ids="ev_123")
        call_args = mock_execute.call_args[0][0]
        assert "--calendar-event-ids" in call_args


class TestMinutesSearch:
    """lark.minutes.search 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_search(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"minutes": []}},
            duration_ms=250,
        )
        output = minutes_search(query="产品评审")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+search" in call_args
        assert "--query" in call_args
        assert "产品评审" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_with_time_and_participants(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        minutes_search(start="2026-06-01", end="2026-06-30", participant_ids="me")
        call_args = mock_execute.call_args[0][0]
        assert "--start" in call_args
        assert "--end" in call_args
        assert "--participant-ids" in call_args
        assert "me" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_custom_page_size(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        minutes_search(page_size=5)
        call_args = mock_execute.call_args[0][0]
        assert "5" in call_args
