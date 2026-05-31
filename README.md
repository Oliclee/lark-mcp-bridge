# lark-mcp-bridge

飞书 CLI → MCP Bridge：将 [lark-cli](https://github.com/larksuite/cli) 能力以 MCP tools 形式暴露给 AI Agent。

## 功能

- **5 个手工 shortcut tool**：消息发送、日程查询、多维表格搜索、文档读取、联系人搜索
- **1 个复合 tool**：预约会议（查空闲 → 找会议室 → 创建日程）
- **动态发现**：自动解析 lark-cli 219 个 API 操作，按需暴露
- **渐进式暴露**：默认只暴露精选 tool，Agent 通过 `lark.discover` 按域查询更多
- **安全过滤**：白名单/黑名单机制，破坏性操作自动拦截
- **结构化错误**：每个错误包含 recovery_hint，告诉 Agent 如何修复
- **审计日志**：可选记录所有 tool 调用（支持脱敏）

## 快速开始

### 前置条件

- Python 3.12+
- [lark-cli](https://github.com/larksuite/cli) >= 1.0.43 已安装并完成认证
- [uv](https://docs.astral.sh/uv/) 已安装

### 安装

```bash
git clone https://github.com/loveseal/lark-mcp-bridge.git
cd lark-mcp-bridge
conda create -n lark-mcp-bridge python=3.12 -y
uv pip install --python /path/to/envs/lark-mcp-bridge/bin/python -e ".[dev]"
```

### 验证

```bash
conda run -n lark-mcp-bridge pytest
conda run -n lark-mcp-bridge lark-mcp-bridge  # Ctrl+C 退出
```

### 在 Amazon Quick Desktop 中使用

Settings → Capabilities → MCP → + Add MCP → Local：

| 字段 | 值 |
|------|-----|
| Command | `/path/to/envs/lark-mcp-bridge/bin/python` |
| Arguments | `-m lark_mcp_bridge.server` |

## 可用 Tool

| Tool | 描述 |
|------|------|
| `lark.im.messages-send` | 发送消息（text/markdown，支持 chat_id 或 user_id） |
| `lark.calendar.agenda` | 查看日历日程 |
| `lark.calendar.schedule-meeting` | 预约会议（复合 tool，自动编排多步） |
| `lark.base.record-search` | 搜索多维表格记录 |
| `lark.docs.fetch` | 读取飞书文档 |
| `lark.contact.search-user` | 搜索联系人 |
| `lark.discover` | 按域查询所有可用 API 操作 |
| `lark.identity` | 查看当前登录身份 |
| `lark.permissions` | 查看已授权 scope |
| `lark.domains` | 查看可用域概览 |

## 配置

通过环境变量配置（前缀 `LARK_MCP_`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LARK_MCP_TIMEOUT` | `30` | 子进程超时秒数 |
| `LARK_MCP_LOG_LEVEL` | `INFO` | 日志级别 |
| `LARK_MCP_LOG_FORMAT` | `json` | 日志格式（json/text） |
| `LARK_MCP_AUDIT_LOG` | (disabled) | 审计日志路径 |
| `LARK_MCP_NO_CACHE` | `false` | 禁用 discovery 缓存 |

完整配置见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

安全策略配置见 [lark-mcp-bridge.toml.example](lark-mcp-bridge.toml.example)。

## 架构

```
Amazon Quick → stdio → lark-mcp-bridge → subprocess → lark-cli → 飞书 API
```

四层架构：
- **L1 原子 tool**：自动从 lark-cli schema 生成
- **L2 复合 tool**：手工编排多步工作流
- **L3 Prompt**：领域知识按需注入
- **L4 智能引导**：description + examples + hints

详细设计见 [docs/PROJECT_DESIGN.md](docs/PROJECT_DESIGN.md)。

## 开发

```bash
# 运行测试
conda run -n lark-mcp-bridge pytest

# 运行测试（含覆盖率）
conda run -n lark-mcp-bridge pytest --cov=lark_mcp_bridge

# 性能基准
conda run -n lark-mcp-bridge python scripts/benchmark.py

# 审计日志分析
conda run -n lark-mcp-bridge python scripts/analyze_audit.py
```

## 许可证

[MIT](LICENSE)
