"""启动预检 + Banner + 结构化日志配置。"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from typing import Any

from lark_mcp_bridge import __version__
from lark_mcp_bridge.config import BridgeSettings, get_settings
from lark_mcp_bridge.errors import ExecutionError


class JsonFormatter(logging.Formatter):
    """JSON 格式日志 formatter。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(settings: BridgeSettings | None = None) -> None:
    """配置结构化日志，输出到 stderr。"""
    if settings is None:
        settings = get_settings()

    # 所有日志必须走 stderr（stdout 专用于 MCP 协议）
    handler = logging.StreamHandler(sys.stderr)

    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    # 配置根 logger
    root = logging.getLogger("lark_mcp_bridge")
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.handlers = [handler]


def print_banner(settings: BridgeSettings | None = None) -> None:
    """输出启动 Banner 到 stderr。"""
    if settings is None:
        settings = get_settings()

    lines = [
        f"lark-mcp-bridge v{__version__}",
        f"  transport: {settings.transport}",
        f"  cli_path:  {settings.cli_path}",
        f"  timeout:   {settings.timeout}s",
        f"  log_level: {settings.log_level}",
    ]
    if settings.audit_log:
        lines.append(f"  audit_log: {settings.audit_log}")

    for line in lines:
        print(line, file=sys.stderr)


def preflight_check(settings: BridgeSettings | None = None) -> dict[str, Any]:
    """启动预检：检查 lark-cli 安装和认证状态。

    Returns:
        预检结果字典，包含 cli_version、auth_status 等。
        不抛异常——降级启动时仍返回结果。
    """
    if settings is None:
        settings = get_settings()

    result: dict[str, Any] = {
        "cli_available": False,
        "cli_version": None,
        "auth_ready": False,
        "identity": None,
        "warnings": [],
    }

    logger = logging.getLogger("lark_mcp_bridge.startup")

    # 1. 检查 lark-cli 是否可用
    try:
        version_result = subprocess.run(
            [settings.cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if version_result.returncode == 0:
            result["cli_available"] = True
            result["cli_version"] = version_result.stdout.strip()
            logger.info(f"lark-cli: {result['cli_version']}")
        else:
            result["warnings"].append(f"lark-cli 返回错误: {version_result.stderr.strip()}")
            logger.warning(f"lark-cli 异常: {version_result.stderr.strip()}")
            return result
    except FileNotFoundError:
        result["warnings"].append(f"lark-cli 未找到（路径: {settings.cli_path}）")
        logger.error(f"lark-cli 未找到: {settings.cli_path}")
        return result
    except subprocess.TimeoutExpired:
        result["warnings"].append("lark-cli --version 超时")
        logger.error("lark-cli --version 超时")
        return result

    # 2. 检查认证状态
    try:
        auth_result = subprocess.run(
            [settings.cli_path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if auth_result.returncode == 0:
            auth_data = json.loads(auth_result.stdout)
            identities = auth_data.get("identities", {})

            # 检查是否有可用身份
            user_ready = identities.get("user", {}).get("available", False)
            bot_ready = identities.get("bot", {}).get("available", False)

            if user_ready or bot_ready:
                result["auth_ready"] = True
                result["identity"] = auth_data.get("identity", "unknown")
                logger.info(f"认证就绪: identity={result['identity']}")
            else:
                result["warnings"].append("无可用身份，请运行 lark-cli auth login")
                logger.warning("认证未就绪: 无可用身份")
        else:
            result["warnings"].append("auth status 失败")
            logger.warning("auth status 返回非零")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        result["warnings"].append(f"认证检查异常: {e}")
        logger.warning(f"认证检查异常: {e}")

    return result


def run_startup(settings: BridgeSettings | None = None) -> dict[str, Any]:
    """执行完整启动流程：日志配置 → Banner → 预检。"""
    if settings is None:
        settings = get_settings()

    setup_logging(settings)
    print_banner(settings)
    result = preflight_check(settings)

    logger = logging.getLogger("lark_mcp_bridge.startup")

    if result["warnings"]:
        for w in result["warnings"]:
            print(f"  ⚠️  {w}", file=sys.stderr)

    if not result["cli_available"]:
        print("  ❌ lark-cli 不可用，bridge 将无法执行任何操作", file=sys.stderr)
    elif not result["auth_ready"]:
        print("  ⚠️  认证未就绪，部分操作可能失败", file=sys.stderr)
    else:
        print("  ✅ 预检通过", file=sys.stderr)

    return result
