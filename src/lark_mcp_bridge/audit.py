"""审计日志：记录 tool 调用、拦截、错误等事件。"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Literal

from lark_mcp_bridge.config import BridgeSettings, get_settings

# 需要脱敏的字段模式
_SENSITIVE_ID_FIELDS = {"chat_id", "chatId", "user_id", "userId", "open_id", "openId"}
_SENSITIVE_CONTENT_FIELDS = {"text", "content", "markdown", "description"}


def _mask_id(value: str) -> str:
    """ID 脱敏：保留前 3 位 + 后 3 位。"""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def _summarize_params(params: dict[str, Any], risk_level: str) -> dict[str, Any]:
    """参数摘要：根据风险级别决定脱敏策略。

    - write/destructive 操作：参数完整记录（便于审计）
    - read 操作：ID 脱敏，内容字段只记录长度
    """
    if risk_level in ("write", "destructive"):
        return params

    summary: dict[str, Any] = {}
    for key, value in params.items():
        if key in _SENSITIVE_ID_FIELDS and isinstance(value, str):
            summary[key] = _mask_id(value)
        elif key in _SENSITIVE_CONTENT_FIELDS and isinstance(value, str):
            summary[key] = f"<{len(value)} chars>"
        else:
            summary[key] = value
    return summary


class AuditLogger:
    """审计日志记录器。"""

    def __init__(self, settings: BridgeSettings | None = None):
        if settings is None:
            settings = get_settings()

        self._enabled = bool(settings.audit_log)
        self._level = settings.audit_level
        self._log_path: Path | None = Path(settings.audit_log) if settings.audit_log else None
        self._tz = timezone(timedelta(hours=8))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _should_log(self, risk_level: str) -> bool:
        """根据审计级别判断是否记录。"""
        if not self._enabled:
            return False
        if self._level == "all":
            return True
        if self._level == "write":
            return risk_level in ("write", "destructive")
        if self._level == "read":
            return risk_level == "read"
        return False

    def _write(self, event: dict[str, Any]) -> None:
        """写入审计日志。"""
        if not self._log_path:
            return

        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _now(self) -> str:
        return datetime.now(self._tz).isoformat()

    def log_tool_call(
        self,
        tool_name: str,
        risk_level: str,
        params: dict[str, Any],
    ) -> None:
        """记录 tool 调用事件。"""
        if not self._should_log(risk_level):
            return

        event = {
            "ts": self._now(),
            "event": "TOOL_CALL",
            "tool": tool_name,
            "risk_level": risk_level,
            "params_summary": _summarize_params(params, risk_level),
        }
        self._write(event)

    def log_tool_result(
        self,
        tool_name: str,
        risk_level: str,
        success: bool,
        duration_ms: int,
        error_code: str | None = None,
    ) -> None:
        """记录 tool 执行结果。"""
        if not self._should_log(risk_level):
            return

        event: dict[str, Any] = {
            "ts": self._now(),
            "event": "TOOL_RESULT",
            "tool": tool_name,
            "risk_level": risk_level,
            "success": success,
            "duration_ms": duration_ms,
        }
        if error_code:
            event["error_code"] = error_code
        self._write(event)

    def log_tool_blocked(
        self,
        tool_name: str,
        reason: str,
    ) -> None:
        """记录 tool 被拦截事件（始终记录，不受 level 限制）。"""
        if not self._enabled:
            return

        event = {
            "ts": self._now(),
            "event": "TOOL_BLOCKED",
            "tool": tool_name,
            "reason": reason,
        }
        self._write(event)

    def log_auth_error(
        self,
        error_type: str,
    ) -> None:
        """记录认证错误（始终记录）。"""
        if not self._enabled:
            return

        event = {
            "ts": self._now(),
            "event": "AUTH_ERROR",
            "error_type": error_type,
        }
        self._write(event)


# 全局实例（延迟初始化）
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志实例。"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
