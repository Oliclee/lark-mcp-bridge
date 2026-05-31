# SECURITY: 安全模型

> 文档索引见 [INDEX.md](./INDEX.md)

---

## 1. 安全边界总览

```
┌─────────────────────────────────────────────────────────┐
│  Amazon Quick (MCP Client)                               │
│  ── 信任边界 ──────────────────────────────────────────  │
│  bridge 仅监听 localhost，不暴露公网                       │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP (localhost only)
                             ▼
┌─────────────────────────────────────────────────────────┐
│  lark-mcp-bridge                                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ filters.py   │  │ audit.py     │  │ executor.py  │  │
│  │ 权限过滤     │  │ 审计记录     │  │ 子进程执行   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ── 信任边界 ──────────────────────────────────────────  │
│  bridge 不接触凭证，凭证由 lark-cli 管理                  │
└────────────────────────────┬────────────────────────────┘
                             │ subprocess
                             ▼
┌─────────────────────────────────────────────────────────┐
│  lark-cli                                                │
│  OAuth token 存储在 OS keychain                          │
│  权限范围 = 飞书应用已授权的 scope                        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 命令过滤策略

### 2.1 核心原则：白名单优先

```
默认策略: DENY ALL
↓
白名单匹配 → ALLOW（进入 risk_level 判断）
↓
黑名单匹配 → DENY（即使白名单通过）
```

### 2.2 风险分级（risk_level）

| 级别 | 标识 | 行为 | 示例 |
|---|---|---|---|
| `read` | lark-cli shortcut 以 `-` 开头 | 直接执行 | `lark.calendar.agenda`, `lark.docs.fetch` |
| `write` | lark-cli shortcut 以 `+` 开头 | 执行，结果标记 `readOnlyHint: false` | `lark.im.messages-send`, `lark.task.create` |
| `destructive` | 命令含 `delete/remove/destroy/batch-delete` | 需客户端二次确认（MCP `destructiveHint: true`） | `lark.drive.delete`, `lark.base.records-batch-delete` |

### 2.3 自动分级规则

discovery 阶段根据 lark-cli shortcut 前缀自动标记：

```python
def classify_risk(shortcut: str, command_name: str) -> RiskLevel:
    """
    启发式分级：
    1. shortcut 以 '-' 开头 → read
    2. shortcut 以 '+' 开头 → write
    3. command_name 含 delete/remove/destroy/batch → destructive
    4. 默认 → write（保守策略）
    """
```

### 2.4 白名单配置格式

```toml
# lark-mcp-bridge.toml

[security]
default_policy = "deny"  # deny | allow

[security.whitelist]
# 按域允许
domains = ["im", "calendar", "contact", "doc", "base", "task"]

# 按具体命令允许（覆盖域级别）
commands = [
    "lark.drive.list",
    "lark.drive.download",
]

[security.blacklist]
# 始终禁止（优先级最高）
patterns = ["delete", "remove", "destroy", "batch-delete", "purge"]
commands = ["lark.admin.*"]  # 管理员命令全部禁止
```

### 2.5 黑名单 vs 白名单优先级

```
黑名单 > 白名单 > 默认策略

即：黑名单中的命令，即使出现在白名单中也不允许执行。
```

---

## 3. 审计日志

### 3.1 审计事件

| 事件 | 记录内容 |
|---|---|
| `TOOL_CALL` | timestamp, tool_name, risk_level, 参数摘要（脱敏） |
| `TOOL_RESULT` | timestamp, tool_name, success/error, 耗时 |
| `TOOL_BLOCKED` | timestamp, tool_name, 原因（黑名单/未在白名单/策略拒绝） |
| `DESTRUCTIVE_CONFIRM` | timestamp, tool_name, 是否通过二次确认 |
| `AUTH_ERROR` | timestamp, 错误类型 |

### 3.2 日志格式

```json
{
  "ts": "2026-05-29T08:30:00+08:00",
  "event": "TOOL_CALL",
  "tool": "lark.im.messages-send",
  "risk_level": "write",
  "params_summary": {"chatId": "oc_***d3f", "msgType": "text"},
  "duration_ms": 1200,
  "success": true
}
```

### 3.3 脱敏规则

- `chatId`、`userId` 等 ID：保留前 3 位 + 后 3 位，中间替换为 `***`
- `text`、`content` 等内容字段：仅记录长度（`"text": "<128 chars>"`）
- `write`/`destructive` 操作的参数记录完整（不脱敏），便于事后审计

### 3.4 配置

```bash
LARK_MCP_AUDIT_LOG=/var/log/lark-mcp-bridge/audit.jsonl  # 日志路径
LARK_MCP_AUDIT_LEVEL=write  # 记录级别：read | write | all
```

---

## 4. Identity 安全

### 4.1 身份标记

discovery 阶段为每个 tool 标记 `required_identity`：

| 标记 | 含义 | 来源 |
|---|---|---|
| `user` | 必须用户身份 | lark-cli 元数据中标记为 user-only 的命令 |
| `bot` | 必须应用身份 | lark-cli 元数据中标记为 bot-only 的命令 |
| `both` | 两种身份均可 | 默认值 |

### 4.2 身份不匹配处理

当 Agent 调用需要特定身份的 tool 但当前身份不匹配时：

```json
{
  "isError": true,
  "content": [{
    "type": "text",
    "text": "此操作需要 user 身份。当前为 bot 身份。请使用 identityAs: \"user\" 参数重试，或确认 lark-cli 已完成用户登录（lark-cli auth login --as user）。"
  }]
}
```

---

## 5. 网络安全

| 措施 | 说明 |
|---|---|
| 监听地址 | 默认 `127.0.0.1`，不接受远程连接 |
| CORS | 仅允许 Amazon Quick 来源 |
| 无认证 | bridge ↔ Amazon Quick 之间无额外认证（localhost 信任模型） |
| 子进程隔离 | 每个 tool call 为独立子进程，无共享状态 |

---

## 6. 威胁模型

| 威胁 | 缓解 |
|---|---|
| 恶意 tool call 删除数据 | 白名单 + destructiveHint 二次确认 |
| Agent 幻觉调用不存在的命令 | executor 校验命令在注册列表中 |
| lark-cli token 泄露 | bridge 不接触 token，存储在 OS keychain |
| prompt injection 导致越权 | filters.py 在 executor 前拦截，与 Agent 推理独立 |
| 子进程挂起/资源耗尽 | 超时控制 + 进程级 kill |
