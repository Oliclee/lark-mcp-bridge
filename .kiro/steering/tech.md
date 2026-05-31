# 技术栈

## 语言与运行时

- **Python 3.12**（conda 环境：`lark-mcp-bridge`）
- 包格式：`src/` 布局 + `pyproject.toml`

## 核心依赖

| 包 | 用途 |
|---|------|
| `mcp` >= 1.27 | FastMCP server 框架（tools、prompts、resources、HTTP streaming + stdio transport） |
| `pydantic-settings` | 统一配置模型（环境变量 / .env / toml） |
| `lark-cli`（外部） | 飞书 CLI，以子进程方式调用——不是 Python 依赖 |

## 开发依赖

| 包 | 用途 |
|---|------|
| `pytest` | 测试运行器 |
| `pytest-cov` | 覆盖率报告 |
| `pytest-asyncio` | 异步测试支持（FastMCP 是 async 的） |

## 构建与打包

- 构建系统：`pyproject.toml`（PEP 621）
- 开发安装：`uv pip install --system -e ".[dev]"`
- 生产安装：`uv pip install --system lark-mcp-bridge`（未来 PyPI）
- 入口：`python -m lark_mcp_bridge.server`

## 常用命令

```bash
# 创建环境（仅首次）
conda create -n lark-mcp-bridge python=3.12 -y

# 安装依赖（指定目标环境的 Python）
uv pip install --python /Users/loveseal/miniforge3/envs/lark-mcp-bridge/bin/python -e ".[dev]"

# 运行测试
conda run -n lark-mcp-bridge pytest

# 运行测试（含覆盖率）
conda run -n lark-mcp-bridge pytest --cov=lark_mcp_bridge --cov-report=xml

# 运行 bridge（stdio 模式）
conda run -n lark-mcp-bridge lark-mcp-bridge

# 录制测试 fixture（需要已认证的 lark-cli）
conda run -n lark-mcp-bridge bash scripts/record_fixtures.sh
```

## 包安装规则

在 conda 环境中使用 `uv pip install --python <环境Python路径>` 安装包。这比 `--system` 更精确，避免装到错误的环境。

当前项目环境 Python 路径：`/Users/loveseal/miniforge3/envs/lark-mcp-bridge/bin/python`

Kiro 终端无法 `conda activate`，所以运行命令统一使用 `conda run -n lark-mcp-bridge <command>` 前缀。

## 配置

- 环境变量以 `LARK_MCP_` 为前缀（如 `LARK_MCP_TIMEOUT`、`LARK_MCP_LOG_LEVEL`）
- 可选 TOML 配置文件：`lark-mcp-bridge.toml`
- 配置查找顺序：`--config` 参数 → `./lark-mcp-bridge.toml` → `~/.config/lark-mcp-bridge/config.toml`

## 传输协议

- **stdio**（当前/默认）：通过 stdin/stdout 的 JSON-RPC，由 Amazon Quick Desktop 管理
- **streamable-http**（Phase 4）：localhost HTTP streaming

## 关键约束

所有日志和调试输出必须走 stderr。stdout 专用于 MCP JSON-RPC 协议消息，严禁污染。

## 文档同步规则

当修改 `src/` 下的源码时，必须同步检查并更新 `docs/` 中的相关文档（如 API_SPEC、PROJECT_DESIGN、DEPLOYMENT 等）。所有生成的文档使用中文。

## 发布就绪原则

开发过程中提前考虑正式发布的需求：
- 新增功能时同步添加对应的冒烟测试（验证 entry point、import、基本可用性）
- CLI 接口变更时同步更新 DEPLOYMENT.md 中的使用说明
- 确保 `lark-mcp-bridge` console script 始终可用
