"""discovery.py 单元测试。"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lark_mcp_bridge.config import BridgeSettings
from lark_mcp_bridge.discovery import (
    ToolDefinition,
    _classify_identity,
    _classify_risk,
    _name_to_mcp_tool_name,
    _parse_tool,
    discover_tools,
    get_tools_by_domain,
)
from lark_mcp_bridge.errors import DiscoveryError


class TestNameConversion:
    """_name_to_mcp_tool_name() 测试。"""

    def test_simple_two_parts(self):
        assert _name_to_mcp_tool_name("calendar events") == "lark.calendar.events"

    def test_three_parts(self):
        assert _name_to_mcp_tool_name("im messages create") == "lark.im.messages-create"

    def test_dotted_resource(self):
        assert _name_to_mcp_tool_name("im chat.members create") == "lark.im.chat-members-create"

    def test_approval(self):
        assert _name_to_mcp_tool_name("approval instances cancel") == "lark.approval.instances-cancel"

    def test_single_part(self):
        assert _name_to_mcp_tool_name("something") == "lark.something"


class TestClassifyRisk:
    """_classify_risk() 测试。"""

    def test_read(self):
        assert _classify_risk({"risk": "read"}) == "read"

    def test_write(self):
        assert _classify_risk({"risk": "write"}) == "write"

    def test_high_risk_write(self):
        assert _classify_risk({"risk": "high-risk-write"}) == "destructive"

    def test_danger_flag(self):
        assert _classify_risk({"risk": "write", "danger": True}) == "destructive"

    def test_empty_meta(self):
        assert _classify_risk({}) == "write"


class TestClassifyIdentity:
    """_classify_identity() 测试。"""

    def test_user_only(self):
        assert _classify_identity({"access_tokens": ["user"]}) == "user"

    def test_bot_only(self):
        assert _classify_identity({"access_tokens": ["bot"]}) == "bot"

    def test_both(self):
        assert _classify_identity({"access_tokens": ["bot", "user"]}) == "both"

    def test_empty(self):
        assert _classify_identity({}) == "both"


class TestParseTool:
    """_parse_tool() 测试。"""

    def test_full_tool(self):
        raw = {
            "name": "im messages create",
            "description": "发送消息",
            "inputSchema": {
                "type": "object",
                "required": ["data"],
                "properties": {
                    "data": {"type": "object"},
                    "yes": {"type": "boolean", "default": False},
                },
            },
            "outputSchema": {"type": "object"},
            "_meta": {
                "envelope_version": "1.0",
                "scopes": ["im:message"],
                "access_tokens": ["bot", "user"],
                "danger": False,
                "risk": "write",
                "doc_url": "https://example.com",
            },
        }
        tool = _parse_tool(raw)
        assert tool.name == "lark.im.messages-create"
        assert tool.cli_command == "im messages create"
        assert tool.description == "发送消息"
        assert tool.risk_level == "write"
        assert tool.required_identity == "both"
        assert "yes" not in tool.input_schema.get("properties", {})
        assert tool.doc_url == "https://example.com"

    def test_danger_tool(self):
        raw = {
            "name": "im chat.members delete",
            "description": "移除群成员",
            "inputSchema": {"type": "object", "properties": {"data": {}, "yes": {}}},
            "_meta": {"danger": True, "risk": "high-risk-write", "access_tokens": ["bot", "user"]},
        }
        tool = _parse_tool(raw)
        assert tool.risk_level == "destructive"
        assert tool.danger is True


class TestDiscoverTools:
    """discover_tools() 测试。"""

    @pytest.fixture
    def settings(self, tmp_path):
        return BridgeSettings(
            cli_path="lark-cli",
            cache_dir=str(tmp_path / "cache"),
            no_cache=True,
        )

    @pytest.fixture
    def sample_schema(self):
        return [
            {
                "name": "calendar events create",
                "description": "创建日程",
                "inputSchema": {"type": "object", "properties": {"data": {}}},
                "_meta": {"risk": "write", "access_tokens": ["user"], "scopes": ["calendar:event:create"]},
            },
            {
                "name": "im messages create",
                "description": "发送消息",
                "inputSchema": {"type": "object", "properties": {"data": {}}},
                "_meta": {"risk": "write", "access_tokens": ["bot", "user"], "scopes": ["im:message"]},
            },
        ]

    def test_discover_from_cli(self, settings, sample_schema):
        """从 lark-cli 发现 tool。"""
        with patch("lark_mcp_bridge.discovery.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(sample_schema),
                stderr="",
            )
            tools = discover_tools(settings=settings)

        assert len(tools) == 2
        assert tools[0].name == "lark.calendar.events-create"
        assert tools[1].name == "lark.im.messages-create"

    def test_discover_from_cache(self, tmp_path, sample_schema):
        """从缓存加载 tool。"""
        cache_path = tmp_path / "cache" / "schema_cache.json"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(json.dumps(sample_schema))

        settings = BridgeSettings(
            cli_path="lark-cli",
            cache_dir=str(tmp_path / "cache"),
            no_cache=False,
        )
        tools = discover_tools(settings=settings, cache_path=cache_path)
        assert len(tools) == 2

    def test_discover_cli_not_found(self, settings):
        """lark-cli 不存在。"""
        with patch("lark_mcp_bridge.discovery.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(DiscoveryError) as exc_info:
                discover_tools(settings=settings)
            assert exc_info.value.error_code == "E_CLI_NOT_FOUND"

    def test_discover_cli_error(self, settings):
        """lark-cli schema 返回错误。"""
        with patch("lark_mcp_bridge.discovery.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
            with pytest.raises(DiscoveryError) as exc_info:
                discover_tools(settings=settings)
            assert exc_info.value.error_code == "E_CLI_ERROR"

    def test_discover_writes_cache(self, tmp_path, sample_schema):
        """发现后写入缓存。"""
        cache_path = tmp_path / "cache" / "schema_cache.json"
        settings = BridgeSettings(
            cli_path="lark-cli",
            cache_dir=str(tmp_path / "cache"),
            no_cache=False,
        )
        with patch("lark_mcp_bridge.discovery.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(sample_schema),
                stderr="",
            )
            discover_tools(settings=settings, cache_path=cache_path)

        assert cache_path.exists()
        cached = json.loads(cache_path.read_text())
        assert len(cached) == 2

    def test_discover_empty_schema(self, settings):
        """schema 返回空列表。"""
        with patch("lark_mcp_bridge.discovery.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")
            tools = discover_tools(settings=settings)
        assert tools == []


class TestGetToolsByDomain:
    """get_tools_by_domain() 测试。"""

    def test_grouping(self):
        tools = [
            ToolDefinition(name="lark.im.send", cli_command="im send", description="", input_schema={}),
            ToolDefinition(name="lark.im.list", cli_command="im list", description="", input_schema={}),
            ToolDefinition(name="lark.calendar.create", cli_command="calendar create", description="", input_schema={}),
        ]
        grouped = get_tools_by_domain(tools)
        assert len(grouped["im"]) == 2
        assert len(grouped["calendar"]) == 1


class TestDiscoverWithRealFixture:
    """使用真实 fixture 文件测试。"""

    def test_parse_all_219_tools(self):
        """解析完整的 219 个 tool fixture。"""
        fixture_path = Path(__file__).parent / "fixtures" / "schema" / "all_tools.json"
        if not fixture_path.exists():
            pytest.skip("fixture 文件不存在")

        raw_data = json.loads(fixture_path.read_text())
        tools = []
        for raw in raw_data:
            try:
                tools.append(_parse_tool(raw))
            except (KeyError, TypeError):
                continue

        assert len(tools) == 219
        # 验证域分布
        domains = get_tools_by_domain(tools)
        assert "im" in domains
        assert "calendar" in domains
        assert "mail" in domains
