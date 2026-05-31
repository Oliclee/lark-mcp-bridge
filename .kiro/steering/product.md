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

Phase 4（生产化）已完成。Phase 5（发布）进行中。

已实现：5 个手工 shortcut tool + 1 个 composite tool + discover 元工具 + 动态发现（219 API）+ 白名单安全 + 结构化错误 + 审计日志 + 启动预检。

## 下一迭代：Shortcut 扩展（Phase 5.1）

**目标**：对齐 lark-cli 官方 20 个 AI Agent Skill 的覆盖域，补齐缺失的 9 个域的 shortcut tool，提升开箱体验。

**原则**：
- 每个新 shortcut 对应 lark-cli 的一个 `+shortcut` 命令
- 遵循现有命名规范：`lark.{domain}.{action}`
- 需实际测试 lark-cli 对应命令的输出格式兼容性
- 完成后同步更新 `docs/API_SPEC.md` 和 README 工具表格

## 目标部署方式

本地 stdio 模式，由 Amazon Quick Desktop 管理进程生命周期。HTTP streaming 模式计划在 Phase 4 实现。
