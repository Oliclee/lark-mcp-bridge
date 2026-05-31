# API SPEC: MCP Tool 接口规范

> 文档索引见 [INDEX.md](./INDEX.md)

## 语言策略

基于 [EVALUATION §3.6](./EVALUATION.md#36-语言策略分析) 的决策：

| 字段 | 语言 | 示例 |
|---|---|---|
| tool name | 英文 | `lark.calendar.agenda` |
| tool description | 中文 | `"查看日历日程，默认展示今天的安排"` |
| 参数 description | 中文 | `"开始时间（ISO 8601 格式，默认：今天起始）"` |
| error message | 中文 | `"此操作需要 user 身份"` |
| recovery_hint | 中文 | `"请运行 lark-cli auth login 重新认证"` |

---

## MCP Tool 定义

bridge 将每个 lark-cli 命令注册为一个 MCP tool，遵循 MCP 标准 tool schema：

```json
{
  "name": "lark.im.messages-send",
  "description": "发送消息到指定会话或用户。支持 text、markdown、post、image 等消息类型。chat_id 和 user_id 二选一。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": { "type": "string", "description": "纯文本消息内容（与 markdown 二选一）" },
      "chatId": { "type": "string", "description": "会话 ID（oc_xxx），与 user_id 互斥" },
      "userId": { "type": "string", "description": "用户 open_id（ou_xxx），与 chat_id 互斥" },
      "markdown": { "type": "string", "description": "markdown 格式消息（与 text 二选一）" },
      "msgType": { "type": "string", "description": "消息类型，默认 text" }
    },
    "required": ["text"]
  }
}
```

## Tool 命名规则

```
lark.<domain>.<action>

domain = schema name 的第一个空格分隔词: im | calendar | base | docs | sheets | task | mail | contact | wiki | vc | approval | attendance | okr | drive | ...
action = schema name 剩余部分用 - 连接，. 替换为 -

转换逻辑（_name_to_mcp_tool_name）：
  "im chat.members create"     → "lark.im.chat-members-create"
  "calendar events patch"      → "lark.calendar.events-patch"
  "approval instances cancel"  → "lark.approval.instances-cancel"
  "im messages send"           → "lark.im.messages-send"
```

> **注意**：MCP 规范仅允许 tool name 包含 `A-Z a-z 0-9 _ - .`，因此使用 `.` 作为分隔符（非 `:`）。

---

## Phase 1 Tool 完整定义

### `lark.im.messages-send`

发送消息到指定会话或用户。支持 text、markdown、post、image 等消息类型。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `text` | string | ✅ | 纯文本消息内容（与 markdown 二选一） |
| `chatId` | string | ❌ | 会话 ID（oc_xxx），与 userId 互斥 |
| `userId` | string | ❌ | 用户 open_id（ou_xxx），与 chatId 互斥 |
| `markdown` | string | ❌ | markdown 格式消息（与 text 二选一） |
| `msgType` | string | ❌ | 消息类型，默认 `text` |

> chatId 和 userId 二选一，至少提供一个目标。

### `lark.calendar.agenda`

查看日历日程，默认展示今天的安排。可指定日期范围。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `startTime` | string | ❌ | 开始时间（ISO 8601 格式，默认：今天起始） |
| `endTime` | string | ❌ | 结束时间（ISO 8601 格式，默认：今天结束） |

### `lark.base.record-search`

搜索多维表格记录。根据关键词在指定表格中搜索。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `baseToken` | string | ✅ | 多维表格 Base Token |
| `tableId` | string | ✅ | 数据表 ID（tbl 开头）或表名 |
| `keyword` | string | ✅ | 搜索关键词 |
| `searchFields` | string | ❌ | 搜索字段列表（逗号分隔的字段名），不指定则搜索所有文本字段 |
| `selectFields` | string | ❌ | 返回字段列表（逗号分隔的字段名），不指定则返回所有字段 |
| `limit` | integer | ❌ | 返回记录数上限，1-200，默认 10 |

> 内部通过 `--json` 传递结构化搜索参数（searchFields/selectFields 转为数组）。

### `lark.docs.fetch`

读取飞书文档内容。支持通过文档 URL 或 token 获取。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `doc` | string | ✅ | 文档 URL 或 document token |

> 内部使用 `--api-version v2` 调用新版文档 API。

### `lark.contact.search-user`

搜索飞书联系人。支持按姓名、邮箱等关键词搜索用户。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | ✅ | 搜索关键词（姓名、邮箱等，最多 50 字符） |
| `pageSize` | integer | ❌ | 每页返回数量，1-30，默认 20 |

---

## 参数映射规则

lark-cli CLI flag → MCP tool parameter：

| CLI flag | MCP JSON Schema type |
|---|---|
| `--xxx-yyy <value>` | `"xxxYyy": { "type": "string" }` |
| `--int-flag <N>` | `"intFlag": { "type": "integer" }` |
| `--bool-flag` | `"boolFlag": { "type": "boolean" }` |

- flag 名去掉 `--`，kebab-case → camelCase
- 所有参数均为 optional（required 由 lark-cli 自行校验）
- `--format`、`--dry-run`、`--yes` 等 bridge 内部控制的 flag 不暴露

### inputSchema 清理规则

`discovery.py` 的 `_clean_input_schema()` 在注册前自动清理 schema：

| 清理项 | 原因 |
|---|---|
| 移除 `yes` 属性 | bridge 内部处理确认逻辑（高风险操作自动追加 `--yes`） |
| 从 `required` 数组中移除 `yes` | 保持 required 与 properties 一致 |

## Tool 返回值

bridge 透传 lark-cli 的 stdout。大多数 tool 通过 `--format json` 强制 JSON 输出；部分命令（如 `im +messages-send`）默认即为 JSON 格式，无需额外指定。lark-cli 输出格式为标准 JSON envelope：

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

调用失败时，bridge 返回 MCP error：

```json
{
  "isError": true,
  "content": [{
    "type": "text",
    "text": "<lark-cli stderr / error message>"
  }]
}
```

## MCP 协议层

| 项目 | 实现 |
|---|---|
| Transport | `streamable-http`（Phase 4 增加 SSE） |
| Protocol version | MCP 2025-11-25 |
| Session | 无状态（每次 tool call 独立子进程） |
| Tool list notification | 不支持（tool 列表静态，重启 bridge 生效） |

## 错误码映射

| lark-cli 行为 | MCP 行为 |
|---|---|
| 正常返回 (exit 0) | 返回 tool result，透传 stdout |
| 返回错误 (exit ≠ 0) | 返回 `isError: true`，透传 stderr |
| 子进程超时 | 返回 timeout error |
| lark-cli 未找到 | bridge 启动失败，不提供服务 |
| exit code 10 (高风险确认) | 标记为 MCP annotation `destructiveHint`，要求客户端二次确认后追加 `--yes` 重试 |

### 结构化错误分类

bridge 对 lark-cli 错误进行分类，返回结构化错误信息：

```json
{
  "isError": true,
  "content": [{
    "type": "text",
    "text": "{\"error_code\": \"E_AUTH_EXPIRED\", \"message\": \"OAuth token 已过期\", \"recovery_hint\": \"请运行 lark-cli auth login 重新认证后重试\"}"
  }]
}
```

**错误类型枚举**：

| error_code | 触发条件 | recovery_hint |
|---|---|---|
| `E_AUTH_EXPIRED` | lark-cli 返回 401/token expired | "请运行 `lark-cli auth login` 重新认证" |
| `E_AUTH_NO_LOGIN` | lark-cli 未登录 | "请先执行 `lark-cli auth login --recommend`" |
| `E_RATE_LIMITED` | lark-cli 返回 429 | "飞书 API 限流，请稍后重试。bridge 将在 {N}s 后自动重试" |
| `E_NOT_FOUND` | 资源不存在（404） | "未找到指定资源，请检查 ID 是否正确" |
| `E_PERMISSION_DENIED` | 权限不足（403） | "当前身份无权执行此操作。需要 {required_scope}" |
| `E_IDENTITY_MISMATCH` | 需要 user 身份但当前为 bot | "此操作需要 user 身份，请使用 identityAs: \"user\" 参数" |
| `E_TIMEOUT` | 子进程超时 | "命令执行超时（{timeout}s），可能是网络问题，请重试" |
| `E_CLI_NOT_FOUND` | lark-cli 不在 PATH 中 | "lark-cli 未安装或不在 PATH 中" |
| `E_CLI_ERROR` | lark-cli 内部错误 | "lark-cli 内部错误，请检查版本是否最新" |
| `E_BLOCKED` | 命令被安全策略拦截 | "此命令被安全策略禁止。详见 SECURITY.md" |

**自动重试逻辑**：

| error_code | 重试策略 |
|---|---|
| `E_RATE_LIMITED` | 指数退避，最多 3 次（1s → 2s → 4s） |
| `E_TIMEOUT` | 立即重试 1 次（可能是偶发网络抖动） |
| 其他 | 不重试，直接返回 Agent |

## MCP Tool Annotations

Tool 使用 MCP annotation 标记风险级别和属性：

```json
{
  "name": "lark.drive.delete",
  "annotations": {
    "destructiveHint": true,
    "readOnlyHint": false,
    "idempotentHint": false
  }
}
```

```json
{
  "name": "lark.calendar.agenda",
  "annotations": {
    "readOnlyHint": true,
    "idempotentHint": true
  }
}
```

## Composite Tool Schema 示例

复合 tool 的 inputSchema 包含 `input_examples` 便于 Agent 理解用法：

```json
{
  "name": "lark.calendar.schedule-meeting",
  "description": "预约会议（完整流程）：检查空闲时段 → 可选查找会议室 → 创建日程。不指定时间时自动查询最近空闲。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string", "description": "会议标题" },
      "attendees": {
        "type": "array",
        "items": { "type": "string" },
        "description": "参会人 open_id 列表（ou_xxx）"
      },
      "start": { "type": "string", "description": "开始时间（ISO 8601），不指定则自动查找最近空闲时段" },
      "end": { "type": "string", "description": "结束时间（ISO 8601），不指定则根据 durationMinutes 计算" },
      "durationMinutes": { "type": "integer", "description": "会议时长（分钟），默认 30", "default": 30 },
      "needRoom": { "type": "boolean", "description": "是否需要会议室", "default": false },
      "description": { "type": "string", "description": "会议描述" }
    },
    "required": ["title", "attendees"]
  },
  "input_examples": [
    {
      "title": "产品评审会",
      "attendees": ["ou_aaa", "ou_bbb"],
      "durationMinutes": 60,
      "start": "2026-06-01T14:00:00+08:00",
      "needRoom": true
    },
    {
      "title": "临时讨论",
      "attendees": ["ou_aaa"],
      "description": "讨论 Q3 计划"
    }
  ],
  "annotations": {
    "readOnlyHint": false,
    "idempotentHint": false
  }
}
```

## MCP Resources

bridge 通过 MCP Resources 暴露只读上下文信息：

| Resource URI | 描述 | 返回示例 |
|---|---|---|
| `lark://identity` | 当前登录身份 | `{"type": "user", "name": "张三", "email": "zhang.san@co.com"}` |
| `lark://permissions` | 已授权 scope | `{"scopes": ["im:message", "calendar:event", "contact:user.base"]}` |
| `lark://domains` | 可用域概览 | `{"domains": [{"name": "im", "tool_count": 8}, ...]}` |
| `lark://config` | bridge 运行配置 | `{"filter_policy": "whitelist", "timeout": 30, "pool_size": 0, "transport": "stdio"}` |
