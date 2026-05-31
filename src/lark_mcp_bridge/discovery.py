"""动态发现：解析 lark-cli schema 元数据，生成 ToolDefinition 列表。"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from lark_mcp_bridge.config import BridgeSettings, get_settings
from lark_mcp_bridge.errors import DiscoveryError


@dataclass
class ToolDefinition:
    """单个 MCP tool 的定义。"""

    name: str  # "lark.im.messages-create"
    cli_command: str  # "im messages create" (原始 schema name)
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    risk_level: Literal["read", "write", "destructive"] = "write"
    required_identity: Literal["user", "bot", "both"] = "both"
    scopes: list[str] = field(default_factory=list)
    doc_url: str | None = None
    danger: bool = False


def _name_to_mcp_tool_name(schema_name: str) -> str:
    """将 schema name 转为 MCP tool name。

    "im chat.members create" → "lark.im.chat-members-create"
    "calendar events patch" → "lark.calendar.events-patch"
    "approval instances cancel" → "lark.approval.instances-cancel"
    """
    parts = schema_name.split()
    if len(parts) < 2:
        return f"lark.{schema_name.replace(' ', '-')}"

    domain = parts[0]
    # 剩余部分用 - 连接，. 也替换为 -
    action = "-".join(parts[1:]).replace(".", "-")
    return f"lark.{domain}.{action}"


def _classify_risk(meta: dict[str, Any]) -> Literal["read", "write", "destructive"]:
    """根据 _meta 分类风险级别。"""
    risk = meta.get("risk", "")
    if risk == "read":
        return "read"
    elif "high-risk" in risk or meta.get("danger", False):
        return "destructive"
    else:
        return "write"


def _classify_identity(meta: dict[str, Any]) -> Literal["user", "bot", "both"]:
    """根据 access_tokens 分类身份要求。"""
    tokens = meta.get("access_tokens", [])
    if tokens == ["user"]:
        return "user"
    elif tokens == ["bot"]:
        return "bot"
    else:
        return "both"


def _clean_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """清理 inputSchema，移除 bridge 内部控制的字段。"""
    props = schema.get("properties", {})
    # 移除 yes 字段（bridge 内部处理确认逻辑）
    cleaned_props = {k: v for k, v in props.items() if k != "yes"}

    cleaned = dict(schema)
    cleaned["properties"] = cleaned_props

    # 从 required 中也移除 yes
    if "required" in cleaned:
        cleaned["required"] = [r for r in cleaned["required"] if r != "yes"]

    return cleaned


def _parse_tool(raw: dict[str, Any]) -> ToolDefinition:
    """解析单个 schema 条目为 ToolDefinition。"""
    name = raw["name"]
    meta = raw.get("_meta", {})

    return ToolDefinition(
        name=_name_to_mcp_tool_name(name),
        cli_command=name,
        description=raw.get("description", ""),
        input_schema=_clean_input_schema(raw.get("inputSchema", {})),
        output_schema=raw.get("outputSchema"),
        risk_level=_classify_risk(meta),
        required_identity=_classify_identity(meta),
        scopes=meta.get("scopes", []),
        doc_url=meta.get("doc_url"),
        danger=meta.get("danger", False),
    )


def discover_tools(
    *,
    settings: BridgeSettings | None = None,
    cache_path: Path | None = None,
) -> list[ToolDefinition]:
    """发现所有可注册的 tool 定义。

    优先从缓存加载，缓存不存在或 no_cache=True 时调用 lark-cli schema。

    Args:
        settings: 可选配置覆盖
        cache_path: 可选缓存文件路径覆盖

    Returns:
        ToolDefinition 列表

    Raises:
        DiscoveryError: lark-cli schema 命令失败时
    """
    if settings is None:
        settings = get_settings()

    # 确定缓存路径
    if cache_path is None:
        cache_dir = Path(settings.cache_dir)
        cache_path = cache_dir / "schema_cache.json"

    # 尝试从缓存加载
    if not settings.no_cache and cache_path.exists():
        try:
            raw_data = json.loads(cache_path.read_text(encoding="utf-8"))
            return [_parse_tool(t) for t in raw_data]
        except (json.JSONDecodeError, KeyError):
            pass  # 缓存损坏，重新发现

    # 调用 lark-cli schema
    try:
        result = subprocess.run(
            [settings.cli_path, "schema", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,  # schema 可能较慢
        )
    except FileNotFoundError:
        raise DiscoveryError(
            f"lark-cli 未找到（路径: {settings.cli_path}）",
            error_code="E_CLI_NOT_FOUND",
        )
    except subprocess.TimeoutExpired:
        raise DiscoveryError(
            "lark-cli schema 命令超时",
            error_code="E_TIMEOUT",
        )

    if result.returncode != 0:
        raise DiscoveryError(
            f"lark-cli schema 失败: {result.stderr.strip()}",
            error_code="E_CLI_ERROR",
        )

    # 解析 JSON
    try:
        raw_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise DiscoveryError(
            f"lark-cli schema 输出不是有效 JSON: {e}",
            error_code="E_CLI_ERROR",
        )

    if not isinstance(raw_data, list):
        raise DiscoveryError(
            "lark-cli schema 输出格式异常（期望数组）",
            error_code="E_CLI_ERROR",
        )

    # 写入缓存
    if not settings.no_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(raw_data, ensure_ascii=False),
            encoding="utf-8",
        )

    # 解析所有 tool
    tools = []
    for raw in raw_data:
        try:
            tools.append(_parse_tool(raw))
        except (KeyError, TypeError):
            continue  # 跳过格式异常的条目

    return tools


def get_tools_by_domain(tools: list[ToolDefinition]) -> dict[str, list[ToolDefinition]]:
    """按域分组 tool 列表。"""
    domains: dict[str, list[ToolDefinition]] = {}
    for tool in tools:
        # 从 name "lark.domain.action" 提取 domain
        parts = tool.name.split(".")
        domain = parts[1] if len(parts) >= 3 else "unknown"
        domains.setdefault(domain, []).append(tool)
    return domains
