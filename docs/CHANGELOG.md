# CHANGELOG

## [0.1.0] - 2026-05-31

### Phase 0-2 完成

#### Added
- 项目骨架：pyproject.toml、src layout、pytest 配置、console script entry point
- `config.py`：pydantic-settings 统一配置（环境变量 / .env / toml）
- `errors.py`：BridgeError 错误层级
- `executor.py`：subprocess 执行器 + 超时 + 错误分类 + 业务层 ok:false 检测
- `filters.py`：白名单/黑名单过滤 + 风险分级（16 个域）
- `server.py`：FastMCP stdio server
- 5 个固定 tool：im.messages-send、calendar.agenda、base.record-search、docs.fetch、contact.search-user
- `composite.py`：schedule-meeting 复合 tool（查空闲 → 找会议室 → 创建日程）
- `prompts/calendar.md`：日历域工作流 Prompt
- `discovery.py`：解析 lark-cli schema（219 个 ToolDefinition）+ 缓存
- `lark.discover` meta-tool：按域查询可用操作（渐进式暴露）
- `resources.py`：MCP Resources（identity / permissions / domains）
- Resources as Tools：`lark.identity`、`lark.permissions`、`lark.domains`（Quick 兼容）

#### Fixed
- `im.messages-send` 移除不支持的 `--format` flag
- Tool 命名从 `lark:domain:action` 改为 `lark.domain.action`（符合 MCP SEP-986）

#### Notes
- 已在 Amazon Quick Desktop 端到端验证通过
- 测试：83 个通过，覆盖率 86%
- lark-cli 最低版本要求：1.0.43
