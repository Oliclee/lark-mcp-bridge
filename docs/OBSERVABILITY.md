# OBSERVABILITY: 可观测性

> 文档索引见 [INDEX.md](./INDEX.md)

---

## 1. 健康检查

### 1.1 端点定义

```
GET /health
```

**响应**：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "lark_cli": {
    "found": true,
    "version": "0.26.3",
    "auth_status": "authenticated",
    "identity": "user"
  },
  "tools": {
    "registered": 47,
    "filtered_out": 12,
    "domains": ["im", "calendar", "base", "doc", "contact", "task"]
  },
  "last_call": {
    "timestamp": "2026-05-29T08:25:00+08:00",
    "tool": "lark.calendar.agenda",
    "success": true
  }
}
```

### 1.2 健康状态判定

| 状态 | 条件 |
|---|---|
| `healthy` | lark-cli 可用 + 认证有效 |
| `degraded` | lark-cli 可用但认证过期（需重新登录） |
| `unhealthy` | lark-cli 未找到 / 无法执行 |

### 1.3 HTTP 状态码

| 健康状态 | HTTP Code |
|---|---|
| healthy | 200 |
| degraded | 200（body 中标记 degraded） |
| unhealthy | 503 |

---

## 2. 指标（Metrics）

### 2.1 端点

```
GET /metrics
```

返回 Prometheus text format。

### 2.2 指标定义

```prometheus
# HELP lark_mcp_tool_calls_total Total number of tool calls
# TYPE lark_mcp_tool_calls_total counter
lark_mcp_tool_calls_total{tool="lark.calendar.agenda",status="success"} 42
lark_mcp_tool_calls_total{tool="lark.im.messages-send",status="error"} 3

# HELP lark_mcp_tool_duration_seconds Tool call duration
# TYPE lark_mcp_tool_duration_seconds histogram
lark_mcp_tool_duration_seconds_bucket{tool="lark.calendar.agenda",le="1.0"} 38
lark_mcp_tool_duration_seconds_bucket{tool="lark.calendar.agenda",le="5.0"} 41
lark_mcp_tool_duration_seconds_bucket{tool="lark.calendar.agenda",le="30.0"} 42

# HELP lark_mcp_tool_blocked_total Tool calls blocked by filter
# TYPE lark_mcp_tool_blocked_total counter
lark_mcp_tool_blocked_total{tool="lark.drive.delete",reason="blacklist"} 1

# HELP lark_mcp_subprocess_pool_size Current subprocess pool utilization
# TYPE lark_mcp_subprocess_pool_size gauge
lark_mcp_subprocess_pool_size{state="active"} 2
lark_mcp_subprocess_pool_size{state="idle"} 3

# HELP lark_mcp_discovery_duration_seconds Time to complete tool discovery
# TYPE lark_mcp_discovery_duration_seconds gauge
lark_mcp_discovery_duration_seconds 2.3
```

### 2.3 关键告警指标

| 指标 | 告警阈值 | 含义 |
|---|---|---|
| error rate (5min) | > 30% | 可能 token 过期或 lark-cli 异常 |
| p95 延迟 | > 10s | 子进程响应慢 |
| blocked calls | 连续 > 5 次 | Agent 可能在尝试越权操作 |

---

## 3. 日志规范

### 3.1 日志级别

| 级别 | 用途 |
|---|---|
| `INFO` | 启动信息、tool 注册完成、正常 tool call |
| `WARNING` | 认证即将过期、tool call 超时但重试成功 |
| `ERROR` | tool call 失败、子进程异常退出 |
| `DEBUG` | 完整 subprocess 命令行、stdout/stderr 原文 |

### 3.2 结构化日志格式

```json
{
  "level": "INFO",
  "ts": "2026-05-29T08:30:00.123+08:00",
  "msg": "tool_call_complete",
  "tool": "lark.calendar.agenda",
  "duration_ms": 850,
  "exit_code": 0
}
```

### 3.3 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LARK_MCP_LOG_LEVEL` | `INFO` | 日志级别 |
| `LARK_MCP_LOG_FORMAT` | `json` | json / text |
| `LARK_MCP_LOG_FILE` | (stdout) | 日志输出路径 |

---

## 4. 启动 Banner

bridge 启动时输出诊断信息：

```
═══════════════════════════════════════════════════════
  lark-mcp-bridge v0.1.0
  Transport: streamable-http @ http://127.0.0.1:8080/mcp
───────────────────────────────────────────────────────
  lark-cli: v0.26.3 ✓
  Identity: user (zhang.san@company.com)
  Auth:     valid (expires in 6d)
───────────────────────────────────────────────────────
  Tools:    47 registered (12 filtered by policy)
  Domains:  im, calendar, base, doc, contact, task
  Prompts:  5 loaded
  Filter:   whitelist (6 domains) + blacklist (5 patterns)
───────────────────────────────────────────────────────
  Health:   http://127.0.0.1:8080/health
  Metrics:  http://127.0.0.1:8080/metrics
═══════════════════════════════════════════════════════
```

---

## 5. 错误追踪

### 5.1 错误分类

每个错误附带 `error_code` 前缀，便于追踪：

| 前缀 | 含义 | 处理 |
|---|---|---|
| `E_AUTH_*` | 认证相关 | 提示用户重新登录 |
| `E_NET_*` | 网络/超时 | 自动重试 |
| `E_PERM_*` | 权限不足 | 提示所需权限 |
| `E_CLI_*` | lark-cli 自身错误 | 记录 stderr，提示升级 |
| `E_BRIDGE_*` | bridge 内部错误 | 记录堆栈，报告 bug |

### 5.2 关联 ID

每个 MCP tool call 生成唯一 `trace_id`，贯穿日志和审计记录：

```json
{
  "trace_id": "tc_29a8f3c1",
  "tool": "lark.im.messages-send",
  "steps": [
    {"step": "filter_check", "result": "pass", "ms": 0},
    {"step": "subprocess_exec", "cmd": "lark-cli im +messages-send ...", "ms": 1150},
    {"step": "response_parse", "result": "ok", "ms": 2}
  ]
}
```

---

## 6. Agent Trace（链路追踪）

### 6.1 lark-cli 原生支持（v1.0.44+）

lark-cli 支持通过环境变量 `LARKSUITE_CLI_AGENT_TRACE` 注入 `X-Agent-Trace` HTTP header，飞书服务端可据此区分请求来源。

**bridge 集成方式**（Phase 3 实施）：

executor 在 spawn 子进程时注入该环境变量：

```python
env = os.environ.copy()
env["LARKSUITE_CLI_AGENT_TRACE"] = f"lark-mcp-bridge/{bridge_version}"
subprocess.run(command, env=env, ...)
```

### 6.2 追踪价值

| 场景 | 价值 |
|---|---|
| 飞书后端日志排查 | 区分"来自 bridge 的 API 调用" vs 用户直接使用 lark-cli |
| bridge 多实例 | 不同 bridge 实例可设置不同 trace 值（如 `lark-mcp-bridge/0.1.0/instance-a`） |
| 与 bridge 内部 trace_id 关联 | bridge 可将自身的 `trace_id`（§5.2）拼入 agent trace，实现端到端追踪 |

> 来源：lark-cli [#1158](https://github.com/larksuite/cli/pull/1158)，v1.0.44 新增。
