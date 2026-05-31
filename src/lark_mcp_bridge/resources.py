"""MCP Resources 层：暴露只读上下文信息。"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from lark_mcp_bridge.config import BridgeSettings, get_settings


def get_identity(settings: BridgeSettings | None = None) -> dict[str, Any]:
    """获取当前登录身份信息。"""
    if settings is None:
        settings = get_settings()

    try:
        result = subprocess.run(
            [settings.cli_path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"error": "无法获取身份信息", "status": "unavailable"}

    if result.returncode != 0:
        return {"error": "auth status 失败", "status": "unavailable"}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "auth status 输出解析失败", "status": "unavailable"}

    # 提取关键信息
    identities = data.get("identities", {})
    user_info = identities.get("user", {})
    bot_info = identities.get("bot", {})

    identity: dict[str, Any] = {
        "app_id": data.get("appId", ""),
        "brand": data.get("brand", ""),
        "default_as": data.get("defaultAs", ""),
        "current_identity": data.get("identity", ""),
    }

    if user_info:
        identity["user"] = {
            "status": user_info.get("status", ""),
            "available": user_info.get("available", False),
            "name": user_info.get("userName", ""),
            "open_id": user_info.get("openId", ""),
        }

    if bot_info:
        identity["bot"] = {
            "status": bot_info.get("status", ""),
            "available": bot_info.get("available", False),
        }

    return identity


def get_permissions(settings: BridgeSettings | None = None) -> dict[str, Any]:
    """获取当前已授权的 scope 列表。"""
    if settings is None:
        settings = get_settings()

    try:
        result = subprocess.run(
            [settings.cli_path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"scopes": [], "error": "无法获取权限信息"}

    if result.returncode != 0:
        return {"scopes": [], "error": "auth status 失败"}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"scopes": [], "error": "解析失败"}

    # scope 在 user identity 的 scope 字段中
    user_info = data.get("identities", {}).get("user", {})
    scope_str = user_info.get("scope", "")
    scopes = scope_str.split() if scope_str else []

    return {"scopes": scopes, "total": len(scopes)}


def get_domains_summary(settings: BridgeSettings | None = None) -> dict[str, Any]:
    """获取已发现的域概览。"""
    try:
        from lark_mcp_bridge.discovery import discover_tools, get_tools_by_domain
        tools = discover_tools(settings=settings)
        domains = get_tools_by_domain(tools)
        return {
            "domains": [
                {"name": name, "tool_count": len(tools_list)}
                for name, tools_list in sorted(domains.items())
            ],
            "total_tools": len(tools),
            "total_domains": len(domains),
        }
    except Exception as e:
        return {"domains": [], "error": str(e)}
