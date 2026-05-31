# DEPLOYMENT

> 文档索引见 [INDEX.md](./INDEX.md)

## 前置条件

### 1. 安装并认证 lark-cli

```bash
npx @larksuite/cli@latest install
```

创建飞书应用并授权：

```bash
lark-cli config init --new
lark-cli auth login --recommend
```

验证可用：

```bash
lark-cli calendar +agenda
```

### 2. Python 环境

```bash
conda create -n lark-mcp-bridge python=3.12
conda activate lark-mcp-bridge
```

## 安装

### 开发模式（推荐）

```bash
git clone <repo-url>
cd lark-mcp-bridge
uv pip install --system -e ".[dev]"
```

### 通过 PyPI（正式发布后）

```bash
# 方式 1：全局安装
uv pip install --system lark-mcp-bridge

# 方式 2：使用 uvx 免安装运行（推荐）
uvx lark-mcp-bridge
```

## 启动方式

安装后有三种等价的启动方式：

```bash
# 1. Console script（推荐，最简洁）
lark-mcp-bridge

# 2. 模块方式
python -m lark_mcp_bridge.server

# 3. uvx 免安装（PyPI 发布后可用）
uvx lark-mcp-bridge
```

所有方式默认使用 stdio transport（stdin/stdout JSON-RPC）。

## 在 Amazon Quick Desktop 中使用

### 方式 1：Console script（推荐）

Settings → Capabilities → MCP → + Add MCP → Local：

| 字段 | 值 |
|------|-----|
| Name | `Lark MCP Bridge` |
| Command | `lark-mcp-bridge` |
| Arguments | （留空） |
| Description | `飞书集成——消息、日历、文档、多维表格等` |

> 如果 Quick 找不到命令，使用完整路径：`/path/to/python所在目录/lark-mcp-bridge`

### 方式 2：Python 完整路径（环境隔离更明确）

| 字段 | 值 |
|------|-----|
| Command | `/Users/loveseal/miniforge3/bin/python` |
| Arguments | `-m lark_mcp_bridge.server` |

### 方式 3：uvx（PyPI 发布后，零安装）

| 字段 | 值 |
|------|-----|
| Command | `uvx` |
| Arguments | `lark-mcp-bridge` |

Quick 会自动管理进程的启动和停止。

### 不推荐：conda run

`conda run` 存在信号传递不可靠、启动开销大、stderr 可能被污染等问题，不建议用于 MCP server 启动。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LARK_MCP_PORT` | `8080` | HTTP 监听端口（streamable-http 模式） |
| `LARK_MCP_HOST` | `127.0.0.1` | 绑定地址 |
| `LARK_MCP_TRANSPORT` | `stdio` | 传输协议 (stdio / streamable-http / sse) |
| `LARK_CLI_PATH` | `lark-cli` | lark-cli 可执行文件路径 |
| `LARK_MCP_TIMEOUT` | `30` | 子进程超时秒数 |
| `LARK_MCP_POOL_SIZE` | `0` | 进程池大小（0=禁用，使用 subprocess.run） |
| `LARK_MCP_AUDIT_LOG` | (disabled) | 审计日志路径（设置后启用审计） |
| `LARK_MCP_AUDIT_LEVEL` | `write` | 审计级别：read / write / all |
| `LARK_MCP_LOG_LEVEL` | `INFO` | 日志级别 |
| `LARK_MCP_LOG_FORMAT` | `json` | 日志格式：json / text |
| `LARK_MCP_LOG_FILE` | (stderr) | 日志输出路径 |
| `LARK_MCP_CACHE_DIR` | `~/.cache/lark-mcp-bridge` | Discovery 缓存目录 |
| `LARK_MCP_NO_CACHE` | `false` | 禁用缓存（每次启动重新 discovery） |

## 配置文件

对于安全策略等复杂配置，推荐使用 `lark-mcp-bridge.toml`：

```bash
# bridge 按以下优先级查找配置：
# 1. --config 命令行参数指定路径
# 2. 当前目录下的 lark-mcp-bridge.toml
# 3. ~/.config/lark-mcp-bridge/config.toml
```

配置文件格式详见 [SECURITY.md §2.4](./SECURITY.md#24-白名单配置格式)。

## MCP Tool 命名规范

Tool 名称使用 `.` 作为分隔符（符合 MCP SEP-986 规范）：

```
lark.<domain>.<action>

示例：
  lark.im.messages-send
  lark.calendar.agenda
  lark.base.record-search
  lark.docs.fetch
  lark.contact.search-user
```

## 验证安装

```bash
# 确认 lark-cli 可用
lark-cli --version    # >= 1.0.43
lark-cli auth status  # identities.user.status 或 bot.status 为 ready

# 确认 bridge 可启动（Ctrl+C 退出）
lark-mcp-bridge
# 应该静默等待 stdin 输入（stdio 模式），无报错
```

## Docker（Phase 4+）

```bash
docker build -t lark-mcp-bridge .
docker run -p 8080:8080 lark-mcp-bridge
```
