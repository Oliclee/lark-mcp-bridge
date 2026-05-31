"""统一配置模型：支持环境变量 / .env / toml 三级覆盖。"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeSettings(BaseSettings):
    """lark-mcp-bridge 运行时配置。"""

    model_config = SettingsConfigDict(
        env_prefix="LARK_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 网络
    host: str = "127.0.0.1"
    port: int = 8080
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"

    # lark-cli
    cli_path: str = "lark-cli"
    timeout: int = 30

    # 进程池
    pool_size: int = 0  # 0 = 禁用，使用 subprocess.run

    # 日志
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    log_file: str | None = None

    # 缓存
    cache_dir: str = str(Path.home() / ".cache" / "lark-mcp-bridge")
    no_cache: bool = False

    # 审计
    audit_log: str | None = None
    audit_level: Literal["read", "write", "all"] = "write"


def get_settings() -> BridgeSettings:
    """获取全局配置实例。"""
    return BridgeSettings()
