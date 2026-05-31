"""子进程执行器：调用 lark-cli 并处理结果。"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from lark_mcp_bridge.config import BridgeSettings, get_settings
from lark_mcp_bridge.errors import ExecutionError


@dataclass
class ExecutionResult:
    """单次 tool call 的执行结果。"""

    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    recovery_hint: str | None = None
    duration_ms: int = 0


# lark-cli stderr 关键词 → 结构化错误码映射
_ERROR_PATTERNS: list[tuple[str, str, str]] = [
    # (stderr 关键词, error_code, recovery_hint)
    ("token expired", "E_AUTH_EXPIRED", "请运行 `lark-cli auth login` 重新认证"),
    ("401", "E_AUTH_EXPIRED", "请运行 `lark-cli auth login` 重新认证"),
    ("not logged in", "E_AUTH_NO_LOGIN", "请先执行 `lark-cli auth login --recommend`"),
    ("no login", "E_AUTH_NO_LOGIN", "请先执行 `lark-cli auth login --recommend`"),
    ("429", "E_RATE_LIMITED", "飞书 API 限流，请稍后重试"),
    ("rate limit", "E_RATE_LIMITED", "飞书 API 限流，请稍后重试"),
    ("not found", "E_NOT_FOUND", "未找到指定资源，请检查 ID 是否正确"),
    ("404", "E_NOT_FOUND", "未找到指定资源，请检查 ID 是否正确"),
    ("permission denied", "E_PERMISSION_DENIED", "当前身份无权执行此操作"),
    ("403", "E_PERMISSION_DENIED", "当前身份无权执行此操作"),
]


def _classify_error(stderr: str, returncode: int) -> tuple[str, str]:
    """根据 stderr 内容和 exit code 分类错误。"""
    stderr_lower = stderr.lower()
    for pattern, code, hint in _ERROR_PATTERNS:
        if pattern in stderr_lower:
            return code, hint
    return "E_CLI_ERROR", "lark-cli 内部错误，请检查版本是否最新"


def check_cli_available(settings: BridgeSettings | None = None) -> None:
    """检查 lark-cli 是否可用。启动时调用，不可用则抛异常。"""
    if settings is None:
        settings = get_settings()
    try:
        result = subprocess.run(
            [settings.cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise ExecutionError(
                f"lark-cli 返回错误: {result.stderr.strip()}",
                error_code="E_CLI_NOT_FOUND",
            )
    except FileNotFoundError:
        raise ExecutionError(
            f"lark-cli 未找到（路径: {settings.cli_path}）。"
            "请确认已安装: npx @larksuite/cli@latest install",
            error_code="E_CLI_NOT_FOUND",
        )
    except subprocess.TimeoutExpired:
        raise ExecutionError(
            "lark-cli --version 超时，可能安装异常",
            error_code="E_CLI_NOT_FOUND",
        )


def execute(
    command: list[str],
    *,
    settings: BridgeSettings | None = None,
) -> ExecutionResult:
    """执行 lark-cli 命令并返回结构化结果。

    Args:
        command: lark-cli 子命令及参数列表，如 ["calendar", "+agenda", "--format", "json"]
        settings: 可选配置覆盖

    Returns:
        ExecutionResult，success=True 时 data 包含解析后的 JSON。
    """
    if settings is None:
        settings = get_settings()

    full_command = [settings.cli_path] + command

    start = time.perf_counter_ns()
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=settings.timeout,
        )
    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter_ns() - start) // 1_000_000
        return ExecutionResult(
            success=False,
            error_code="E_TIMEOUT",
            error_message=f"命令执行超时（{settings.timeout}s）",
            recovery_hint="命令执行超时，可能是网络问题，请重试",
            duration_ms=duration_ms,
        )
    except FileNotFoundError:
        duration_ms = (time.perf_counter_ns() - start) // 1_000_000
        return ExecutionResult(
            success=False,
            error_code="E_CLI_NOT_FOUND",
            error_message=f"lark-cli 未找到（路径: {settings.cli_path}）",
            recovery_hint="lark-cli 未安装或不在 PATH 中",
            duration_ms=duration_ms,
        )

    duration_ms = (time.perf_counter_ns() - start) // 1_000_000

    # exit code 10 = 高风险操作需要确认
    if result.returncode == 10:
        return ExecutionResult(
            success=False,
            error_code="E_DESTRUCTIVE_CONFIRM",
            error_message="此操作为高风险操作，需要确认",
            recovery_hint="请确认后使用 --yes 参数重试",
            duration_ms=duration_ms,
        )

    if result.returncode != 0:
        error_code, recovery_hint = _classify_error(result.stderr, result.returncode)
        return ExecutionResult(
            success=False,
            error_code=error_code,
            error_message=result.stderr.strip() or f"命令失败（exit code: {result.returncode}）",
            recovery_hint=recovery_hint,
            duration_ms=duration_ms,
        )

    # 成功：尝试解析 JSON
    stdout = result.stdout.strip()
    if not stdout:
        return ExecutionResult(success=True, data={}, duration_ms=duration_ms)

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # 非 JSON 输出，作为纯文本返回
        data = {"_raw": stdout}

    # 检查业务层错误：lark-cli 可能 exit 0 但返回 {"ok": false, "error": {...}}
    if isinstance(data, dict) and data.get("ok") is False:
        error_info = data.get("error", {})
        error_msg = error_info.get("message", data.get("msg", "业务层错误"))
        error_code_val = error_info.get("code", data.get("code", ""))
        return ExecutionResult(
            success=False,
            data=data,
            error_code="E_BUSINESS_ERROR",
            error_message=f"飞书 API 返回错误: {error_msg} (code: {error_code_val})",
            recovery_hint="请检查参数是否正确，或确认资源是否存在",
            duration_ms=duration_ms,
        )

    return ExecutionResult(success=True, data=data, duration_ms=duration_ms)
