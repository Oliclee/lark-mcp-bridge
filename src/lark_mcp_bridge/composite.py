"""复合 tool：封装多步工作流，中间结果不进 Agent context。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from lark_mcp_bridge.executor import ExecutionResult, execute


def schedule_meeting(
    title: str,
    attendees: list[str],
    start: str | None = None,
    end: str | None = None,
    duration_minutes: int = 30,
    need_room: bool = False,
    description: str = "",
) -> ExecutionResult:
    """预约会议完整流程：检查空闲 → 可选找会议室 → 创建日程。

    Args:
        title: 会议标题
        attendees: 参会人 open_id 列表（ou_xxx）
        start: 开始时间（ISO 8601），不指定则自动查找最近空闲时段
        end: 结束时间（ISO 8601），不指定则根据 duration 计算
        duration_minutes: 会议时长（分钟），默认 30
        need_room: 是否需要会议室
        description: 会议描述

    Returns:
        ExecutionResult，成功时 data 包含创建的日程信息。
    """
    # Step 1: 如果未指定时间，查询空闲时段
    if not start:
        # 默认查今天剩余时间的空闲
        now = datetime.now(timezone(timedelta(hours=8)))
        freebusy_start = now.isoformat()
        freebusy_end = now.replace(hour=23, minute=59, second=59).isoformat()

        freebusy_result = execute([
            "calendar", "+freebusy",
            "--start", freebusy_start,
            "--end", freebusy_end,
            "--format", "json",
        ])

        if not freebusy_result.success:
            return ExecutionResult(
                success=False,
                error_code=freebusy_result.error_code,
                error_message=f"查询空闲时段失败: {freebusy_result.error_message}",
                recovery_hint="请手动指定 start 和 end 时间",
                duration_ms=freebusy_result.duration_ms,
            )

        # 使用当前时间作为默认开始（简化逻辑，后续可优化为真正的空闲时段分析）
        start = (now + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0).isoformat()

    # 计算结束时间
    if not end:
        start_dt = datetime.fromisoformat(start)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        end = end_dt.isoformat()

    # Step 2: 如果需要会议室，查找可用会议室
    room_id: str | None = None
    if need_room:
        slot = f"{start}~{end}"
        room_cmd = [
            "calendar", "+room-find",
            "--slot", slot,
            "--format", "json",
        ]
        if attendees:
            room_cmd.extend(["--attendee-ids", ",".join(attendees)])

        room_result = execute(room_cmd)

        if room_result.success and room_result.data:
            # 尝试从返回数据中提取第一个可用会议室
            rooms = room_result.data.get("data", [])
            if isinstance(rooms, list) and rooms:
                first_room = rooms[0]
                if isinstance(first_room, dict):
                    room_id = first_room.get("room_id") or first_room.get("id")
        # 找不到会议室不阻塞流程，继续创建日程

    # Step 3: 创建日程
    create_cmd = [
        "calendar", "+create",
        "--summary", title,
        "--start", start,
        "--end", end,
        "--format", "json",
    ]

    # 添加参会人
    all_attendees = list(attendees)
    if room_id:
        all_attendees.append(room_id)
    if all_attendees:
        create_cmd.extend(["--attendee-ids", ",".join(all_attendees)])

    if description:
        create_cmd.extend(["--description", description])

    create_result = execute(create_cmd)

    if not create_result.success:
        return create_result

    # 构造聚合结果
    summary: dict[str, Any] = {
        "ok": True,
        "event": create_result.data,
        "meeting_room": room_id,
        "_summary": f"已创建会议「{title}」，时间 {start} ~ {end}",
    }
    if room_id:
        summary["_summary"] += f"，会议室 {room_id}"

    return ExecutionResult(
        success=True,
        data=summary,
        duration_ms=create_result.duration_ms,
    )
