"""Phase 3.5 审计日志分析脚本。

读取审计日志，输出：
- Tool 调用成功率
- 失败模式分布
- 高频 tool 排名
- 平均延迟

用法：
  python scripts/analyze_audit.py [audit_log_path]
  默认路径：~/.local/share/lark-mcp-bridge/audit.jsonl
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def analyze(log_path: Path) -> None:
    if not log_path.exists():
        print(f"审计日志不存在: {log_path}")
        print("提示：设置 LARK_MCP_AUDIT_LOG 环境变量启用审计日志")
        return

    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    events = [json.loads(line) for line in lines if line.strip()]

    if not events:
        print("审计日志为空")
        return

    print(f"审计日志: {log_path}")
    print(f"总事件数: {len(events)}")
    print()

    # 按事件类型分组
    by_type = Counter(e["event"] for e in events)
    print("=== 事件类型分布 ===")
    for event_type, count in by_type.most_common():
        print(f"  {event_type}: {count}")
    print()

    # Tool 调用分析
    calls = [e for e in events if e["event"] == "TOOL_CALL"]
    results = [e for e in events if e["event"] == "TOOL_RESULT"]
    blocked = [e for e in events if e["event"] == "TOOL_BLOCKED"]

    if results:
        success_count = sum(1 for r in results if r.get("success"))
        total = len(results)
        print("=== 成功率 ===")
        print(f"  总调用: {total}")
        print(f"  成功: {success_count} ({success_count/total*100:.1f}%)")
        print(f"  失败: {total - success_count} ({(total-success_count)/total*100:.1f}%)")
        print()

    # 失败模式
    failures = [r for r in results if not r.get("success")]
    if failures:
        error_codes = Counter(f.get("error_code", "unknown") for f in failures)
        print("=== 失败模式 ===")
        for code, count in error_codes.most_common(10):
            print(f"  {code}: {count}")
        print()

    # 高频 tool
    if calls:
        tool_freq = Counter(c["tool"] for c in calls)
        print("=== 高频 Tool（Top 10）===")
        for tool, count in tool_freq.most_common(10):
            print(f"  {tool}: {count}")
        print()

    # 延迟分析
    durations = [r["duration_ms"] for r in results if "duration_ms" in r]
    if durations:
        durations.sort()
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)]
        print("=== 延迟分布 ===")
        print(f"  P50: {p50}ms")
        print(f"  P95: {p95}ms")
        print(f"  平均: {sum(durations) // len(durations)}ms")
        print(f"  最大: {max(durations)}ms")
        print()

    # 被拦截的命令
    if blocked:
        blocked_tools = Counter(b["tool"] for b in blocked)
        print("=== 被拦截的命令 ===")
        for tool, count in blocked_tools.most_common(10):
            print(f"  {tool}: {count}")
        print()

    # 建议
    print("=== 优化建议 ===")
    if failures:
        top_failure = error_codes.most_common(1)[0]
        print(f"  - 最常见失败: {top_failure[0]} ({top_failure[1]}次)")
        if top_failure[0] == "E_BUSINESS_ERROR":
            print("    → 考虑为高频失败场景增加参数校验或更好的错误提示")
        elif top_failure[0] == "E_AUTH_EXPIRED":
            print("    → 考虑在 tool description 中提醒用户检查认证状态")

    if calls:
        top_tool = tool_freq.most_common(1)[0]
        if top_tool[1] > 10:
            print(f"  - 高频 tool: {top_tool[0]} ({top_tool[1]}次)")
            print("    → 如果该 tool 经常需要多次调用才成功，考虑优化 description 或增加 Prompt")


def main():
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        log_path = Path.home() / ".local" / "share" / "lark-mcp-bridge" / "audit.jsonl"

    analyze(log_path)


if __name__ == "__main__":
    main()
