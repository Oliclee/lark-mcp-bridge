# EVALUATION: 项目可行性评估与决策记录

> 文档索引见 [INDEX.md](./INDEX.md)

> 本文档记录项目立项决策依据、可行性分析和关键假设。上线后追加 Review 段落，与初始评估对比。

---

## 1. 项目动机

### 1.1 为什么要做

| 维度 | 说明 |
|---|---|
| **用户痛点** | 飞书是国内企业主力协作平台，但 AI Agent 生态（MCP）中无成熟的飞书集成方案 |
| **市场空白** | 唯一的 `larksuite/lark-openapi-mcp` 已停更 10 个月（v0.5.1），仅裸 API 封装，无 Agent 友好设计 |
| **时机窗口** | lark-cli 已成为飞书官方主力工具（13k stars, 日更, 26 Skills, 200+ commands），但自身定位是 CLI 而非 MCP server |
| **差异化价值** | 不是重写飞书 API 封装，而是站在 lark-cli 肩膀上做 MCP 适配——工作量小、跟随升级成本低 |

### 1.2 不做的后果

- Agent 用户需要自己手动 prompt engineering 去拼 lark-cli 命令（体验差、成功率低）
- 每个 Agent 用户重复造轮子：解析 CLI 输出、处理错误、管理认证流程
- 飞书在 AI Agent 生态中持续处于"不可达"状态

### 1.3 成功标准（Definition of Done）

| 阶段 | 指标 |
|---|---|
| MVP 成功 | Agent 能完成 3 个核心场景（查日程、发消息、搜联系人）且成功率 > 80% |
| 生产可用 | 支持 10+ 域、Agent 首次 tool call 成功率 > 70%、平均调用延迟 < 3s |
| 开源成功 | GitHub stars > 100、有外部 contributor PR |

---

## 2. lark-cli 依赖分析

### 2.1 为什么选择 lark-cli 作为底层

| 因素 | 评估 |
|---|---|
| **维护活跃度** | ⭐⭐⭐⭐⭐ 503 commits，日更级别，官方团队维护 |
| **功能覆盖** | ⭐⭐⭐⭐⭐ 18 域 200+ 命令，远超任何第三方封装 |
| **Agent 友好** | ⭐⭐⭐⭐ 原生支持 `--format json`，结构化输出，Smart defaults |
| **文档质量** | ⭐⭐⭐⭐ 26 个 SKILL.md，含意图分支和错误恢复指南 |
| **API 稳定性** | ⭐⭐⭐⭐ Shortcut 层稳定，三层架构分明，breaking change 极少 |
| **安装便捷性** | ⭐⭐⭐ 需要 Node.js (`npx @larksuite/cli@latest install`)，非 Python 原生 |

### 2.2 lark-cli 的架构优势（对 bridge 有利）

```
lark-cli 三层命令架构：

Layer 1: Shortcuts（如 +agenda, +send）
  ↑ bridge 主要包装这一层
  - 人/AI 友好，Smart defaults
  - 前缀 +/- 区分读写（bridge 可用于 risk 分类）

Layer 2: API Commands（如 api calendar event list）
  ↑ bridge 可选暴露，用于 shortcut 无法覆盖的场景
  - 与飞书开放平台 1:1 对应

Layer 3: Raw API（http get/post）
  ✗ bridge 不暴露——Agent 不应直接发 HTTP
```

### 2.3 lark-cli 的风险点

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| lark-cli 停更/项目方向转变 | 低 | 高 | 官方主力项目，13k stars，极不可能 |
| Shortcut 前缀语义变化 | 低 | 中 | bridge 的 risk 分级支持手动 override |
| `--format json` 输出结构变化 | 极低 | 高 | bridge 不解析 `data` 内部结构，仅透传 |
| 新版本引入 breaking change | 低 | 中 | 版本感知缓存 + CI 集成测试覆盖 |
| Node.js 依赖导致部署复杂 | 中 | 低 | Dockerfile 封装，一次配置 |
| lark-cli 命令执行慢（子进程开销） | 中 | 中 | 进程池 + 缓存双重优化 |

### 2.4 lark-cli 更新适应性评估

```
lark-cli 变更类型 → bridge 影响：

✅ 自动适应（~80% 变更）：
   - 新增 Shortcut → discovery.py 自动发现
   - 新增参数 → 映射规则自动处理
   - 新增 API Command → 自动注册

⚙️ 配置适应（< 5min）：
   - 新域上线 → 白名单加一行

🔧 人工适应（每月 1-2 次）：
   - 新 SKILL.md → sync_prompts.py + review
   - 高频 tool 需要 description 增强 → override map

🏗️ 设计适应（季度级）：
   - 新跨域场景 → 新 composite tool + scenario prompt
```

---

## 3. 技术可行性

### 3.1 核心假设验证

| 假设 | 验证方式 | 当前状态 |
|---|---|---|
| lark-cli 可通过 subprocess 可靠调用 | 原型验证 | ✅ `subprocess.run(["lark-cli", "calendar", "+agenda", "--format", "json"])` 可行 |
| lark-cli `--format json` 输出是稳定的结构化数据 | 多版本对比 | ✅ JSON envelope `{code, msg, data}` 稳定 |
| FastMCP 支持 HTTP streaming transport | 库文档确认 | ✅ FastMCP 原生支持 |
| lark-cli 内建元数据可供 discovery | 源码分析 + 验证 | ✅ 已验证（详见下方 §3.3） |
| MCP Prompt 能有效提升 Agent 成功率 | Phase 1.5 A/B 测试 | ⏳ 待验证 |

### 3.2 元数据 Discovery 可行性验证（2026-05-29）

通过分析 lark-cli 源码（GitHub larksuite/cli），验证了元数据暴露能力：

#### API Command 层：✅ 完美支持

`lark-cli schema` 命令原生输出结构化 JSON 元数据：

```bash
# 列出所有 service
lark-cli schema --format json

# 列出某 service 的所有 resource + method
lark-cli schema calendar --format json

# 某个具体 method 的完整 schema
lark-cli schema calendar.calendar_event.list --format json
```

输出包含：`name`、`httpMethod`、`path`、`parameters`（type/location/required/options/example/description）、`requestBody`、`responseBody`、`accessTokens`（user/bot）、`scopes`、`docUrl`。

数据来源：`internal/registry` 包中维护的 meta JSON，通过 `registry.ListFromMetaProjects()` 和 `registry.LoadFromMeta()` 加载。

#### Shortcut 层：⚠️ 需 help 文本解析

每个 Shortcut 在源码中声明了丰富的元数据结构体（`common.Shortcut`）：

```go
var CalendarAgenda = common.Shortcut{
    Service:     "calendar",
    Command:     "+agenda",
    Description: "View calendar agenda (defaults to today)",
    Risk:        "read",               // ← bridge 可直接用于 risk_level 分级
    Scopes:      []string{"calendar:calendar.event:read"},
    AuthTypes:   []string{"user", "bot"},  // ← bridge 可用于 identity 标记
    HasFormat:   true,
    Flags: []common.Flag{
        {Name: "start", Desc: "start time (ISO 8601, default: start of today)"},
        {Name: "end", Desc: "end time (ISO 8601, default: end of start day)"},
        {Name: "calendar-id", Desc: "calendar ID (default: primary)"},
    },
}
```

**但运行时暴露有限**：lark-cli 未提供 `lark-cli shortcuts --format json` 这样的命令直接导出 Shortcut 元数据。需通过 `lark-cli <service> --help` 解析文本输出获取命令列表和 flags。

#### bridge discovery.py 的策略（基于验证结论）

```
优先级 1: lark-cli schema --format json
  → 获取完整 API Command 层元数据（service/resource/method/params/types/scopes/identity）
  → 适合 L1 atomic tool 注册

优先级 2: lark-cli <service> --help
  → 解析 Shortcut 列表（命令名 + 描述 + flags）
  → 作为高频 tool 的补充来源

优先级 3: override 配置（manual.toml / auto_enhanced.json）
  → 补充 risk_level（从源码 Risk 字段映射）
  → 增强 description（从 SKILL.md 提取）
  → 修正 identity 标记
```

#### 关键发现

- Shortcut 源码中的 `Risk` 字段（"read"/"write"/"danger"）是我们 risk_level 分级的最权威来源
- `AuthTypes` 字段（"user"/"bot"）是 identity 标记的权威来源
- 这些字段虽然运行时未直接暴露 JSON，但可以通过一次性脚本从 GitHub 源码提取，生成静态的 `override/shortcut_meta.json`，随版本更新刷新

#### 验证数据（2026-05-29，lark-cli v1.0.43）

> v1.0.44 (2026-05-29 发布) 已确认兼容：schema 输出格式不变，无 breaking change。详见 [lark-cli CHANGELOG](https://github.com/larksuite/cli/blob/main/CHANGELOG.md)。

```
lark-cli schema --format json 实测输出：

总 tool 数量:     219
覆盖域:          14 个
  mail: 57, task: 34, drive: 25, im: 24, okr: 23,
  calendar: 18, approval: 11, wiki: 10, sheets: 8,
  slides: 5, attendance: 1, contact: 1, minutes: 1, vc: 1

风险分级（_meta.risk 字段，自动可用）：
  read: 87, write: 95, high-risk-write: 37

Identity（_meta.access_tokens 字段，自动可用）：
  user only: 28, bot only: 10, both: 181

Schema 丰富度：
  有 example:      216/219 (98.6%)
  有 doc_url:      216/219 (98.6%)
  有 outputSchema: 168/219 (76.7%)
  有 enum:         103/219 (47.0%)

实际调用延迟（calendar +agenda）：687ms
```

#### 对设计的简化影响

| 原设计假设 | 验证后结论 | 影响 |
|---|---|---|
| risk_level 需启发式推断（+/- 前缀） | ❌ 不需要——`_meta.risk` 直接提供三级分级 | 删除启发式逻辑 |
| identity 需从源码提取 | ❌ 不需要——`_meta.access_tokens` 直接提供 | 删除 GitHub 源码提取方案 |
| inputSchema 需从 CLI flags 映射 | ❌ 不需要——直接就是 JSON Schema 格式 | discovery.py 大幅简化 |
| 需要手动 override description | ⚠️ 大幅减少——98.6% 已有 description + example | 仅少量 Shortcut 层需增强 |
| 可能需要进程池 | ❌ 687ms 延迟远低于 60s 限制 | Phase 4 进程池降为可选 |

### 3.3 技术栈风险

| 组件 | 成熟度 | 替代方案 |
|---|---|---|
| Python 3.12 | 成熟 | — |
| FastMCP | 较新但活跃 | 自行实现 MCP protocol（不推荐） |
| lark-cli (Node.js) | 成熟 | 直接调飞书 OpenAPI（放弃 CLI 的 Smart defaults） |
| subprocess 通信 | 成熟 | stdin/stdout JSON-RPC（更复杂，收益待评估） |

### 3.4 工程量估算

| Phase | 估算工时 | 关键交付物 |
|---|---|---|
| Phase 0 | 2h | 仓库骨架 |
| Phase 1 | 8h | MVP，5 个固定 tool 可调用 |
| Phase 1.5 | 4h | 端到端验证 |
| Phase 2 | 12h | 动态发现 + 过滤 + 缓存 |
| Phase 3 | 8h | 增强 description + 审计 |
| Phase 4 | 8h | Docker + 健康检查 + 指标 |
| Phase 5 | 4h | 发布 + 文档 |
| **合计** | **~46h** | |

---

### 3.5 接入端分析：Amazon Quick 集成方式

Amazon Quick 提供 5 种第三方集成方式：

| 方式 | 定位 | 适用场景 |
|---|---|---|
| **MCP** | 开放协议，连接任意 MCP server | 自定义工具集成（本项目） |
| **Action Connector** | 预构建 50+ 连接器 | 主流 SaaS（Slack, Jira, Google 等） |
| **OpenAPI Spec** | 基于 OpenAPI 3.0 schema 自动生成 action | 有标准 spec 的 REST API |
| **REST API** | 最灵活的自定义 REST 连接 | 无 spec 的任意 HTTP API |
| **Coding Agents (ACP)** | 委派编码任务 | Kiro, Claude Code |

### MCP 在 Amazon Quick 中的两种形态

| 形态 | Desktop | Enterprise | 说明 |
|---|---|---|---|
| **Local stdio** | ✅ | ❌ | Quick 直接 spawn 本地进程（command + args） |
| **Remote HTTP** | ✅ | ✅ | 连接远程 HTTP endpoint（streamable-http / SSE） |
| **Import** | ✅ | ❌ | 从 Kiro/Claude Code 配置文件导入 |

### Quick MCP 关键限制

| 限制 | 影响 |
|---|---|
| 60s 超时硬限制 | composite tool 必须在 60s 内完成 |
| Tool list 静态 | 需重建 integration 才能刷新 → `lark.discover` meta-tool 方案正确 |
| 不支持自定义 HTTP header | 认证必须走 OAuth/Token/无认证 |
| 不支持 tool list 变更通知 | 与我们"重启生效"设计一致 |

### 部署模式决策

**当前版本决策：仅支持 Local stdio 模式。**

理由：
- 无需部署 HTTP 服务、无需 Docker
- Quick Desktop 自动管理进程生命周期（启动/停止）
- 对用户本地资源占用最小
- 用户体验最简：Settings → MCP → Add Local → 填 command/args 即可
- Remote HTTP 模式作为后续扩展（Phase 4），服务 Enterprise 场景

Local stdio 模式下用户配置：
```
Name: Lark MCP Bridge
Command: python
Arguments: -m lark_mcp_bridge.server
```

### 3.6 语言策略分析

### 发现

- MCP tool name 必须英文（协议约定）
- tool description / 参数描述 / Prompt / 错误提示可自由选择语言
- 中文 token 消耗约为英文 1.5-2x（"查看日历日程" ≈ 6 tokens vs "View calendar agenda" ≈ 3 tokens）
- 30 个 tool × 50 字 description：中文 ~3000 tokens vs 英文 ~1500 tokens，差值 ~1500 tokens
- Amazon Quick 200K context window 下占比 < 2%，可忽略

### 分析

| 方案 | 优点 | 缺点 |
|---|---|---|
| 纯英文 | token 节省、国际通用 | 中文场景下 Agent 匹配 tool 的语义距离稍远 |
| 纯中文 | Agent 在中文对话中匹配更精准、错误提示无需二次翻译 | token 稍多、国际用户不友好 |
| 中英混合（推荐） | 兼顾两者 | 维护时需注意一致性 |

### 结论

token 差异在 200K context 下可忽略。中文 description 在中文对话场景下匹配更直接。

### 决策

| 决策项 | 决策 | 归属期 | 理由 |
|---|---|---|---|
| tool name 使用英文 | YES | Phase 1 | MCP 协议约定，无选择 |
| description / 参数描述使用中文 | YES | Phase 1 | 用户中文优先，Agent 匹配更精准 |
| Prompt 内容使用中文 | YES | Phase 1 | 意图分支、默认值规则、错误恢复均面向中文场景 |
| 错误提示使用中文 | YES | Phase 1 | 用户直接可读，无需 Agent 翻译 |
| 未来增加 `LARK_MCP_LANG` 多语言切换 | 延后 | Phase 5 | 开源发布时再考虑国际用户 |

---

## 4. 竞品与差异化

### 4.1 竞品对比

| 方案 | 覆盖面 | Agent 友好 | 维护状态 | 跟随飞书更新 |
|---|---|---|---|---|
| `larksuite/lark-openapi-mcp` | 中 | ❌ 裸 API | ❌ 停更 10 月 | ❌ 无 |
| 自行封装飞书 OpenAPI | 高 | ❌ 需大量设计 | — | ❌ 需持续追赶 |
| **lark-mcp-bridge（本项目）** | 高 | ✅ 四层架构 | — | ✅ 自动跟随 lark-cli |

### 4.2 本项目的核心差异

1. **站在巨人肩膀上**：不重写 API 封装，复用 lark-cli 的 200+ 命令和 Smart defaults
2. **四层 Agent 友好设计**：不是简单暴露命令，而是 Prompt → Composite → Atomic → Discovery 分层引导
3. **自动跟随更新**：dynamic discovery 机制让 80% 的 lark-cli 更新零成本适应
4. **安全第一**：白名单优先 + risk_level 分级 + 审计日志，适合企业场景

---

## 5. 项目风险总览

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Agent 使用成功率低于预期 | 中 | 高 | Phase 1.5 提前验证 + Prompt 持续迭代 |
| subprocess 延迟不可接受 | 低 | 中 | Phase 2.5 基准测试 + 进程池备选 |
| lark-cli discovery 机制不稳定 | 低 | 高 | 固定 tool 作为 fallback（Phase 1 的手动注册可作为降级方案） |
| Amazon Quick MCP 集成有未知限制 | 中 | 中 | 早期原型验证（Phase 1 核心目标） |
| 开源后无人使用 | 中 | 低 | 先解决自己的问题，开源是附带价值 |

---

## 6. 决策记录

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-05-29 | 选择包装 lark-cli 而非直接调飞书 OpenAPI | 复用 200+ 命令 + Smart defaults，工作量减少 80% |
| 2026-05-29 | 选择 Python + FastMCP 而非 Go/Node | 与 AI/Agent 生态更亲和，FastMCP 简化 MCP 实现 |
| 2026-05-29 | 采用白名单优先安全策略 | 企业场景安全要求，宁可漏暴露不可多暴露 |
| 2026-05-29 | 当前版本仅支持 Local stdio 模式 | 最简部署、无需 Docker/HTTP、资源占用小；Remote HTTP 留待 Phase 4 |
| 2026-05-29 | 设计四层 tool 架构 | Anthropic 最佳实践验证，避免 tool 过多淹没 context |
| 2026-05-29 | License 选择 MIT | lark-cli 本身是 MIT，保持一致，最宽松 |
| 2026-05-29 | 分支策略：当前直推 main | 独立开发阶段无 PR 开销；开源时加分支保护 |
| 2026-05-29 | Commit 规范：Conventional Commits | 低学习成本、CHANGELOG 可自动生成、历史可追溯 |
| 2026-05-29 | 文档与代码同仓 | 版本一致性优先；改接口时强制同步文档 |
| 2026-05-29 | 版本策略：bridge 独立 SemVer，不绑定 lark-cli 版本 | bridge 的 breaking change（tool name 规则变更、配置格式变更）独立于 lark-cli 更新；lark-cli 升级仅需重启 bridge |

---

## 7. 待决策项

以下事项已识别但当前信息不足或时机未到，需等待触发条件后再决策。

| 编号 | 待决策问题 | 触发条件 | 预期决策期 | 依赖数据 |
|---|---|---|---|---|
| P-01 | 是否引入进程池 | Phase 2.5 性能基准完成后 | Phase 4 启动前 | 并发场景下 P95 延迟是否 > 3s |
| P-02 | 是否需要 Shortcut 层专用 discovery | Phase 1.5 验证"仅用 API Command 层 schema"是否足够 | Phase 2 | Agent 使用 Shortcut 的成功率 vs API Command |
| P-03 | 是否支持 Remote HTTP 模式 | 出现 Enterprise 用户需求 | Phase 4 | 用户反馈 / 团队共享场景 |
| P-04 | 是否发布多语言版本（`LARK_MCP_LANG`） | 开源后国际用户反馈 | Phase 5 | GitHub issues 中英文需求比 |
| P-05 | 是否将 219 个 API tool 全部暴露 vs 精选子集 | Phase 1.5 验证 tool list 对 Agent context 的影响 | Phase 2 | Agent 成功率与 tool 数量的关系 |
| P-06 | 是否需要 `auto_enhanced.json` 中间层 description | Phase 3 评估原始 description 的 Agent 可理解性 | Phase 3 | Agent 首次 tool call 匹配率 |
| P-07 | `yes` 确认参数的处理策略（透传 vs bridge 拦截） | Phase 1 实现时评估 | Phase 1 | 高风险操作的用户体验流程设计 |
| P-08 | 是否利用 lark-cli 的 `X-Agent-Trace` header 功能（#1158, v1.0.44）实现链路追踪 | Phase 3 可观测性增强时评估 | Phase 3 | 设置 `LARKSUITE_CLI_AGENT_TRACE=lark-mcp-bridge/{version}` 环境变量传递给子进程。**已确认不影响 Phase 2**：纯新增功能，不设则无影响 |

> **注**：待决策项在触发条件满足后，移至 §6 决策记录表（标注日期和结论）。
> 如果分析后结论为"不做"，同样记录并注明理由，不删除条目。

---

## 8. 上线后 Review（待填写）

> 以下内容在项目上线稳定运行后填写，与上述初始评估对比。

### 8.1 假设验证结果

| 初始假设 | 实际结果 | 差异分析 |
|---|---|---|
| Agent 首次 tool call 成功率 > 70% | _待填写_ | |
| 平均调用延迟 < 3s | _待填写_ | |
| Prompt 提升成功率 | _待填写_ | |
| 80% lark-cli 更新自动适应 | _待填写_ | |

### 8.2 意外发现

_待填写：上线后发现的未预见问题或机会_

### 8.3 架构调整记录

| 日期 | 调整 | 原因 |
|---|---|---|
| _待填写_ | | |

### 8.4 成本 vs 收益回顾

| 指标 | 预期 | 实际 |
|---|---|---|
| 总开发工时 | ~46h | _待填写_ |
| 日常维护工时/月 | < 4h | _待填写_ |
| 覆盖飞书域数 | 10+ | _待填写_ |
| 外部用户数 | > 0 | _待填写_ |
