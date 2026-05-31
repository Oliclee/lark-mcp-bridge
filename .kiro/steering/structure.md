# 项目结构

```
lark-mcp-bridge/
├── pyproject.toml                  # 包元数据、依赖、构建配置
├── README.md
├── lark-mcp-bridge.toml            # 运行时配置（安全白名单等）
├── src/lark_mcp_bridge/            # 主包（src 布局）
│   ├── __init__.py
│   ├── server.py                   # FastMCP 入口，注册所有 primitives
│   ├── discovery.py                # 解析 lark-cli 元数据 → ToolDefinition 列表
│   ├── composite.py                # 手工编写的多步工作流 tool
│   ├── executor.py                 # subprocess.run() 封装，超时，错误映射
│   ├── filters.py                  # 白名单/黑名单命令过滤
│   ├── cache.py                    # Discovery + 热数据缓存（TTL）
│   ├── resources.py                # MCP Resources（identity、permissions、domains）
│   ├── config.py                   # 统一配置（pydantic-settings）
│   ├── audit.py                    # 结构化审计日志
│   ├── prompts.py                  # Prompt 注册入口
│   └── prompts/                    # 领域 Prompt 文件（带 frontmatter 的 markdown）
│       ├── __init__.py
│       ├── _base.py                # Prompt 基类/格式工具
│       ├── calendar.md
│       ├── im.md
│       ├── base.md
│       ├── contact.md
│       └── scenarios/              # 跨域场景 Prompt
│           ├── meeting-scheduling.md
│           └── task-delegation.md
├── tests/
│   ├── conftest.py                 # 共享 fixture、mock_executor
│   ├── test_executor.py
│   ├── test_filters.py
│   ├── test_composite.py
│   └── fixtures/                   # 预录制的 lark-cli 输出
│       ├── schema/                 # Discovery 元数据 JSON
│       ├── calls/                  # Tool call 响应 JSON
│       └── help/                   # CLI help 文本
├── scripts/
│   ├── sync_prompts.py             # 从 lark-cli SKILL.md 同步 Prompt
│   └── record_fixtures.sh          # 从真实 CLI 录制测试 fixture
└── docs/                           # 设计与参考文档
    ├── INDEX.md                    # 文档导航
    ├── PROJECT_DESIGN.md           # 架构（权威来源）
    ├── API_SPEC.md                 # MCP tool schema 与错误码
    ├── SECURITY.md                 # 安全模型与过滤策略
    ├── DEPLOYMENT.md               # 安装与配置指南
    ├── TESTING.md                  # 测试策略与 Mock 方案
    ├── PROMPTS_GUIDE.md            # Prompt 编写规范
    ├── OBSERVABILITY.md            # 指标、健康检查、日志
    ├── ROADMAP.md                  # 里程碑与进度
    └── CHANGELOG.md                # 版本变更记录
```

## 模块职责

| 模块 | 单一职责 |
|------|----------|
| `server.py` | FastMCP 生命周期、CORS、注册 tools/prompts/resources |
| `discovery.py` | 解析 CLI 元数据 → `list[ToolDefinition]` |
| `composite.py` | 多步工作流 tool（内部编排） |
| `executor.py` | 运行子进程，处理 exit code，映射为 `ExecutionResult` |
| `filters.py` | 安全门：`is_allowed(tool_name) → bool` |
| `cache.py` | Discovery 结果和热数据的 TTL 缓存 |
| `resources.py` | 暴露只读上下文（identity、permissions、domains） |
| `config.py` | 加载和校验所有配置 |
| `audit.py` | 结构化审计事件记录 |
| `prompts.py` | 从 markdown 文件加载并注册 MCP prompts |

## 命名规范

| 场景 | 格式 | 示例 |
|------|------|------|
| 项目/仓库名 | kebab-case | `lark-mcp-bridge` |
| Python 包/import | snake_case | `lark_mcp_bridge` |
| MCP tool 名 | `lark.<domain>.<action>` | `lark.calendar.agenda` |
| 配置环境变量 | `LARK_MCP_` 前缀，UPPER_SNAKE | `LARK_MCP_TIMEOUT` |
| 错误码 | `E_` 前缀，UPPER_SNAKE | `E_AUTH_EXPIRED` |

## 错误层级

```
BridgeError
├── DiscoveryError
├── ExecutionError
├── FilterError
└── ConfigError
```

`executor.py` 返回 `ExecutionResult`（tool call 失败时不抛异常）。仅不可恢复的启动错误才抛异常阻止启动。
