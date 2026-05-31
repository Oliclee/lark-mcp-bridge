# lark-mcp-bridge

飞书 CLI → MCP Bridge：将 `lark-cli` 能力以 MCP tools 形式暴露给 AI Agent（Amazon Quick）。

## 快速开始

### 前置条件

- Python 3.12+
- [lark-cli](https://github.com/larksuite/cli) 已安装并完成认证
- [uv](https://docs.astral.sh/uv/) 已安装

### 安装

```bash
conda create -n lark-mcp-bridge python=3.12
conda activate lark-mcp-bridge
uv pip install -e ".[dev]"
```

### 运行

```bash
python -m lark_mcp_bridge.server
```

### 在 Amazon Quick Desktop 中使用

Settings → Capabilities → MCP → Add Local：
- Command: `python`
- Arguments: `-m lark_mcp_bridge.server`

### 测试

```bash
pytest
```

## 文档

详细设计文档见 [docs/INDEX.md](docs/INDEX.md)。

## 许可证

MIT
