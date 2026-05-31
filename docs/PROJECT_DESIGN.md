# PROJECT DESIGN: lark-mcp-bridge

> 文档索引见 [INDEX.md](./INDEX.md)

飞书 CLI → MCP Bridge

---

## 1. 背景与动机

### 1.1 问题

Amazon Quick 需要连接飞书生态（消息、文档、多维表格、日历等），但其 MCP 集成仅支持远程 HTTP MCP server，不支持本地 stdio 或 skill 执行器。

### 1.2 既有方案

| 方案 | 问题 |
|---|---|
| `larksuite/lark-openapi-mcp` | 已停更 10 个月，v0.5.1，仅裸 API 封装 |
| `larksuite/cli` (lark-cli) | 飞书官方主力，日更，13k stars，但本身是 CLI 工具，不是 MCP server |

### 1.3 方案选择

编写 Python MCP bridge，启动 lark-cli 子进程，将 CLI 命令封装为 MCP tools，供 Amazon Quick 通过 HTTP MCP 协议调用。

### 1.4 部署模式

**当前版本：Local stdio 模式（仅支持 Amazon Quick Desktop）**

```
Amazon Quick Desktop → Local MCP (stdio) → python -m lark_mcp_bridge.server → lark-cli
```

用户配置：Settings → Capabilities → MCP → Add Local
- Command: `python`
- Arguments: `-m lark_mcp_bridge.server`

**后续扩展（Phase 4）：Remote HTTP 模式**

```
Amazon Quick → HTTP MCP Bridge → subprocess → lark-cli
```

选择 Local stdio 的理由：
- 无需部署 HTTP 服务，无需 Docker
- Quick Desktop 自动管理进程生命周期
- 本地资源占用最小
- 用户体验最简单

详见 [EVALUATION §3.5](./EVALUATION.md#35-接入端分析amazon-quick-集成方式)

### 1.5 stdio Transport 协议细节

Local stdio 模式下，bridge 遵循 MCP stdio transport 规范：

- **通信**：Quick 通过 stdin 发送 JSON-RPC 消息，bridge 通过 stdout 返回响应
- **日志/调试输出**：必须走 stderr，**严禁污染 stdout**（否则 MCP 协议解析失败）
- **消息分隔**：每条 JSON-RPC 消息以 `\n` 结尾（NDJSON 格式）
- **启动信号**：bridge 启动后通过 stdout 发送 MCP `initialize` 响应，表明就绪
- **关闭信号**：Quick 发送 SIGTERM 时，bridge 需 graceful shutdown（完成进行中的 tool call，不超过 5s）
- **stderr 用途**：日志输出（受 `LARK_MCP_LOG_LEVEL` 控制）、启动 banner、调试信息

> 注：FastMCP 库原生支持 stdio transport，以上大部分由框架处理，bridge 仅需确保自身日志不走 stdout。

---

## 2. 架构设计

### 2.1 总体架构

```
┌──────────────────────────────────────────────────────────┐
│                    Amazon Quick                           │
│                (MCP client, HTTP mode)                    │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP streaming
                        ▼
┌──────────────────────────────────────────────────────────┐
│                    lark-mcp-bridge                        │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    server.py                         │ │
│  │         FastMCP: tools + prompts + resources         │ │
│  └──┬──────────────┬──────────────┬────────────────────┘ │
│     │              │              │                       │
│     ▼              ▼              ▼                       │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐                  │
│  │prompts  │ │discovery │ │composite  │                  │
│  │.py      │ │.py       │ │.py        │                  │
│  │ domain  │ │ schema   │ │ hand-     │                  │
│  │ know-   │ │ → atomic │ │ crafted   │                  │
│  │ ledge   │ │ tools    │ │ workflows │                  │
│  └─────────┘ └────┬─────┘ └─────┬─────┘                  │
│                   │              │                        │
│                   ▼              ▼                        │
│              ┌────────────────────────┐                   │
│              │     executor.py        │                   │
│              │  subprocess.run(cli)   │                   │
│              └───────────┬────────────┘                   │
│                          │                                │
│              ┌───────────┴────────────┐                   │
│              │     filters.py         │                   │
│              │  whitelist / blacklist │                   │
│              └────────────────────────┘                   │
└──────────────────────────────┬───────────────────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │    lark-cli     │
                      │  (subprocess)   │
                      └────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 |
|---|---|
| `server.py` | FastMCP HTTP streaming 入口，CORS 配置，生命周期管理，注册 MCP primitives（tools / prompts / resources） |
| `discovery.py` | 调用 `lark-cli schema --format json`，解析 JSON 数组，动态生成原子 tool schema。内置缓存逻辑（优先从本地 JSON 缓存加载） |
| `composite.py` | 手工维护的复合 tool（封装多步骤工作流，如预约会议的全流程） |
| `prompts.py` | 领域知识 Prompt 定义（本地维护，参见 [PROMPTS_GUIDE](./PROMPTS_GUIDE.md)） |
| `executor.py` | 构造子进程调用 `lark-cli <command> --format json`，处理 exit code、stdout/stderr |
| `filters.py` | 命令过滤（白名单优先策略），详见 [SECURITY](./SECURITY.md) |
| `cache.py` | 热门数据短期缓存（TTL），减少重复子进程调用（Discovery 缓存已内置于 discovery.py） |
| `resources.py` | MCP Resources 层：暴露用户身份、权限范围、可用域等上下文信息 |
| `config.py` | 统一配置模型（pydantic-settings），支持环境变量 / .env 覆盖，`LARK_MCP_` 前缀 |
| `audit.py` | 审计日志记录，详见 [SECURITY §3](./SECURITY.md#3-审计日志) |

### 2.2.1 模块内部接口定义

各模块间的调用契约（类型签名）：

```python
# === discovery.py ===
@dataclass
class ToolDefinition:
    name: str                    # "lark.calendar.agenda"（MCP tool name）
    cli_command: str             # "calendar events patch"（原始 schema name，用于 executor 调用）
    description: str             # 中文描述
    input_schema: dict           # JSON Schema（已清理 bridge 内部字段如 yes）
    output_schema: dict | None   # JSON Schema（可选）
    risk_level: Literal["read", "write", "destructive"]
    required_identity: Literal["user", "bot", "both"]
    scopes: list[str]
    doc_url: str | None
    danger: bool                 # 是否需要 --yes 确认

def discover_tools(*, settings: BridgeSettings | None = None, cache_path: Path | None = None) -> list[ToolDefinition]:
    """启动时调用，返回所有可注册的 tool 定义。优先从缓存加载，缓存不存在或 no_cache=True 时调用 lark-cli schema。"""

def get_tools_by_domain(tools: list[ToolDefinition]) -> dict[str, list[ToolDefinition]]:
    """按域分组 tool 列表，从 name 中提取 domain 部分。"""

# === executor.py ===
@dataclass
class ExecutionResult:
    success: bool
    data: dict | None            # lark-cli stdout JSON（成功时）
    error_code: str | None       # E_AUTH_EXPIRED, E_TIMEOUT 等
    error_message: str | None    # 中文错误描述
    recovery_hint: str | None    # 中文恢复建议
    duration_ms: int

def execute(command: list[str], *, settings: BridgeSettings | None = None) -> ExecutionResult:
    """执行 lark-cli 命令。command 为子命令及参数列表，如 ["calendar", "+agenda", "--format", "json"]"""

# === filters.py ===
def is_allowed(tool_name: str) -> bool:
    """检查命令是否通过安全策略"""

def get_risk_level(tool_name: str) -> Literal["read", "write", "destructive"]:
    """返回命令的风险级别"""

# === 错误传播 ===
# 所有模块内部错误统一为 BridgeError 层级：
#   BridgeError → DiscoveryError | ExecutionError | FilterError | ConfigError
# executor.py 不抛异常，返回 ExecutionResult（success=False）
# 仅不可恢复的启动错误（如 lark-cli 不存在）才抛异常阻止启动
```

### 2.3 数据流

**启动阶段**：
```
discovery.py → lark-cli schema --format json → 解析 JSON 数组 → 注册 atomic tools
           ↳ 优先从 $LARK_MCP_CACHE_DIR/schema_cache.json 加载缓存
           ↳ 缓存不存在或 LARK_MCP_NO_CACHE=true 时调用 CLI
           ↳ 解析过程：_name_to_mcp_tool_name() 转换命名 + _clean_input_schema() 清理内部字段
composite.py → 手工定义 → 注册 composite tools（含 input_examples）
prompts.py → 加载 → 注册 MCP prompts（领域知识）
```

**原子 tool 调用**：
```
Agent tool call → executor.run(command, args) → subprocess → lark-cli --format json
→ stdout JSON → 透传 MCP response（可选追加 _next_hint）
```

**复合 tool 调用**：
```
Agent tool call → composite 内部编排多步 atomic tool → 聚合结果 → 返回
（中间子进程结果不进 Agent context，由 composite 内部消化）
```

**Prompt 注入**：
```
Agent 收到飞书相关请求 → list_prompts() → 发现相关 prompt
→ get_prompt("lark-calendar-workflow") → 获得完整使用指南
→ 根据指南逐步调用 tool
```

### 2.4 Tool 注册策略：四层架构

> 设计来源：[Anthropic 工程师关于 MCP tool 设计的最佳实践](#9-参考来源)

核心洞察：Skill 模式的本质优势不是"选哪个命令"，而是 **SKILL.md 中的工作流引导**（先判断意图分支、再补默认值、冲突才追问）——这些推理逻辑在扁平化原子 tool 中会丢失。MCP 协议提供 tools / prompts / resources 三种 primitive，正确的做法是组合使用，而非把所有能力塞进 tool。

**四层架构**：

| 层 | MCP Primitive | 职责 | 示例 |
|---|---|---|---|
| **L1: 原子 tool** | tools（自动生成） | 单个飞书 API 操作 | `lark.im.messages-send` |
| **L2: 复合 tool** | tools（手工编写） | 封装多步工作流，中间结果不进 context | `lark.calendar.schedule-meeting`（内部编排 agenda → room-find → create） |
| **L3: Prompt 注入** | prompts | 领域知识按需加载，教 Agent "怎么用" | `prompts/lark-calendar-workflow`（等效 SKILL.md） |
| **L4: 智能引导** | tool description + examples + result hint | 帮 Agent 选对 tool、填对参数、知道下一步 | `input_examples`、`_next_hint`、可执行错误提示 |

**L1 与 L2 的边界判定**：如果一个业务流程需要 Agent 连续调用 ≥3 个原子 tool 才能完成（如预约会议需要查空闲 → 找会议室 → 创建日程），则应该封装为复合 tool。Anthropic 实测复合 tool 将准确率从 49% 提升到 74%（Opus 4）。

**L3 的设计原则**：按 Anthropic 的 Agent Skills 哲学——"Building a skill for an agent is like putting together an onboarding guide for a new hire"。L3 的 Prompt 本质上是把 lark-cli 的 26 个 SKILL.md 转化为 MCP prompt，Agent 按需加载，不占用 context。

**渐进式暴露**：避免 219 个 tool definition 撑爆 context（Anthropic 实测一个 Jira server 17K tokens）。优先暴露复合 tool 作为领域入口，原子 tool 在复合 tool 无法覆盖的边缘场景时按需暴露。

#### 渐进式暴露的具体实现机制

**默认暴露集**：bridge 启动后，MCP tool list 仅包含：
1. 所有 composite tool（L2，约 5-10 个）
2. 高频 atomic tool（L1 中标记为 `expose: always` 的，约 10-15 个）
3. 一个 meta-tool：`lark.discover`

**按需发现**：Agent 通过 `lark.discover` 查询某域下所有可用 tool：

```json
{
  "name": "lark.discover",
  "description": "查询指定飞书域下所有可用的原子操作。当 composite tool 无法满足需求时使用。",
  "inputSchema": {
    "properties": {
      "domain": { "type": "string", "description": "飞书域名，如 calendar, im, base" },
      "keyword": { "type": "string", "description": "可选，按关键词过滤" }
    },
    "required": ["domain"]
  }
}
```

**返回格式**：
```json
{
  "domain": "calendar",
  "available_tools": [
    {"name": "lark.calendar.event-get", "description": "获取单个日程详情", "risk_level": "read"},
    {"name": "lark.calendar.event-update", "description": "修改日程", "risk_level": "write"}
  ],
  "_hint": "如需使用上述 tool，直接按名称调用即可。所有 tool 已注册但默认不在 tool list 中显示。"
}
```

**实现原理**：所有 atomic tool 在 bridge 内部均已注册（可执行），但通过 FastMCP 的 tool list 过滤，默认只返回暴露集。`lark.discover` 的返回值让 Agent "知道"这些 tool 存在，从而可以调用。

### 2.5 Resources 层设计

MCP Resources 暴露只读上下文信息，帮助 Agent 感知当前环境：

| Resource URI | 内容 | 用途 | 实现状态 |
|---|---|---|---|
| `lark://identity` | 当前登录身份（user/bot）、用户名、open_id | Agent 判断可执行哪些操作 | ✅ 已实现 |
| `lark://permissions` | 当前飞书应用已授权的 scope 列表 | Agent 避免调用无权限的 API | ✅ 已实现 |
| `lark://domains` | 已注册的域列表及各域 tool 数量 | Agent 了解可用能力范围 | ✅ 已实现 |
| `lark://config` | bridge 运行配置摘要（过滤策略、超时等） | 调试用 | 计划中 |

**实现特点**：
- 所有 resource 函数通过 `lark-cli auth status` 获取数据（超时 10s）
- 错误时不抛异常，返回包含 `error` 字段的降级响应
- 接受可选 `settings: BridgeSettings` 参数，便于测试注入
- `get_domains_summary()` 内部复用 `discovery.discover_tools()` + `get_tools_by_domain()`

### 2.6 Identity（身份）处理

lark-cli 有 `--as user`（用户身份）和 `--as bot`（应用身份）两种模式。bridge 需要透传此概念：

- 默认行为：使用 lark-cli 的默认身份（由 `lark-cli config` 决定）
- 可选参数：部分 tool 允许指定 `--as user` 或 `--as bot`
- 部分域（如日历、云空间文档）必须 user 身份，bot 无权限——bridge 不做枚举校验，由 lark-cli 自行返回权限错误

**增强：Identity 精细化标记**

在 discovery 阶段为每个 tool 自动标记 `required_identity`：

| 标记 | 含义 | 来源 |
|---|---|---|
| `user` | 必须用户身份 | lark-cli 元数据中标记为 user-only 的 shortcut |
| `bot` | 必须应用身份 | lark-cli 元数据中标记为 bot-only 的 shortcut |
| `both` | 两种身份均可 | 默认值 |

在 tool description 中声明身份要求：
```
"description": "获取用户日历日程 [需要 user 身份]"
```

当身份不匹配时，返回 actionable error 而非让 lark-cli 报晦涩错误：
```
"此操作需要 user 身份。当前为 bot 身份。请使用 identityAs: \"user\" 参数重试。"
```

### 2.7 MCP Tool 设计十二条（提炼自 Anthropic 官方指南）

> 详细说明与引用参见 [第 9 节参考来源](#9-参考来源)

**粒度原则**
1. **Composite over atomic**：合并多个 API 为一个语义操作，模拟人类完成任务的思维过程 [Anthropic #1]
2. **namespace 分组**：按域前缀命名（`lark.calendar.*`），避免 Agent 混淆 [Anthropic #2]
3. **渐进式暴露**：先注册领域入口 tool，Agent 按需发现子命令——避免 219 个 tool 撑爆 context [Anthropic advanced]

**返回数据原则**
4. **高信号输出**：返回 name 而非 uuid，返回 url 而非内部 ID；提供 `concise`/`detailed` 两级返回 [Anthropic #3]
5. **Token 效率**：默认分页、默认精简，但允许 Agent 主动请求更多 [Anthropic #4]
6. **可执行错误**：错误信息告诉 Agent "如何修正"，而非仅返回错误码 [Anthropic #4]
7. **Result hint**：返回值追加 `_next_hint` 字段，引导 Agent 下一步操作 [本设计]

**表现力原则**
8. **Description = prompt engineering**：tool description 对 Agent 的影响 ≥ system prompt [Anthropic #5]
9. **Input examples > 文字描述**：tool schema 嵌入 `input_examples`，解决 JSON Schema 无法表达的用法模式 [Anthropic advanced]
10. **Skills = prompts**：Skill 文档不等于 tool，应通过 MCP prompt 按需注入 [Anthropic skills]

**工程原则**
11. **ACI ≥ HCI**：Agent-Computer Interface 的设计投入应不低于 Human-Computer Interface [Anthropic #2 appendix]
12. **最小高信号 token 集**：找到能最大化期望结果的最小 token 集合 [Anthropic context engineering]

---

### 2.8 性能设计

#### 子进程执行模型

**当前方案（Phase 1-2）**：每次 tool call 独立 `subprocess.run()`，简单可靠。

**优化方案（Phase 4+）**：进程池模式，减少冷启动开销。

```
executor.py
├── mode = "simple"    # Phase 1-2: subprocess.run() per call
└── mode = "pool"      # Phase 4+: 预启动 N 个 worker
    ├── LARK_MCP_POOL_SIZE = 3 (default)
    ├── worker idle timeout = 60s
    └── 超过 pool 容量 → 排队等待（不 spawn 新进程）
```

#### 缓存策略

| 缓存对象 | TTL | 失效条件 | 实现位置 |
|---|---|---|---|
| Discovery 元数据（schema） | 持久化至 `$LARK_MCP_CACHE_DIR/schema_cache.json` | `LARK_MCP_NO_CACHE=true` / 手动删除缓存文件 | `discovery.py` 内置 |
| 联系人搜索结果 | 5 min | 手动清除 | `cache.py`（计划） |
| 日历空闲时段 | 2 min | tool call 后自动失效 | `cache.py`（计划） |

---

### 2.9 降级策略

| 场景 | bridge 行为 |
|---|---|
| lark-cli 未安装 | 启动失败，stderr 输出清晰错误信息 + 安装指引 |
| lark-cli 未认证（auth status ≠ ready） | 启动成功，但注册 0 个 tool + 注册 1 个 `lark.auth-required` 提示 tool |
| 认证过期（运行中） | tool call 返回 `E_AUTH_EXPIRED` + recovery_hint |
| 部分域授权不全 | 所有 tool 正常注册；调用时由 lark-cli 返回权限错误，bridge 转为 `E_PERMISSION_DENIED` |
| lark-cli 版本过旧（缺少 `schema --format json`） | 启动失败，提示最低版本要求 |
| schema 命令返回空列表 | 启动成功，注册 0 个 tool，stderr 警告 |

**设计原则**：
- **启动尽量成功**——即使认证不全也能启动，通过 tool 响应告知问题
- **错误信息可操作**——每个降级状态都有 recovery_hint
- **不静默失败**——所有降级在 stderr 中记录 WARNING

### 最低版本要求

```
lark-cli >= 1.0.43（首个支持 schema --format json 输出 envelope_version 1.0 的版本）
```

---

## 3. 技术选型

### 3.1 语言：Python

| 维度 | 评估 |
|---|---|
| MCP SDK | `mcp` v1.27.1，FastMCP + HTTP streaming 一行配置 |
| 动态性 | JSON → 函数注册天然适合 |
| 生命周期 | lark-cli 日更，重启 bridge 即可，无需重编译 |
| 性能 | 无关（瓶颈在 lark-cli 子进程 I/O） |
| 环境 | 复用现有 conda `agent-study` |
| 开源 | PyPI 分发成熟，pyproject.toml 标准化 |

### 3.2 关键依赖

| 依赖 | 用途 |
|---|---|
| `mcp` >= 1.27 | FastMCP server + HTTP streaming transport（内含 uvicorn） |
| `lark-cli` (external) | 子进程调用的飞书 CLI，需用户独立安装 |

### 3.3 API 封装粒度

**原子 tool（自动生成）**：通过 discovery.py 将 lark-cli 命令映射为 MCP tool：
- tool name = `lark.<domain>.<shortcut>`
- tool description = 来自 lark-cli 元数据 + 手动增强
- tool parameters = CLI flags 的 JSON Schema 自动映射
- tool response = lark-cli `--format json` stdout 透传

**复合 tool（手工编写）**：对高频多步工作流封装为单个语义操作：
- 内部编排多个原子 tool 调用
- 中间子进程结果不进 Agent context（减少 token 消耗）
- 只有最终聚合结果返回给 Agent

**Prompt（领域知识注入）**：从 lark-cli 的 SKILL.md 提取关键规则：
- Agent 处理飞书相关请求时，先通过 `list_prompts` 发现可用指南
- 按需 `get_prompt` 获取完整使用说明
- 等效于 Skill 模式的"教 Agent 怎么用"

---

## 4. MCP Tool 命名规范

```
lark.<domain>.<action>

domain 对应 lark-cli 域: im | calendar | base | docs | sheets | task | mail | contact | wiki | vc | approval | attendance | okr | drive | ...
action 对应 lark-cli shortcut: +messages-send, +agenda, +record-search 等（+ 和 - 去除）

示例:
  lark.im.messages-send
  lark.calendar.agenda
  lark.base.record-search
  lark.docs.fetch
  lark.contact.search-user
```

---

## 5. 安全模型

| 层级 | 措施 |
|---|---|
| 认证 | lark-cli 自身管理 OAuth token（OS keychain），bridge 不接触凭证 |
| 命令过滤 | filters.py 默认黑名单：`delete`、`remove`、`destroy` |
| 权限 | 运行在 lark-cli 已授权的 app scope 内，无额外提权 |
| 网络 | bridge 仅监听 localhost |

---

## 6. 开发路线

参见 [ROADMAP.md](./ROADMAP.md)

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| lark-cli 命令树格式变更 | CI 兼容性检查 |
| 子进程超时 | 默认 30s，可配置 |
| lark-cli 未安装/未认证 | 启动时预检，友好错误提示 |
| 并发调用 | FastMCP 默认 async，每个 tool call 为独立子进程 |

---

## 8. 项目结构

```
lark-mcp-bridge/
├── pyproject.toml
├── src/lark_mcp_bridge/
│   ├── __init__.py
│   ├── server.py       # FastMCP HTTP streaming 入口
│   ├── discovery.py    # lark-cli 命令元数据 → 原子 tool
│   ├── composite.py    # 手工维护的复合 tool（多步工作流）
│   ├── prompts.py      # 领域知识 Prompt 注册入口
│   ├── prompts/        # Prompt 内容文件（详见 PROMPTS_GUIDE）
│   ├── executor.py     # subprocess 执行 + exit code 处理
│   ├── filters.py      # 白名单优先过滤
│   ├── cache.py        # Discovery 缓存 + 热门数据缓存
│   ├── resources.py    # MCP Resources 层
│   ├── config.py       # 统一配置（pydantic-settings）
│   └── audit.py        # 审计日志
├── tests/
│   ├── test_executor.py
│   ├── test_composite.py
│   └── test_filters.py
├── docs/
│   ├── PROJECT_DESIGN.md   # 本文档
│   ├── ROADMAP.md
│   ├── DEPLOYMENT.md
│   ├── SECURITY.md
│   ├── OBSERVABILITY.md
│   ├── PROMPTS_GUIDE.md
│   ├── API_SPEC.md
│   ├── CHANGELOG.md
│   └── INDEX.md
├── scripts/
│   └── sync_prompts.py    # Prompt 同步脚本
└── README.md
```

---

## 9. 参考来源

以下 5 篇 Anthropic 官方文章为本项目的 MCP tool 设计策略提供了核心理论依据：

1. **[Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents)**（2025-09）
   - 提出五原则：Composite > Atomic、namespace 分组、高信号输出、Token 效率、Description 即 prompt engineering
   - 核心金句："Tools are a new kind of software which reflects a contract between deterministic systems and non-deterministic agents"

2. **[Introducing advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)**（2025-11）
   - 三种高级模式：Tool Search（渐进式发现，Token 节省 85-95%）、Programmatic Tool Calling（用代码编排工具）、Tool Use Examples
   - 量化数据：复合 tool 准确率 49% → 74%（Opus 4）

3. **[Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)**（2025-10）
   - Skills 的本质："putting together an onboarding guide for a new hire"
   - 三级渐进式泄露，按需读取不占 context
   - 直接验证了本项目的 Prompt 层设计

4. **[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)**（2024-12）
   - 基础理论：何时用 workflow vs agent，何时用 tool vs prompt
   - 关键建议："Tool definitions should be given just as much prompt engineering attention as your overall prompts"

5. **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)**（2025-09）
   - 上下文预算（attention budget）理论
   - 金句："Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome"
   - "If a human engineer can't definitively say which tool should be used, an AI agent can't be expected to do better"

**社区补充**：
- [Latent Space 播客：MCP 协议作者谈设计哲学](https://www.latent.space/p/mcp)（2025-03）——MCP 三个 primitive 的正确用法
- [Towards AI Friendly Web APIs](https://medium.com/@chalyi/towards-ai-friendly-web-apis-mykhailo-chalyi-c40c2b9d13ec)（2026-05）——API 设计六原则（语义化操作、自说明 schema、可执行错误等）
