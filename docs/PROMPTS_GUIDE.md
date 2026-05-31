# PROMPTS GUIDE: Prompt 维护指南

> 文档索引见 [INDEX.md](./INDEX.md)

---

## 1. Prompt 层在系统中的角色

参见 [PROJECT_DESIGN §2.4 四层架构](./PROJECT_DESIGN.md#24-tool-注册策略四层架构)

Prompt（L3 层）的职责是**教 Agent "怎么用"**——不是告诉它有什么 tool，而是告诉它在什么场景下、以什么顺序、注意什么约束来使用 tool。

```
Agent 收到飞书相关请求 → list_prompts() → 发现相关 prompt
→ get_prompt("lark-calendar-workflow") → 获得完整使用指南
→ 根据指南逐步调用 tool
```

---

## 2. Prompt 来源

### 2.1 主要来源：lark-cli SKILL.md

lark-cli 为每个域维护一份 SKILL.md（约 26 个域），包含：
- 意图分支逻辑（用户说 X → 应该调用 Y）
- 默认值补充规则（缺少参数时如何推断）
- 冲突处理策略（时间冲突时如何追问）
- 常见错误恢复指南

### 2.2 补充来源

| 来源 | 用途 |
|---|---|
| 人工编写 | 跨域场景化 Prompt（如会议预约全流程） |
| 使用日志 | 高频失败模式 → 新增 Prompt 规避 |
| 社区反馈 | 开源后用户贡献的最佳实践 |

---

## 3. 本地维护策略

### 3.1 目录结构

```
src/lark_mcp_bridge/
└── prompts/
    ├── __init__.py           # Prompt 注册入口
    ├── _base.py              # Prompt 基类/格式工具
    ├── calendar.md           # 日历域 Prompt
    ├── im.md                 # 消息域 Prompt
    ├── base.md               # 多维表格域 Prompt
    ├── doc.md                # 文档域 Prompt
    ├── contact.md            # 联系人域 Prompt
    ├── task.md               # 任务域 Prompt
    └── scenarios/            # 跨域场景化 Prompt
        ├── meeting-scheduling.md
        ├── document-sharing.md
        └── task-delegation.md
```

### 3.2 不直接运行时解析 lark-cli SKILL.md

原因：
- lark-cli SKILL.md 格式可能随版本变化
- bridge 需要增强/修改原始内容（增加中文说明、补充 examples）
- 本地副本允许版本控制和 review

### 3.3 同步脚本

```bash
# 从 lark-cli 最新版本同步 SKILL.md → 本地 prompts/
python scripts/sync_prompts.py

# 流程：
# 1. 读取 lark-cli 各域的 SKILL.md
# 2. 转换为 bridge 的 Prompt 格式
# 3. 与本地副本 diff
# 4. 输出变更报告，人工确认后合入
```

---

## 4. Prompt 编写规范

### 4.1 文件格式

每个 Prompt 文件为 Markdown，顶部使用 YAML frontmatter：

```markdown
---
name: lark-calendar-workflow
description: 飞书日历操作完整指南——查询日程、创建会议、处理冲突
domains: [calendar, contact]
tools_referenced: [lark.calendar.agenda, lark.calendar.create, lark.contact.search-user]
---

## 使用场景

当用户请求涉及日历操作时加载本 Prompt。

## 意图分支

1. **查询日程**：用户想知道某天/某周的安排
   → 调用 `lark.calendar.agenda`
   → 默认范围：今天起 7 天

2. **创建会议**：用户想预约会议
   → 先调用 `lark.calendar.agenda` 检查冲突
   → 再调用 `lark.contact.search-user` 确认参会人
   → 最后调用 `lark.calendar.create`

3. **修改/取消**：用户想变更已有日程
   → ...

## 默认值规则

| 参数 | 默认值 | 说明 |
|---|---|---|
| duration | 30min | 未指定时长时 |
| reminder | 15min before | 未指定提醒时 |
| timezone | 用户本地时区 | 从 lark-cli config 获取 |

## 常见错误恢复

| 错误 | 恢复策略 |
|---|---|
| "time conflict" | 展示冲突详情，询问是否仍要创建 |
| "user not found" | 尝试模糊搜索，展示候选列表 |
```

### 4.2 编写原则

1. **意图优先**：先列出用户可能的意图分支，再给出对应的 tool 调用序列
2. **填补 Agent 推理盲区**：重点写 Agent 自己推理不出的隐含规则（如默认值、业务约束）
3. **可执行的错误恢复**：不只列错误码，要给出 Agent 可自主执行的恢复步骤
4. **精简**：一个 Prompt 控制在 2000 tokens 以内（避免占用过多 context）
5. **中英双语**：description 用中文，tool name/参数用英文原名

---

## 5. 场景化 Prompt

### 5.1 什么时候需要场景化 Prompt

当一个业务流程跨越 2 个以上域时，单域 Prompt 无法覆盖完整流程。

### 5.2 已规划场景

| 场景 | 涉及域 | 典型用户指令 |
|---|---|---|
| `meeting-scheduling` | calendar + contact + im | "帮我约一下周三和小明的会" |
| `document-sharing` | drive + im + contact | "把这个文档分享给产品组" |
| `task-delegation` | task + im + contact | "给小红派个任务，下周五前完成报告" |

### 5.3 场景 Prompt 与 Composite Tool 的关系

- **Composite Tool**（L2）：在 bridge 内部编排，Agent 看到的是单个 tool，中间结果不进 context
- **场景 Prompt**（L3）：教 Agent 自己编排多个 tool，Agent 看到每步结果并做判断

**选择标准**：
- 流程固定、不需要中间判断 → Composite Tool
- 流程有分支、需要 Agent 根据中间结果决策 → 场景 Prompt

---

## 6. 维护工作流

### 6.1 新增 Prompt

1. 在 `src/lark_mcp_bridge/prompts/` 下创建 `.md` 文件
2. 按 §4.1 格式编写
3. 在 `__init__.py` 中注册
4. 运行测试验证加载成功
5. PR review

### 6.2 更新已有 Prompt

1. 运行 `scripts/sync_prompts.py` 查看上游变化
2. 评估是否需要合入
3. 本地修改 + 测试
4. 更新 CHANGELOG

### 6.3 质量检查清单

- [ ] frontmatter 完整（name, description, domains, tools_referenced）
- [ ] 意图分支覆盖主要场景
- [ ] 引用的 tool 名称在 API_SPEC 中存在
- [ ] Token 估算 < 2000
- [ ] 错误恢复策略可执行（不是空泛的"请重试"）
