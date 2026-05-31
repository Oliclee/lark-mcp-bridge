"""config.py 单元测试。"""

import os
from unittest.mock import patch

import pytest

from lark_mcp_bridge.config import BridgeSettings, get_settings


class TestBridgeSettings:
    """BridgeSettings 配置模型测试。"""

    def test_defaults(self):
        """默认值正确。"""
        settings = BridgeSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 8080
        assert settings.transport == "stdio"
        assert settings.cli_path == "lark-cli"
        assert settings.timeout == 30
        assert settings.pool_size == 0
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.no_cache is False
        assert settings.audit_log is None
        assert settings.audit_level == "write"

    def test_env_override(self):
        """环境变量覆盖默认值。"""
        env = {
            "LARK_MCP_HOST": "0.0.0.0",
            "LARK_MCP_PORT": "9090",
            "LARK_MCP_TIMEOUT": "60",
            "LARK_MCP_LOG_LEVEL": "DEBUG",
            "LARK_MCP_NO_CACHE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = BridgeSettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9090
        assert settings.timeout == 60
        assert settings.log_level == "DEBUG"
        assert settings.no_cache is True

    def test_cli_path_override(self):
        """自定义 lark-cli 路径。"""
        with patch.dict(os.environ, {"LARK_MCP_CLI_PATH": "/usr/local/bin/lark-cli"}):
            settings = BridgeSettings()
        assert settings.cli_path == "/usr/local/bin/lark-cli"

    def test_get_settings(self):
        """get_settings() 返回有效实例。"""
        settings = get_settings()
        assert isinstance(settings, BridgeSettings)
