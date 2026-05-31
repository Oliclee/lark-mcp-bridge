# ROADMAP

> 文档索引见 [INDEX.md](./INDEX.md)

## Phase 0: 项目初始化 ✅

**目标**：代码仓库和生产工程就绪

- [x] GitHub 仓库创建
- [x] `pyproject.toml` + conda env 配置
- [x] `src/lark_mcp_bridge/` 基础骨架
- [x] `pytest` 测试框架搭建
- [x] `config.py` 统一配置模型（pydantic-settings）

## Phase 1: MVP（固定 tool）✅

**目标**：最小可用，验证架构可行性

- [x] 5 个固定 MCP tool 手动注册
  - `lark.im.messages-send` — 发送消息（支持 chat_id/user_id 二选一，text/markdown 二选一）
  - `lark.calendar.agenda` — 查看日程
  - `lark.base.record-search` — 搜索多维表格记录（支持字段过滤和分页）
  - `lark.docs.fetch` — 读取文档（支持 URL 或 token）
  - `lark.contact.search-user` — 搜索联系人（支持分页）
- [x] FastMCP stdio transport
- [x] 基础 subprocess 执行器 + 超时控制
- [x] 在 Amazon Quick 中成功调用并返回结果
- [x] 基础结构化错误处理（含业务层 ok:false 检测）

## Phase 1.5: 端到端验证 ✅

**目标**：验证四层架构有效性，建立 Agent 使用成功率 baseline

- [x] 编写 1 个 composite tool（`lark.calendar.schedule-meeting`）
- [x] 编写 1 个 Prompt（`lark-calendar-workflow`）
- [x] 端到端测试：Agent 完成"查日程→找联系人→预约会议"完整流程
- [ ] 记录 Agent 调用成功率、平均 tool call 次数
- [ ] 验证 Prompt 引导是否有效减少 Agent 试错

## Phase 2: 动态发现 ✅

**目标**：自动跟随 lark-cli 版本，无需手动维护 tool 列表

- [x] `discovery.py`：解析 lark-cli schema --format json（219 个 tool）
- [x] ToolDefinition 数据模型（name、risk_level、identity、scopes）
- [x] `filters.py`：白名单优先机制，扩展至 16 个域
- [x] 参数类型自动映射（inputSchema 清理 + yes 字段移除）
- [x] Discovery 结果缓存至本地 JSON
- [x] `lark.discover` meta-tool 实现（渐进式暴露，按域查询）
- [x] `resources.py`：MCP Resources 层 + 等价 tool（identity / permissions / domains）

## Phase 2.5: 性能基准 🆕

**目标**：建立性能 baseline，识别瓶颈

- [ ] 测量 discovery 完整耗时（含缓存 vs 无缓存）
- [ ] 测量单次 tool call 延迟分布（P50/P95/P99）
- [ ] 测量 subprocess 冷启动开销
- [ ] 确定是否需要进程池（Phase 4 决策依据）
- [ ] 记录 MCP tool list token 消耗（验证渐进式暴露效果）

## Phase 3: 手动增强

**目标**：提升 Agent 使用体验

- [ ] 高频 tool 覆写 description（中文 + example）
- [ ] 结构化错误信息（区分 auth error / network error / logic error）
- [ ] 高风险操作二次确认标记（MCP annotation `destructiveHint`）
- [ ] `audit.py`：审计日志（参见 [SECURITY §3](./SECURITY.md#3-审计日志)）
- [ ] Identity 精细化标记（tool description 中声明所需身份）

## Phase 3.5: 用户反馈循环 🆕

**目标**：数据驱动的 Prompt/tool 迭代

- [ ] 记录 Agent tool call 成功率 / 失败模式
- [ ] 识别高频失败场景 → 新增 composite tool 或 Prompt
- [ ] 收集 description 改进前后的成功率对比
- [ ] 根据使用数据调整 `expose: always` 的 tool 列表

## Phase 4: SSE + 生产化

**目标**：可部署

- [ ] SSE transport 支持
- [ ] Dockerfile
- [ ] 健康检查端点（参见 [OBSERVABILITY](./OBSERVABILITY.md#1-健康检查)）
- [ ] `/metrics` Prometheus 指标端点
- [ ] 启动预检（lark-cli 安装/认证状态）
- [ ] 进程池模式（`LARK_MCP_POOL_SIZE`，基于 Phase 2.5 数据决策）
- [ ] 启动 Banner 输出诊断信息
- [ ] 结构化日志（JSON 格式）

## Phase 5: 发布

**目标**：开源可用

- [ ] PyPI 发布
- [ ] Amazon Quick 配置文档
- [ ] README + 快速开始指南
- [ ] CI（lint + test）
- [ ] `lark-mcp-bridge.toml` 配置文件模板
- [ ] `scripts/sync_prompts.py` Prompt 同步脚本
