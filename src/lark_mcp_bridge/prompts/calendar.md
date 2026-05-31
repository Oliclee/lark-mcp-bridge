---
name: lark-calendar-workflow
description: 飞书日历操作完整指南——查询日程、创建会议、处理冲突
domains: [calendar, contact]
tools_referenced: [lark.calendar.agenda, lark.calendar.schedule-meeting, lark.contact.search-user]
---

## 使用场景

当用户请求涉及日历操作时加载本 Prompt。

## 意图分支

### 1. 查询日程

用户想知道某天/某周的安排。

→ 调用 `lark.calendar.agenda`
→ 默认范围：今天。如需其他日期，传 `start_time` 和 `end_time`（ISO 8601）

### 2. 预约会议

用户想约一个会议。

**优先使用 composite tool**：
→ 调用 `lark.calendar.schedule-meeting`（一步完成：查空闲 → 找会议室 → 创建日程）

**需要的信息**：
- 会议标题（必须）
- 参会人（必须）——如果用户给的是姓名，先用 `lark.contact.search-user` 查 open_id
- 时间（可选）——不指定则自动选最近空闲时段
- 时长（可选）——默认 30 分钟
- 是否需要会议室（可选）——默认不需要

**参会人解析流程**：
1. 用户给了 open_id（ou_xxx）→ 直接使用
2. 用户给了姓名/邮箱 → 调用 `lark.contact.search-user` 获取 open_id
3. 搜索到多个结果 → 展示候选列表，让用户确认

### 3. 查看空闲

用户想知道某人某时段是否有空。

→ 目前无独立 tool 暴露（在 composite tool 内部使用）
→ 建议用 `lark.calendar.agenda` 查看自己的日程来判断

## 默认值规则

| 参数 | 默认值 | 说明 |
|---|---|---|
| duration_minutes | 30 | 未指定时长时 |
| need_room | false | 未明确要求会议室时 |
| start | 最近整点或半点 | 未指定时间时 |

## 常见错误恢复

| 错误 | 恢复策略 |
|---|---|
| 参会人 open_id 无效 | 用 `lark.contact.search-user` 重新搜索确认 |
| 时间格式错误 | 转换为 ISO 8601 格式（如 "明天下午3点" → "2026-06-01T15:00:00+08:00"） |
| 权限不足 | 提示用户确认 lark-cli 已用 user 身份登录 |
| 会议室找不到 | 会议仍会创建，只是没有会议室。告知用户可手动添加 |

## 时间处理提示

- 用户说"明天下午"→ 转为明天 14:00 开始
- 用户说"下周一上午"→ 转为下周一 09:00 开始
- 时区默认 +08:00（中国标准时间）
- 所有时间必须是 ISO 8601 格式传给 tool
