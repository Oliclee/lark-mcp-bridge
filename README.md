# lark-mcp-bridge

将 [lark-cli](https://github.com/larksuite/cli)（飞书/Lark 官方 CLI）封装为 [MCP](https://modelcontextprotocol.io/) Server，使 AI 助手能够操作飞书。

支持飞书（中国版）和 Lark（国际版），取决于 lark-cli 配置。当前仅在飞书环境下验证。

## 背景

AI 工作助手（如 Amazon Quick、Claude Desktop、Anthropic Coworker）出于安全设计，不能直接执行 shell 命令或调用外部 API。它们通过 MCP 协议扩展能力——MCP 是这类助手连接外部服务的唯一通道。本项目让这类助手能够操作飞书。

对于有终端权限的编码工具（Claude Code、Cursor 等），同样可以通过 MCP 获得结构化的飞书操作能力，无需自行解析 CLI 输出。

## 特点

- **无需创建飞书应用** — 复用 lark-cli 的个人登录态，无需 App ID/Secret
- **14 个域、219 个 API** — 通过 `lark.discover` 元工具让 Agent 按需探索，不受固定工具列表限制
- **安全白名单** — 默认拒绝未审核操作，风险分级，破坏性操作需确认
- **结构化交互** — 每个操作提供完整 JSON Schema（参数名、类型、枚举、必填），Agent 不需要猜参数
- **统一错误处理** — 分类错误码（认证过期、限流、权限不足…）+ 中文恢复建议，而非裸 stderr
- **上下文友好** — schema 按需加载，不会一次性灌入大量 help 文本占用 Agent 上下文窗口
- **标准 MCP 协议** — 兼容任何 MCP 客户端（Amazon Quick、Claude、Cursor、opencode 等）

## 前置条件

- Python 3.12+
- [lark-cli](https://github.com/larksuite/cli) 已安装并完成登录（`lark-cli auth login`）

## 安装

```bash
pip install lark-mcp-bridge

# 或开发模式
git clone https://github.com/YOUR_USERNAME/lark-mcp-bridge.git
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

| 工具 | 功能 |
|------|------|
| `lark.im.messages-send` | 发送消息 |
| `lark.calendar.agenda` | 查看日程 |
| `lark.calendar.schedule-meeting` | 预约会议 |
| `lark.base.record-search` | 搜索多维表格 |
| `lark.docs.fetch` | 读取文档 |
| `lark.contact.search-user` | 搜索联系人 |
| `lark.sheets.read` | 读取电子表格数据 |
| `lark.sheets.write` | 写入电子表格数据 |
| `lark.task.list` | 查看我的任务列表 |
| `lark.task.create` | 创建任务 |
| `lark.mail.send` | 发送邮件 |
| `lark.mail.list` | 查看邮件列表 |
| `lark.drive.upload` | 上传文件到云空间 |
| `lark.drive.download` | 下载云空间文件 |
| `lark.wiki.search` | 搜索文档和知识库 |
| `lark.wiki.get-node` | 获取知识库节点详情 |
| `lark.discover` | 探索任意域的可用操作 |
| `lark.identity` | 查看当前登录身份 |
| `lark.permissions` | 查看已授权 scope |
| `lark.domains` | 查看所有可用域 |

### 动态发现

当内置工具不满足需求时，Agent 可调用 `lark.discover(domain="mail")` 查询该域下所有可用 API 的完整 schema（参数、类型、示例），然后直接调用——无需更新 bridge 版本。

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
