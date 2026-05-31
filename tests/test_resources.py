"""resources.py 单元测试。"""

import json
from unittest.mock import Mock, patch

import pytest

from lark_mcp_bridge.config import BridgeSettings
from lark_mcp_bridge.resources import get_domains_summary, get_identity, get_permissions


@pytest.fixture
def settings():
    return BridgeSettings(cli_path="lark-cli")


class TestGetIdentity:
    """get_identity() 测试。"""

    def test_normal_identity(self, settings):
        """正常返回身份信息。"""
        auth_output = json.dumps({
            "appId": "cli_abc123",
            "brand": "feishu",
            "defaultAs": "auto",
            "identity": "user",
            "identities": {
                "user": {
                    "status": "ready",
                    "available": True,
                    "userName": "Olic",
                    "openId": "ou_xxx",
                    "scope": "im:message calendar:event",
                },
                "bot": {
                    "status": "ready",
                    "available": True,
                },
            },
        })
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=auth_output, stderr="")
            result = get_identity(settings)

        assert result["app_id"] == "cli_abc123"
        assert result["brand"] == "feishu"
        assert result["current_identity"] == "user"
        assert result["user"]["name"] == "Olic"
        assert result["user"]["open_id"] == "ou_xxx"
        assert result["bot"]["available"] is True

    def test_cli_not_found(self, settings):
        """lark-cli 不存在。"""
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = get_identity(settings)

        assert result["status"] == "unavailable"

    def test_cli_error(self, settings):
        """auth status 返回错误。"""
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
            result = get_identity(settings)

        assert result["status"] == "unavailable"


class TestGetPermissions:
    """get_permissions() 测试。"""

    def test_normal_permissions(self, settings):
        """正常返回 scope 列表。"""
        auth_output = json.dumps({
            "identities": {
                "user": {
                    "scope": "im:message calendar:event:create contact:user.base:readonly",
                },
            },
        })
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=auth_output, stderr="")
            result = get_permissions(settings)

        assert result["total"] == 3
        assert "im:message" in result["scopes"]
        assert "calendar:event:create" in result["scopes"]

    def test_no_scopes(self, settings):
        """无 scope。"""
        auth_output = json.dumps({"identities": {"user": {}}})
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=auth_output, stderr="")
            result = get_permissions(settings)

        assert result["scopes"] == []
        assert result["total"] == 0


class TestGetDomainsSummary:
    """get_domains_summary() 测试。"""

    def test_normal_summary(self, settings):
        """正常返回域概览。"""
        sample_schema = [
            {"name": "im messages create", "description": "", "inputSchema": {}, "_meta": {}},
            {"name": "im chats get", "description": "", "inputSchema": {}, "_meta": {}},
            {"name": "calendar events create", "description": "", "inputSchema": {}, "_meta": {}},
        ]
        with patch("lark_mcp_bridge.resources.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(sample_schema),
                stderr="",
            )
            result = get_domains_summary(
                BridgeSettings(cli_path="lark-cli", no_cache=True, cache_dir="/tmp/test_cache_res")
            )

        assert result["total_tools"] == 3
        assert result["total_domains"] == 2
        domains_dict = {d["name"]: d["tool_count"] for d in result["domains"]}
        assert domains_dict["im"] == 2
        assert domains_dict["calendar"] == 1
