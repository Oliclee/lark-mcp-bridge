"""命令过滤：白名单优先策略。

优先级：黑名单 > 白名单 > 默认策略（deny）

Tool 命名规范：lark.<domain>.<action>
（MCP 规范仅允许 A-Z a-z 0-9 _ - .，不允许 :）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class FilterConfig:
    """过滤策略配置。"""

    default_policy: Literal["deny", "allow"] = "deny"
    whitelist_domains: list[str] = field(default_factory=list)
    whitelist_commands: list[str] = field(default_factory=list)
    blacklist_patterns: list[str] = field(
        default_factory=lambda: ["delete", "remove", "destroy", "batch-delete", "purge"]
    )
    blacklist_commands: list[str] = field(default_factory=lambda: ["lark.admin.*"])


# Phase 1 默认配置：允许常用域
_DEFAULT_CONFIG = FilterConfig(
    default_policy="deny",
    whitelist_domains=[
        "im", "calendar", "base", "docs", "contact",
        "task", "drive", "wiki", "sheets", "approval",
        "mail", "okr", "vc", "attendance", "minutes", "slides",
    ],
    blacklist_patterns=["delete", "remove", "destroy", "batch-delete", "purge"],
    blacklist_commands=["lark.admin.*"],
)


def _parse_tool_name(tool_name: str) -> tuple[str, str]:
    """解析 tool name 为 (domain, action)。

    tool_name 格式: lark.<domain>.<action>
    """
    parts = tool_name.split(".")
    if len(parts) != 3 or parts[0] != "lark":
        return ("", tool_name)
    return (parts[1], parts[2])


def _matches_glob(pattern: str, value: str) -> bool:
    """简单 glob 匹配（仅支持末尾 *）。"""
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def is_allowed(tool_name: str, config: FilterConfig | None = None) -> bool:
    """检查命令是否通过安全策略。

    Args:
        tool_name: MCP tool 名称，如 "lark.calendar.agenda"
        config: 可选配置覆盖，默认使用内置配置

    Returns:
        True 表示允许执行，False 表示拒绝。
    """
    if config is None:
        config = _DEFAULT_CONFIG

    domain, action = _parse_tool_name(tool_name)

    # 1. 黑名单检查（最高优先级）
    for pattern in config.blacklist_patterns:
        if pattern in action:
            return False

    for cmd_pattern in config.blacklist_commands:
        if _matches_glob(cmd_pattern, tool_name):
            return False

    # 2. 白名单检查
    if tool_name in config.whitelist_commands:
        return True

    if domain in config.whitelist_domains:
        return True

    # 3. 默认策略
    return config.default_policy == "allow"


def get_risk_level(tool_name: str) -> Literal["read", "write", "destructive"]:
    """根据 tool name 推断风险级别。

    启发式规则：
    - action 以常见读取词开头 → read
    - action 含 delete/remove/destroy → destructive
    - 其他 → write（保守策略）
    """
    _, action = _parse_tool_name(tool_name)

    # 读操作关键词
    read_keywords = ["get", "list", "search", "agenda", "query", "info", "status", "fetch"]
    for kw in read_keywords:
        if action.startswith(kw) or action == kw:
            return "read"

    # 破坏性操作关键词
    destructive_keywords = ["delete", "remove", "destroy", "purge", "batch-delete"]
    for kw in destructive_keywords:
        if kw in action:
            return "destructive"

    # 默认为写操作
    return "write"
