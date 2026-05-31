# 文档索引

lark-mcp-bridge 项目文档结构说明。

---

## 目录结构

```
docs/
├── INDEX.md              ← 本文件：文档索引与导航
├── EVALUATION.md         ← 立项评估 + 可行性分析 + 上线后 Review
├── PROJECT_DESIGN.md     ← 架构 + 模块 + 数据流（核心设计文档）
├── API_SPEC.md           ← 接口契约（tool schema / error / protocol）
├── SECURITY.md           ← 安全模型 + 审计 + 权限分级
├── OBSERVABILITY.md      ← 健康检查 + 指标 + 日志规范
├── PROMPTS_GUIDE.md      ← Prompt 维护指南（来源、同步、编写规范）
├── TESTING.md            ← 测试策略（分层、Mock、Fixture、CI）
├── REVIEW_CHECKLIST.md   ← 设计审核清单（Gate Review 通用模板）
├── DEPLOYMENT.md         ← 部署 + 配置 + 环境变量
├── ROADMAP.md            ← 里程碑 + 进度跟踪
└── CHANGELOG.md          ← 版本变更记录
```

---

## 按受众索引

| 受众 | 应阅读文档 |
|---|---|
| **开发者**（功能开发） | PROJECT_DESIGN → API_SPEC → PROMPTS_GUIDE |
| **决策者/评审者** | EVALUATION → PROJECT_DESIGN → ROADMAP |
| **运维**（部署运行） | DEPLOYMENT → OBSERVABILITY |
| **安全审计** | SECURITY → API_SPEC（错误码/权限） |
| **测试/QA** | TESTING → PROJECT_DESIGN §2.2.1（接口定义） |
| **Prompt 维护者**（新增/更新飞书域 Prompt） | PROMPTS_GUIDE → PROJECT_DESIGN §2.4 |
| **贡献者**（首次参与） | INDEX → PROJECT_DESIGN → ROADMAP |

---

## 按变更频率索引

| 频率 | 文档 | 说明 |
|---|---|---|
| 高频 | ROADMAP, CHANGELOG | 每次迭代更新 |
| 低频（追加） | EVALUATION §7 | 上线后 Review，与初始评估对比 |
| 中频 | API_SPEC, PROMPTS_GUIDE, DEPLOYMENT | 新增 tool/prompt/配置时更新 |
| 低频 | PROJECT_DESIGN, SECURITY, OBSERVABILITY | 架构变更时更新，需严格 review |

---

## 文档职责边界

| 文档 | 回答的问题 | 不应包含 |
|---|---|---|
| EVALUATION | "为什么做？值不值得？做对了吗？" | 具体实现细节（引用 DESIGN） |
| PROJECT_DESIGN | "系统如何工作？模块如何协作？" | 具体接口字段定义、部署步骤 |
| API_SPEC | "接口契约是什么？请求/响应格式？" | 架构决策理由、部署配置 |
| TESTING | "如何测试？Mock 策略？CI 怎么跑？" | 测试用例实现代码 |
| TESTING | "如何测试？Mock 策略？CI 怎么跑？" | 测试用例实现代码 |
| SECURITY | "什么能做？什么不能做？如何审计？" | 具体错误码（引用 API_SPEC） |
| OBSERVABILITY | "如何监控？指标含义？日志在哪？" | 安全策略（引用 SECURITY） |
| PROMPTS_GUIDE | "如何新增/更新 Prompt？格式规范？" | Prompt 的运行机制（引用 DESIGN） |
| DEPLOYMENT | "如何安装？如何配置？如何启动？" | 架构原理（引用 DESIGN） |
| ROADMAP | "下一步做什么？进度如何？" | 技术细节 |
| CHANGELOG | "这个版本改了什么？" | 未来计划（在 ROADMAP） |

### 内容边界判定原则

当不确定某段内容应放哪个文档时，用以下标准判断：

| 内容性质 | 归属 | 示例 |
|---|---|---|
| "这样做可行吗？"（论证可行性的分析细节） | EVALUATION | "discovery.py 可通过 schema 命令获取元数据" |
| "就这样做"（接口签名、模块设计规范） | PROJECT_DESIGN | "discover_tools() → list[ToolDefinition]" |
| "按这个格式交互"（外部契约） | API_SPEC | tool schema 示例、错误码定义 |
| "用户这样操作"（部署步骤、配置项） | DEPLOYMENT | 环境变量表、启动命令 |

> EVALUATION 允许包含"分析级别的实现细节"（支撑论证），但**权威定义**始终在对应的实现文档中。如两处冲突，以 DESIGN/API_SPEC/DEPLOYMENT 为准。

---

## 交叉引用约定

文档间引用使用相对链接：

```markdown
详见 [安全模型](./SECURITY.md#命令过滤策略)
参见 [API_SPEC §错误码映射](./API_SPEC.md#错误码映射)
```

---

## 术语约定

以下术语在不同文档中根据语境有不同写法，均指同一项目：

| 写法 | 使用场景 | 示例 |
|---|---|---|
| `lark-mcp-bridge` | 项目名、仓库名、CLI 命令 | "git clone lark-mcp-bridge"、文档标题 |
| `lark_mcp_bridge` | Python 包名、import 路径 | `from lark_mcp_bridge.executor import ...` |
| `Lark MCP Bridge` | 用户界面显示名（如 Quick 配置中的 Name 字段） | Settings → MCP → Name: "Lark MCP Bridge" |

**规则**：三种写法各有其固定使用场景，不可混用。如需泛指本项目，使用 `lark-mcp-bridge`（kebab-case）。

---

## 错误码体系说明

错误码在文档中有两种粒度，含义不同：

| 粒度 | 格式 | 定义位置 | 用途 |
|---|---|---|---|
| **前缀（分类）** | `E_AUTH_*`、`E_NET_*`、`E_CLI_*` | OBSERVABILITY.md §5.1 | 日志分类、告警规则 |
| **具体码（枚举）** | `E_AUTH_EXPIRED`、`E_RATE_LIMITED` | API_SPEC.md §结构化错误分类 | MCP 响应中的 error_code 字段 |

前缀是具体码的分组。新增错误码时，必须在 API_SPEC 中定义具体码，并确保其前缀在 OBSERVABILITY 的分类中有覆盖。
