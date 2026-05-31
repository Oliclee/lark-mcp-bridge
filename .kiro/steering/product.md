# 产品概述：lark-mcp-bridge

一个 Python MCP（Model Context Protocol）桥接服务，将官方 `lark-cli`（飞书 CLI）作为子进程启动，并将其能力以 MCP tools 形式暴露给 AI Agent（主要是 Amazon Quick）。

## 核心功能

- 启动 `lark-cli` 作为子进程
- 动态发现 CLI 可用命令，自动注册为 MCP tools
- 提供复合 tool，编排多步工作流（如预约会议）
- 注入领域知识 Prompt，教 Agent *如何* 有效使用 tools
- 通过白名单/黑名单机制实施安全过滤

## 设计哲学

- **四层架构**：L1 原子 tool（CLI 自动生成）、L2 复合 tool（手工编排）、L3 Prompt（领域知识）、L4 智能引导（description + examples + hints）
- **渐进式暴露**：默认只暴露精选子集，Agent 通过 `lark:discover` meta-tool 按需发现更多
- **可执行错误**：每个错误都包含 `recovery_hint`，告诉 Agent 如何修复
- **Token 效率**：最小化 context 消耗；复合 tool 隐藏中间结果

## 当前状态

预实现阶段（设计/文档阶段）。源代码尚未编写。项目处于 Roadmap 的 Phase 0。

## 目标部署方式

本地 stdio 模式，由 Amazon Quick Desktop 管理进程生命周期。HTTP streaming 模式计划在 Phase 4 实现。
