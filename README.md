# lark-mcp-bridge

[![PyPI](https://img.shields.io/pypi/v/lark-mcp-bridge)](https://pypi.org/project/lark-mcp-bridge/)
[![Python](https://img.shields.io/pypi/pyversions/lark-mcp-bridge)](https://pypi.org/project/lark-mcp-bridge/)
[![License](https://img.shields.io/github/license/Oliclee/lark-mcp-bridge)](LICENSE)

将 [lark-cli](https://github.com/larksuite/cli)（飞书/Lark 官方 CLI）封装为 [MCP](https://modelcontextprotocol.io/) Server，使 AI 助手能够操作飞书。

支持飞书（中国版）和 Lark（国际版），取决于 lark-cli 配置。当前仅在飞书环境下验证。

## 为什么选择 lark-mcp-bridge

## 特点

- **零开发者门槛** — 不需要创建飞书开放平台应用、不需要 App ID/Secret、不需要手动配置权限。`lark-cli auth login` 一次登录即用，和网页版飞书同等权限
- **全域覆盖** — 不仅是文档，消息、日历、多维表格、电子表格、邮件、任务、云空间、知识库、会议等 14 个域 219 个 API 全部可用
- **Agent 自主探索** — Agent 通过 `lark.discover` 动态发现任意域的操作，每个操作提供完整 JSON Schema（参数名、类型、枚举、必填），Agent 不需要猜参数
- **安全可控** — 白名单策略 + 风险分级 + 破坏性操作需确认 + 审计日志
- **结构化错误** — 分类错误码（认证过期、限流、权限不足…）+ 中文恢复建议，Agent 能自主修复问题
- **上下文友好** — 渐进式暴露，schema 按需加载，不会一次性灌入大量工具定义占用 Agent 上下文窗口（实测节省 95% token）
- **标准 MCP 协议** — 兼容任何 MCP 客户端（Amazon Quick、Claude Desktop、Cursor、opencode 等）

## 背景

AI 工作助手（如 Amazon Quick、Claude Desktop、Anthropic Coworker）出于安全设计，不能直接执行 shell 命令或调用外部 API。它们通过 MCP 协议扩展能力——MCP 是这类助手连接外部服务的唯一通道。本项目让这类助手能够操作飞书。

对于有终端权限的编码工具（Claude Code、Cursor 等），同样可以通过 MCP 获得结构化的飞书操作能力，无需自行解析 CLI 输出。

## 前置条件

- Python 3.12+
- [lark-cli](https://github.com/larksuite/cli) 已安装并完成登录（`lark-cli auth login`）

## 安装

```bash
pip install lark-mcp-bridge
```

或开发模式：

```bash
git clone https://github.com/Oliclee/lark-mcp-bridge.git
cd lark-mcp-bridge
pip install -e ".[dev]"
```

## 使用

### 启动 Server

```bash
python -m lark_mcp_bridge.server
```

### MCP 客户端配置

所有客户端的配置本质相同：

```json
{
  "mcpServers": {
    "lark": {
      "command": "python",
      "args": ["-m", "lark_mcp_bridge.server"]
    }
  }
}
```

- **Amazon Quick Desktop**: Settings → Capabilities → MCP → Add Local
- **Claude Code / Claude Desktop**: `~/.claude/mcp.json`
- **Cursor**: Settings → MCP Servers → Add (type: command)
- **opencode**: `opencode.json`

## 工作原理

```
AI 客户端 ⇄ MCP (stdio) ⇄ lark-mcp-bridge ⇄ lark-cli ⇄ 飞书 API
```

bridge 不直接调用飞书 HTTP API。认证和 token 管理由 lark-cli 处理，你的 credential 不经过第三方。

### 内置工具

以下工具开箱即用，Agent 直接调用：

| 工具 | 功能 | 示例指令 |
|------|------|----------|
| `lark.im.messages-send` | 发送消息 | "给张三发一条消息说明天开会" |
| `lark.calendar.agenda` | 查看日程 | "看看我今天有什么安排" |
| `lark.calendar.schedule-meeting` | 预约会议 | "帮我约明天下午3点和小明的会" |
| `lark.base.record-search` | 搜索多维表格 | "在项目表里搜索状态为进行中的记录" |
| `lark.docs.fetch` | 读取文档 | "读取这个文档的内容：https://feishu.cn/docx/xxx" |
| `lark.contact.search-user` | 搜索联系人 | "帮我找一下 Alice 的飞书账号" |
| `lark.sheets.read` | 读取电子表格 | "读取这个表格 A1:D10 的数据" |
| `lark.sheets.write` | 写入电子表格 | "把这些数据写入表格的 A1 单元格" |
| `lark.task.list` | 查看任务列表 | "看看我有哪些未完成的任务" |
| `lark.task.create` | 创建任务 | "创建一个任务：下周五前完成报告" |
| `lark.mail.send` | 发送邮件 | "给 alice@company.com 发一封关于项目进度的邮件" |
| `lark.mail.list` | 查看邮件列表 | "看看今天收到了哪些邮件" |
| `lark.drive.upload` | 上传文件 | "把 report.pdf 上传到云空间" |
| `lark.drive.download` | 下载文件 | "下载这个文件到本地" |
| `lark.wiki.search` | 搜索知识库 | "在知识库里搜索 API 设计规范" |
| `lark.wiki.get-node` | 获取知识库节点 | "获取这个知识库页面的内容" |
| `lark.vc.search` | 搜索会议记录 | "找一下上周的产品评审会议" |
| `lark.vc.notes` | 获取会议纪要 | "获取这个会议的纪要" |
| `lark.minutes.search` | 搜索妙记 | "搜索包含'预算'的会议录音" |

### 动态发现：Agent 自主探索，无需猜测

上面 19 个是精选的高频工具。但飞书有 14 个域、219 个 API——Agent 不需要记住它们，也不需要猜参数。

Agent 调用 `lark.discover(domain="mail")` 即可获取该域下所有操作的完整定义（参数名、类型、是否必填、示例值）。这意味着：

- **不受固定工具列表限制** — 即使某个操作没有内置 shortcut，Agent 也能通过 discover 找到并使用
- **不需要猜参数** — 每个操作都有完整的 JSON Schema 定义
- **不需要等版本更新** — lark-cli 新增的命令自动可发现

```
用户: "帮我查看 OKR 进度"
Agent: → lark.discover(domain="okr") → 发现 23 个可用操作 → 选择合适的调用
```

## 开发

```bash
pip install -e ".[dev]"
pytest
```

详细设计文档见 [docs/INDEX.md](docs/INDEX.md)。

## 免责声明

本项目为社区开源项目，与飞书/Lark 及字节跳动无官方关联。"Lark"和"飞书"是字节跳动的注册商标。

**关于安全防护**：本项目内置了白名单策略、风险分级和破坏性操作确认机制，尽力防止误操作。但 AI 助手的行为由模型推理驱动，无法保证 100% 符合用户预期。使用者应：

- 对 AI 助手执行的写入、修改和删除操作保持关注
- 在重要环境中使用前，先在测试环境验证
- 理解本工具以用户自身身份执行操作，后果等同于用户本人操作

使用本工具即表示你理解并接受：项目作者不对因使用本工具导致的任何数据丢失、误操作或其他损害承担责任。使用时请遵守[飞书开放平台使用条款](https://open.feishu.cn/document/common-capabilities/terms-of-service)。

## 许可证

MIT
