# TESTING: 测试策略

> 文档索引见 [INDEX.md](./INDEX.md)

---

## 1. 测试分层

```
┌────────────────────────────────────────────────────┐
│  E2E（端到端）                                      │
│  Amazon Quick → bridge → lark-cli → 飞书           │
│  手动 / Phase 1.5 专项验证                          │
├────────────────────────────────────────────────────┤
│  集成测试                                           │
│  bridge 完整流程 + mock lark-cli subprocess         │
│  CI 可运行，无需认证                                │
├────────────────────────────────────────────────────┤
│  单元测试                                           │
│  各模块独立逻辑（filter 规则、参数映射、缓存）       │
│  最快，覆盖核心逻辑                                 │
└────────────────────────────────────────────────────┘
```

| 层级 | 范围 | Mock 策略 | 运行环境 | 频率 |
|---|---|---|---|---|
| 单元测试 | 单个模块/函数 | 纯函数，不涉及外部依赖 | 本地 + CI | 每次提交 |
| 集成测试 | 多模块协作 | Mock subprocess（fixture 文件） | 本地 + CI | 每次提交 |
| E2E 测试 | 完整链路 | 真实 lark-cli + 飞书沙箱 | 本地（需认证） | 手动 / 里程碑 |

---

## 2. Mock 策略：如何不依赖真实 lark-cli

### 2.1 核心思路

`executor.py` 是唯一与 lark-cli 交互的模块。测试时替换 executor 的 subprocess 调用：

```python
# tests/conftest.py
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_executor():
    """Mock subprocess.run，返回预录制的 fixture 文件内容"""
    def _mock(fixture_name):
        fixture_path = Path(__file__).parent / "fixtures" / f"{fixture_name}.json"
        output = fixture_path.read_text()
        
        with patch("lark_mcp_bridge.executor.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=output,
                stderr=""
            )
            yield mock_run
    
    return _mock
```

### 2.2 Fixture 数据来源

```
tests/fixtures/
├── schema/
│   ├── all_tools.json           # lark-cli schema --format json 完整输出
│   ├── calendar_schema.json     # 单域 schema
│   └── invalid_schema.json      # 异常输出
├── calls/
│   ├── calendar_agenda_ok.json  # +agenda 正常返回
│   ├── calendar_agenda_empty.json
│   ├── im_send_ok.json
│   ├── error_auth_expired.json  # 认证过期
│   ├── error_rate_limit.json    # 限流
│   ├── error_permission.json    # 权限不足
│   └── error_timeout.json       # 超时
├── help/
│   ├── calendar_help.txt        # lark-cli calendar --help 输出
│   └── top_level_help.txt       # lark-cli --help 输出
└── README.md                    # fixture 录制说明
```

### 2.3 录制 Fixture

```bash
# 录制脚本（需要认证环境）
scripts/record_fixtures.sh

# 内容示例：
lark-cli schema --format json > tests/fixtures/schema/all_tools.json
lark-cli calendar +agenda --format json > tests/fixtures/calls/calendar_agenda_ok.json
lark-cli calendar --help > tests/fixtures/help/calendar_help.txt
```

**原则**：fixture 随 lark-cli 版本更新重新录制，版本号记录在 fixture 目录的 `README.md` 中。

---

## 3. 各模块测试重点

### 3.1 discovery.py

| 测试点 | 输入 | 预期输出 |
|---|---|---|
| 正常解析 tool 列表 | `fixtures/schema/all_tools.json` | 对应数量的 ToolDefinition 对象 |
| name 转换（多词） | `"approval instances cancel"` | `"lark.approval.instances-cancel"` |
| name 转换（含点号） | `"im chat.members create"` | `"lark.im.chat-members-create"` |
| name 转换（单词） | `"shortcut"` | `"lark.shortcut"` |
| risk 映射：read | `_meta.risk = "read"` | `risk_level = "read"` |
| risk 映射：destructive | `_meta.risk = "high-risk-write"` | `risk_level = "destructive"` |
| risk 映射：danger 标记 | `_meta.danger = true` | `risk_level = "destructive"` |
| identity 提取：user | `_meta.access_tokens = ["user"]` | `required_identity = "user"` |
| identity 提取：bot | `_meta.access_tokens = ["bot"]` | `required_identity = "bot"` |
| identity 提取：both | `_meta.access_tokens = ["user", "bot"]` | `required_identity = "both"` |
| inputSchema 清理 | schema 含 `yes` 属性 | 输出 schema 不含 `yes`，required 中也移除 |
| cli_command 保留 | `name = "calendar events patch"` | `cli_command = "calendar events patch"` |
| 空 schema 容错 | `[]` | 0 个 tool，不报错 |
| 缓存命中 | 缓存文件存在 + no_cache=False | 不调用 subprocess，直接返回 |
| 缓存跳过 | no_cache=True | 调用 subprocess，忽略缓存 |
| 缓存损坏 | 缓存文件内容非法 JSON | 回退到 subprocess 调用 |
| CLI 未找到 | FileNotFoundError | 抛出 DiscoveryError(E_CLI_NOT_FOUND) |
| CLI 超时 | subprocess.TimeoutExpired | 抛出 DiscoveryError(E_TIMEOUT) |
| CLI 返回非零 | exit code ≠ 0 | 抛出 DiscoveryError(E_CLI_ERROR) |
| 输出非 JSON | stdout 为非法 JSON | 抛出 DiscoveryError(E_CLI_ERROR) |
| 输出非数组 | stdout 为 JSON object | 抛出 DiscoveryError(E_CLI_ERROR) |
| 格式异常条目 | 数组中某条目缺少 name 字段 | 跳过该条目，不报错 |
| 按域分组 | 多个 tool | get_tools_by_domain 正确分组 |

### 3.2 filters.py

| 测试点 | 输入 | 预期输出 |
|---|---|---|
| 白名单通过 | domain=calendar, 白名单含 calendar | ALLOW |
| 白名单拒绝 | domain=admin, 白名单不含 admin | DENY |
| 黑名单优先 | domain=drive, command=delete, 白名单含 drive | DENY |
| 默认策略 deny | 未配置的域 | DENY |

### 3.3 executor.py

| 测试点 | 输入 | 预期输出 |
|---|---|---|
| 正常执行 | exit 0 + valid JSON | tool result |
| 命令失败 | exit 1 + stderr | isError: true + 结构化错误 |
| 超时 | 30s 无响应 | E_TIMEOUT 错误 |
| 二次确认 | exit 10 | destructiveHint 标记 |

### 3.4 composite.py

| 测试点 | 输入 | 预期输出 |
|---|---|---|
| 指定时间创建会议 | title + attendees + start + end | 直接调用 create，返回成功 |
| 不指定时间 | title + attendees（无 start） | 先查 freebusy → 再 create |
| 需要会议室 | need_room=True | 调用 room-find → 将 room_id 加入 attendees → create |
| 找不到会议室 | room-find 返回空列表 | 不阻塞，继续创建日程（meeting_room=None） |
| freebusy 失败 | execute 返回 E_AUTH_EXPIRED | 返回失败 + recovery_hint 提示手动指定时间 |
| create 失败 | execute 返回 E_PERMISSION_DENIED | 透传错误结果 |

### 3.5 server.py（集成测试）

| 测试点 | 输入 | 预期输出 |
|---|---|---|
| tool list | MCP list_tools 请求 | 返回已注册 tool 列表 |
| tool call | MCP tool call 请求 | 透传 executor 结果 |
| 启动检查 | lark-cli 不存在 | 启动失败，报错信息清晰 |

---

## 4. CI 配置

### 4.1 无认证运行

CI 环境中 lark-cli **不认证**——所有测试通过 mock fixture 运行。

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest --cov=lark_mcp_bridge --cov-report=xml
```

### 4.2 覆盖率目标

| Phase | 目标 | 重点 |
|---|---|---|
| Phase 1 | > 60% | executor, filters |
| Phase 2 | > 75% | + discovery |
| Phase 3+ | > 85% | + 错误处理分支 |

---

## 5. E2E 测试（手动）

Phase 1.5 端到端验证清单：

- [ ] bridge 启动后 Amazon Quick 能发现所有 tool
- [ ] Agent 查询日程（`lark.calendar.agenda`）成功返回
- [ ] Agent 发送消息（`lark.im.messages-send`）成功
- [ ] Agent 搜索联系人（`lark.contact.search-user`）成功
- [ ] 高风险操作触发二次确认提示
- [ ] 认证过期时返回可恢复的错误信息
- [ ] Prompt 引导下 Agent 能完成"查日程→发消息"完整流程
