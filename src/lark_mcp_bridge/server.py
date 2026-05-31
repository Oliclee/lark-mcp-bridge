"""FastMCP server 入口：注册 tools / prompts / resources，管理生命周期。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lark_mcp_bridge.config import get_settings
from lark_mcp_bridge.executor import ExecutionResult, execute
from lark_mcp_bridge.filters import get_risk_level, is_allowed

mcp = FastMCP(
    "Lark MCP Bridge",
    instructions="飞书集成——消息、日历、文档、多维表格等",
)


# === MCP Resources ===
# 注：Quick 目前不消费 MCP Resources，保留注册以备未来兼容。
# 同时提供等价的 tool 供 Agent 调用。


@mcp.resource("lark://identity")
def resource_identity() -> str:
    """当前登录身份信息。"""
    from lark_mcp_bridge.resources import get_identity
    return json.dumps(get_identity(), ensure_ascii=False, indent=2)


@mcp.resource("lark://permissions")
def resource_permissions() -> str:
    """已授权的 scope 列表。"""
    from lark_mcp_bridge.resources import get_permissions
    return json.dumps(get_permissions(), ensure_ascii=False, indent=2)


@mcp.resource("lark://domains")
def resource_domains() -> str:
    """可用域概览。"""
    from lark_mcp_bridge.resources import get_domains_summary
    return json.dumps(get_domains_summary(), ensure_ascii=False, indent=2)


# === Resources as Tools（Quick 兼容） ===


@mcp.tool(
    name="lark.identity",
    description="查看当前飞书登录身份（用户/机器人）、状态、open_id 等信息。",
)
def tool_identity() -> str:
    """获取当前身份信息。"""
    from lark_mcp_bridge.resources import get_identity
    return json.dumps(get_identity(), ensure_ascii=False, indent=2)


@mcp.tool(
    name="lark.permissions",
    description="查看当前飞书应用已授权的 scope 列表。用于判断哪些操作可执行。",
)
def tool_permissions() -> str:
    """获取已授权权限列表。"""
    from lark_mcp_bridge.resources import get_permissions
    return json.dumps(get_permissions(), ensure_ascii=False, indent=2)


@mcp.tool(
    name="lark.domains",
    description="查看所有可用的飞书域及各域 tool 数量概览。",
)
def tool_domains() -> str:
    """获取域概览。"""
    from lark_mcp_bridge.resources import get_domains_summary
    return json.dumps(get_domains_summary(), ensure_ascii=False, indent=2)


# === Prompt 注册 ===

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@mcp.prompt(
    name="lark-calendar-workflow",
    description="飞书日历操作完整指南——查询日程、创建会议、处理冲突",
)
def calendar_workflow_prompt() -> str:
    """返回日历域工作流 Prompt。"""
    prompt_file = _PROMPTS_DIR / "calendar.md"
    content = prompt_file.read_text(encoding="utf-8")
    # 去掉 YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    return content


def _format_result(result: ExecutionResult) -> str:
    """将 ExecutionResult 格式化为 MCP tool 返回文本。"""
    if result.success:
        return json.dumps(result.data, ensure_ascii=False, indent=2)
    else:
        error_payload = {
            "error_code": result.error_code,
            "message": result.error_message,
            "recovery_hint": result.recovery_hint,
        }
        return json.dumps(error_payload, ensure_ascii=False, indent=2)


def _check_permission(tool_name: str) -> str | None:
    """检查 tool 是否被允许执行。返回 None 表示允许，否则返回错误信息。"""
    if not is_allowed(tool_name):
        error_payload = {
            "error_code": "E_BLOCKED",
            "message": f"命令 {tool_name} 被安全策略禁止",
            "recovery_hint": "此命令被安全策略禁止。详见 SECURITY.md",
        }
        return json.dumps(error_payload, ensure_ascii=False, indent=2)
    return None


# === Phase 1: 5 个固定 MCP tool ===
# 命名规范：lark.<domain>.<action>（MCP 规范仅允许 A-Z a-z 0-9 _ - .）


@mcp.tool(
    name="lark.im.messages-send",
    description="发送消息到指定会话或用户。支持 text、markdown、post、image 等消息类型。chat_id 和 user_id 二选一。[user/bot 身份均可]",
)
def im_messages_send(
    text: str,
    chat_id: str | None = None,
    user_id: str | None = None,
    markdown: str | None = None,
    msg_type: str = "text",
) -> str:
    """发送飞书消息。

    Args:
        text: 纯文本消息内容（与 markdown 二选一）
        chat_id: 会话 ID（oc_xxx），与 user_id 互斥
        user_id: 用户 open_id（ou_xxx），与 chat_id 互斥
        markdown: markdown 格式消息（与 text 二选一）
        msg_type: 消息类型，默认 text
    """
    blocked = _check_permission("lark.im.messages-send")
    if blocked:
        return blocked

    command = ["im", "+messages-send"]

    if chat_id:
        command.extend(["--chat-id", chat_id])
    elif user_id:
        command.extend(["--user-id", user_id])

    if markdown:
        command.extend(["--markdown", markdown])
    else:
        command.extend(["--text", text])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.calendar.agenda",
    description="查看日历日程，默认展示今天的安排。可指定日期范围。[需要 user 身份]",
)
def calendar_agenda(
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """查询日历日程。

    Args:
        start_time: 开始时间（ISO 8601 格式，默认：今天起始）
        end_time: 结束时间（ISO 8601 格式，默认：今天结束）
    """
    blocked = _check_permission("lark.calendar.agenda")
    if blocked:
        return blocked

    command = ["calendar", "+agenda", "--format", "json"]
    if start_time:
        command.extend(["--start-time", start_time])
    if end_time:
        command.extend(["--end-time", end_time])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.base.record-search",
    description="搜索多维表格记录。根据关键词在指定表格中搜索。[user/bot 身份均可]",
)
def base_record_search(
    base_token: str,
    table_id: str,
    keyword: str,
    search_fields: str | None = None,
    select_fields: str | None = None,
    limit: int = 10,
) -> str:
    """搜索多维表格记录。

    Args:
        base_token: 多维表格 Base Token
        table_id: 数据表 ID（tbl 开头）或表名
        keyword: 搜索关键词
        search_fields: 搜索字段列表（逗号分隔的字段名），不指定则搜索所有文本字段
        select_fields: 返回字段列表（逗号分隔的字段名），不指定则返回所有字段
        limit: 返回记录数上限，1-200，默认 10
    """
    blocked = _check_permission("lark.base.record-search")
    if blocked:
        return blocked

    # 构造 JSON 参数
    search_json: dict[str, Any] = {"keyword": keyword, "limit": limit}
    if search_fields:
        search_json["search_fields"] = [f.strip() for f in search_fields.split(",")]
    if select_fields:
        search_json["select_fields"] = [f.strip() for f in select_fields.split(",")]

    command = [
        "base",
        "+record-search",
        "--base-token", base_token,
        "--table-id", table_id,
        "--json", json.dumps(search_json, ensure_ascii=False),
        "--format", "json",
    ]
    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.docs.fetch",
    description="读取飞书文档内容。支持通过文档 URL 或 token 获取。[需要 user 身份]",
)
def docs_fetch(
    doc: str,
) -> str:
    """获取飞书文档内容。

    Args:
        doc: 文档 URL 或 document token
    """
    blocked = _check_permission("lark.docs.fetch")
    if blocked:
        return blocked

    command = [
        "docs",
        "+fetch",
        "--doc", doc,
        "--api-version", "v2",
        "--format", "json",
    ]
    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.contact.search-user",
    description="搜索飞书联系人。支持按姓名、邮箱等关键词搜索用户。[需要 user 身份]",
)
def contact_search_user(
    query: str,
    page_size: int = 20,
) -> str:
    """搜索联系人。

    Args:
        query: 搜索关键词（姓名、邮箱等，最多 50 字符）
        page_size: 每页返回数量，1-30，默认 20
    """
    blocked = _check_permission("lark.contact.search-user")
    if blocked:
        return blocked

    command = [
        "contact",
        "+search-user",
        "--query", query,
        "--page-size", str(page_size),
        "--format", "json",
    ]
    result = execute(command)
    return _format_result(result)


# === Phase 5.1 P0: 新增 shortcut tools ===


@mcp.tool(
    name="lark.sheets.read",
    description="读取电子表格数据。支持通过 URL 或 token + range 指定读取范围。[需要 user 身份]",
)
def sheets_read(
    range: str,
    spreadsheet_token: str | None = None,
    url: str | None = None,
    sheet_id: str | None = None,
) -> str:
    """读取电子表格单元格数据。

    Args:
        range: 读取范围（如 "A1:D10"、"Sheet1!A1:D10"、或单个单元格 "C2"）
        spreadsheet_token: 电子表格 token（与 url 二选一）
        url: 电子表格 URL（与 spreadsheet_token 二选一）
        sheet_id: 工作表 ID（当 range 中未包含 sheetId 时使用）
    """
    blocked = _check_permission("lark.sheets.read")
    if blocked:
        return blocked

    command = ["sheets", "+read", "--range", range, "--format", "json"]
    if spreadsheet_token:
        command.extend(["--spreadsheet-token", spreadsheet_token])
    elif url:
        command.extend(["--url", url])
    if sheet_id:
        command.extend(["--sheet-id", sheet_id])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.sheets.write",
    description="写入电子表格数据（覆盖模式）。支持通过 URL 或 token + range 指定写入范围。[需要 user 身份]",
)
def sheets_write(
    range: str,
    values: str,
    spreadsheet_token: str | None = None,
    url: str | None = None,
    sheet_id: str | None = None,
) -> str:
    """写入电子表格单元格数据。

    Args:
        range: 写入范围（如 "A1:D10"、"Sheet1!A1:D10"）
        values: 二维数组 JSON（如 '[["a","b"],["c","d"]]'）
        spreadsheet_token: 电子表格 token（与 url 二选一）
        url: 电子表格 URL（与 spreadsheet_token 二选一）
        sheet_id: 工作表 ID（当 range 中未包含 sheetId 时使用）
    """
    blocked = _check_permission("lark.sheets.write")
    if blocked:
        return blocked

    command = ["sheets", "+write", "--range", range, "--values", values]
    if spreadsheet_token:
        command.extend(["--spreadsheet-token", spreadsheet_token])
    elif url:
        command.extend(["--url", url])
    if sheet_id:
        command.extend(["--sheet-id", sheet_id])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.task.list",
    description="查看分配给我的任务列表。支持按完成状态、截止日期、关键词过滤。[需要 user 身份]",
)
def task_list(
    query: str | None = None,
    complete: bool | None = None,
    due_start: str | None = None,
    due_end: str | None = None,
    page_limit: int = 20,
) -> str:
    """查看我的任务列表。

    Args:
        query: 按任务标题搜索（精确匹配优先，然后部分匹配）
        complete: True=已完成，False=未完成，不指定=全部
        due_start: 截止日期起始（ISO 8601 / 相对时间如 +2d）
        due_end: 截止日期结束（ISO 8601 / 相对时间）
        page_limit: 每页数量，默认 20，最大 40
    """
    blocked = _check_permission("lark.task.list")
    if blocked:
        return blocked

    command = ["task", "+get-my-tasks", "--format", "json", "--page-limit", str(page_limit)]
    if query:
        command.extend(["--query", query])
    if complete is True:
        command.append("--complete")
    elif complete is False:
        pass  # 不传 --complete 默认查全部，lark-cli 无 --incomplete flag
    if due_start:
        command.extend(["--due-start", due_start])
    if due_end:
        command.extend(["--due-end", due_end])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.task.create",
    description="创建任务。支持设置标题、描述、截止日期、负责人。[需要 user 身份]",
)
def task_create(
    summary: str,
    description: str | None = None,
    due: str | None = None,
    assignee: str | None = None,
) -> str:
    """创建任务。

    Args:
        summary: 任务标题
        description: 任务描述
        due: 截止日期（ISO 8601 / date:YYYY-MM-DD / 相对时间如 +2d）
        assignee: 负责人 open_id（ou_xxx）
    """
    blocked = _check_permission("lark.task.create")
    if blocked:
        return blocked

    command = ["task", "+create", "--summary", summary, "--format", "json"]
    if description:
        command.extend(["--description", description])
    if due:
        command.extend(["--due", due])
    if assignee:
        command.extend(["--assignee", assignee])

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.mail.send",
    description="发送邮件。默认保存为草稿，使用 confirm_send=true 立即发送。[需要 user 身份]",
)
def mail_send(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    confirm_send: bool = False,
) -> str:
    """发送邮件。

    Args:
        to: 收件人邮箱（多个用逗号分隔）
        subject: 邮件主题
        body: 邮件正文（支持 HTML 格式）
        cc: 抄送邮箱（多个用逗号分隔）
        bcc: 密送邮箱（多个用逗号分隔）
        confirm_send: 是否立即发送（默认 false，仅保存草稿）
    """
    blocked = _check_permission("lark.mail.send")
    if blocked:
        return blocked

    command = ["mail", "+send", "--to", to, "--subject", subject, "--body", body, "--format", "json"]
    if cc:
        command.extend(["--cc", cc])
    if bcc:
        command.extend(["--bcc", bcc])
    if confirm_send:
        command.append("--confirm-send")

    result = execute(command)
    return _format_result(result)


@mcp.tool(
    name="lark.mail.list",
    description="查看邮件列表（摘要）。支持全文搜索和条件过滤。[需要 user 身份]",
)
def mail_list(
    query: str | None = None,
    max_count: int = 20,
    filter_json: str | None = None,
) -> str:
    """查看邮件列表。

    Args:
        query: 全文搜索关键词（搜索发件人/收件人/主题/正文，最多 50 字符）
        max_count: 最大返回数量，1-400，默认 20
        filter_json: 精确匹配过滤条件 JSON（如 '{"folder":"INBOX","from":["alice@example.com"]}'）
    """
    blocked = _check_permission("lark.mail.list")
    if blocked:
        return blocked

    command = ["mail", "+triage", "--format", "json", "--max", str(max_count)]
    if query:
        command.extend(["--query", query])
    if filter_json:
        command.extend(["--filter", filter_json])

    result = execute(command)
    return _format_result(result)


# === Phase 2: 动态发现 + lark.discover meta-tool ===

# 启动时加载所有 tool 定义（用于 discover 查询）
_all_discovered_tools: list[Any] = []


def _load_discovered_tools() -> None:
    """启动时加载 discovery 结果。"""
    global _all_discovered_tools
    try:
        from lark_mcp_bridge.discovery import discover_tools
        _all_discovered_tools = discover_tools()
    except Exception:
        _all_discovered_tools = []


# 延迟加载：首次调用 discover 时触发
_discovery_loaded = False


def _ensure_discovery() -> None:
    global _discovery_loaded
    if not _discovery_loaded:
        _load_discovered_tools()
        _discovery_loaded = True


@mcp.tool(
    name="lark.discover",
    description="查询指定飞书域下所有可用的 API 操作。当已有 tool 无法满足需求时使用。返回该域下所有可调用的操作列表。",
)
def lark_discover(
    domain: str,
    keyword: str | None = None,
) -> str:
    """发现指定域的可用操作。

    Args:
        domain: 飞书域名（如 calendar, im, base, mail, task, drive, approval, wiki, sheets, okr 等）
        keyword: 可选，按关键词过滤操作描述
    """
    _ensure_discovery()

    from lark_mcp_bridge.discovery import get_tools_by_domain

    domains = get_tools_by_domain(_all_discovered_tools)
    domain_tools = domains.get(domain, [])

    if keyword:
        keyword_lower = keyword.lower()
        domain_tools = [
            t for t in domain_tools
            if keyword_lower in t.description.lower() or keyword_lower in t.name.lower()
        ]

    result = {
        "domain": domain,
        "available_tools": [
            {
                "name": t.name,
                "cli_command": t.cli_command,
                "description": t.description + (
                    " ⚠️ 高风险操作，需确认" if t.danger else ""
                ) + (
                    f" [需要 {t.required_identity} 身份]" if t.required_identity != "both" else ""
                ),
                "risk_level": t.risk_level,
                "required_identity": t.required_identity,
                "danger": t.danger,
            }
            for t in domain_tools
        ],
        "total": len(domain_tools),
        "_hint": "上述操作为 REST API 级别的原子操作。如需使用，请告知具体操作名称。",
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# === Phase 1.5: Composite tool ===


@mcp.tool(
    name="lark.calendar.schedule-meeting",
    description="预约会议（完整流程）：自动检查参会人空闲时间、可选查找会议室、创建日程并邀请参会人。内部编排多步操作，只返回最终结果。[需要 user 身份]",
)
def calendar_schedule_meeting(
    title: str,
    attendees: str,
    start: str | None = None,
    end: str | None = None,
    duration_minutes: int = 30,
    need_room: bool = False,
    description: str = "",
) -> str:
    """预约会议。

    Args:
        title: 会议标题
        attendees: 参会人 open_id 列表（逗号分隔，如 "ou_xxx,ou_yyy"）
        start: 开始时间（ISO 8601 格式），不指定则自动选择最近可用时段
        end: 结束时间（ISO 8601 格式），不指定则根据 duration_minutes 计算
        duration_minutes: 会议时长（分钟），默认 30
        need_room: 是否需要会议室，默认 false
        description: 会议描述
    """
    blocked = _check_permission("lark.calendar.schedule-meeting")
    if blocked:
        return blocked

    from lark_mcp_bridge.composite import schedule_meeting

    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
    result = schedule_meeting(
        title=title,
        attendees=attendee_list,
        start=start,
        end=end,
        duration_minutes=duration_minutes,
        need_room=need_room,
        description=description,
    )
    return _format_result(result)


def main() -> None:
    """启动 MCP server（stdio transport）。"""
    from lark_mcp_bridge.startup import run_startup
    run_startup()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
