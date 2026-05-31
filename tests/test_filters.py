"""filters.py 单元测试。"""

import pytest

from lark_mcp_bridge.filters import FilterConfig, get_risk_level, is_allowed


@pytest.fixture
def default_config():
    """默认过滤配置（Phase 1 MVP）。"""
    return FilterConfig(
        default_policy="deny",
        whitelist_domains=["im", "calendar", "base", "docs", "contact"],
        blacklist_patterns=["delete", "remove", "destroy", "batch-delete", "purge"],
        blacklist_commands=["lark.admin.*"],
    )


class TestIsAllowed:
    """is_allowed() 测试。"""

    def test_whitelist_domain_allowed(self, default_config):
        """白名单域中的命令允许执行。"""
        assert is_allowed("lark.calendar.agenda", default_config) is True
        assert is_allowed("lark.im.messages-send", default_config) is True
        assert is_allowed("lark.base.record-search", default_config) is True
        assert is_allowed("lark.docs.fetch", default_config) is True
        assert is_allowed("lark.contact.search-user", default_config) is True

    def test_non_whitelist_domain_denied(self, default_config):
        """非白名单域的命令被拒绝。"""
        assert is_allowed("lark.admin.users-list", default_config) is False
        assert is_allowed("lark.approval.create", default_config) is False
        assert is_allowed("lark.wiki.get", default_config) is False

    def test_blacklist_pattern_overrides_whitelist(self, default_config):
        """黑名单模式优先于白名单。"""
        assert is_allowed("lark.im.messages-delete", default_config) is False
        assert is_allowed("lark.base.records-batch-delete", default_config) is False
        assert is_allowed("lark.docs.remove", default_config) is False
        assert is_allowed("lark.calendar.destroy", default_config) is False

    def test_blacklist_command_glob(self, default_config):
        """黑名单命令 glob 匹配。"""
        assert is_allowed("lark.admin.users-list", default_config) is False
        assert is_allowed("lark.admin.anything", default_config) is False

    def test_whitelist_commands_override(self):
        """白名单具体命令覆盖域级别。"""
        config = FilterConfig(
            default_policy="deny",
            whitelist_domains=[],
            whitelist_commands=["lark.drive.list", "lark.drive.download"],
            blacklist_patterns=["delete"],
            blacklist_commands=[],
        )
        assert is_allowed("lark.drive.list", config) is True
        assert is_allowed("lark.drive.download", config) is True
        assert is_allowed("lark.drive.upload", config) is False
        assert is_allowed("lark.drive.delete", config) is False  # 黑名单优先

    def test_default_policy_allow(self):
        """默认策略为 allow 时，未匹配的命令允许执行。"""
        config = FilterConfig(
            default_policy="allow",
            whitelist_domains=[],
            whitelist_commands=[],
            blacklist_patterns=["delete"],
            blacklist_commands=[],
        )
        assert is_allowed("lark.unknown.something", config) is True
        assert is_allowed("lark.unknown.delete", config) is False

    def test_invalid_tool_name(self, default_config):
        """无效 tool name 格式被拒绝。"""
        assert is_allowed("invalid-name", default_config) is False
        assert is_allowed("", default_config) is False


class TestGetRiskLevel:
    """get_risk_level() 测试。"""

    def test_read_operations(self):
        """读操作识别。"""
        assert get_risk_level("lark.calendar.agenda") == "read"
        assert get_risk_level("lark.docs.fetch") == "read"
        assert get_risk_level("lark.contact.search-user") == "read"
        assert get_risk_level("lark.drive.list") == "read"
        assert get_risk_level("lark.im.query") == "read"

    def test_destructive_operations(self):
        """破坏性操作识别。"""
        assert get_risk_level("lark.drive.delete") == "destructive"
        assert get_risk_level("lark.base.records-batch-delete") == "destructive"
        assert get_risk_level("lark.docs.remove") == "destructive"

    def test_write_operations(self):
        """写操作（默认）。"""
        assert get_risk_level("lark.im.messages-send") == "write"
        assert get_risk_level("lark.calendar.create") == "write"
        assert get_risk_level("lark.task.update") == "write"
