"""composite.py 单元测试。"""

import json
from unittest.mock import patch, call

import pytest

from lark_mcp_bridge.composite import schedule_meeting
from lark_mcp_bridge.executor import ExecutionResult


class TestScheduleMeeting:
    """schedule_meeting() 测试。"""

    @patch("lark_mcp_bridge.composite.execute")
    def test_basic_meeting_with_time(self, mock_execute):
        """指定时间的基本会议创建。"""
        # create 成功
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"event_id": "ev_123"}},
            duration_ms=500,
        )

        result = schedule_meeting(
            title="产品评审",
            attendees=["ou_aaa", "ou_bbb"],
            start="2026-06-01T14:00:00+08:00",
            end="2026-06-01T15:00:00+08:00",
        )

        assert result.success is True
        assert result.data["ok"] is True
        assert "产品评审" in result.data["_summary"]
        # 只调用了 create（因为指定了时间且不需要会议室）
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert "--summary" in call_args
        assert "产品评审" in call_args
        assert "--attendee-ids" in call_args

    @patch("lark_mcp_bridge.composite.execute")
    def test_meeting_with_room(self, mock_execute):
        """需要会议室的会议。"""
        # room-find 返回一个会议室
        room_result = ExecutionResult(
            success=True,
            data={"data": [{"room_id": "omm_room1", "name": "会议室A"}]},
            duration_ms=200,
        )
        # create 成功
        create_result = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"event_id": "ev_456"}},
            duration_ms=300,
        )
        mock_execute.side_effect = [room_result, create_result]

        result = schedule_meeting(
            title="周会",
            attendees=["ou_aaa"],
            start="2026-06-01T10:00:00+08:00",
            duration_minutes=60,
            need_room=True,
        )

        assert result.success is True
        assert result.data["meeting_room"] == "omm_room1"
        assert mock_execute.call_count == 2

    @patch("lark_mcp_bridge.composite.execute")
    def test_meeting_no_room_found(self, mock_execute):
        """找不到会议室时仍创建会议。"""
        # room-find 返回空
        room_result = ExecutionResult(
            success=True,
            data={"data": []},
            duration_ms=200,
        )
        # create 成功
        create_result = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"event_id": "ev_789"}},
            duration_ms=300,
        )
        mock_execute.side_effect = [room_result, create_result]

        result = schedule_meeting(
            title="1:1",
            attendees=["ou_aaa"],
            start="2026-06-01T10:00:00+08:00",
            need_room=True,
        )

        assert result.success is True
        assert result.data["meeting_room"] is None

    @patch("lark_mcp_bridge.composite.execute")
    def test_meeting_without_time(self, mock_execute):
        """不指定时间时自动查询空闲。"""
        # freebusy 成功
        freebusy_result = ExecutionResult(
            success=True,
            data={"ok": True, "data": []},
            duration_ms=150,
        )
        # create 成功
        create_result = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"event_id": "ev_auto"}},
            duration_ms=300,
        )
        mock_execute.side_effect = [freebusy_result, create_result]

        result = schedule_meeting(
            title="临时讨论",
            attendees=["ou_aaa"],
        )

        assert result.success is True
        assert mock_execute.call_count == 2
        # 第一次调用是 freebusy
        first_call = mock_execute.call_args_list[0][0][0]
        assert "+freebusy" in first_call

    @patch("lark_mcp_bridge.composite.execute")
    def test_create_fails(self, mock_execute):
        """创建日程失败时返回错误。"""
        mock_execute.return_value = ExecutionResult(
            success=False,
            error_code="E_PERMISSION_DENIED",
            error_message="权限不足",
            recovery_hint="需要 calendar:event:create scope",
            duration_ms=100,
        )

        result = schedule_meeting(
            title="测试",
            attendees=["ou_aaa"],
            start="2026-06-01T10:00:00+08:00",
        )

        assert result.success is False
        assert result.error_code == "E_PERMISSION_DENIED"

    @patch("lark_mcp_bridge.composite.execute")
    def test_freebusy_fails_returns_hint(self, mock_execute):
        """查询空闲失败时返回提示。"""
        mock_execute.return_value = ExecutionResult(
            success=False,
            error_code="E_AUTH_EXPIRED",
            error_message="token expired",
            recovery_hint="请重新认证",
            duration_ms=50,
        )

        result = schedule_meeting(
            title="测试",
            attendees=["ou_aaa"],
            # 不指定时间，触发 freebusy 查询
        )

        assert result.success is False
        assert "手动指定" in result.recovery_hint
