"""Phase 2.5 性能基准测量脚本。

测量项：
1. Discovery 完整耗时（含缓存 vs 无缓存）
2. 单次 tool call 延迟（P50/P95/P99）
3. subprocess 冷启动开销
4. MCP tool list token 估算
"""

import json
import statistics
import subprocess
import time
from pathlib import Path

# 确保在项目根目录运行
PROJECT_ROOT = Path(__file__).parent.parent


def measure_discovery():
    """测量 discovery 耗时。"""
    print("=" * 60)
    print("1. Discovery 耗时")
    print("=" * 60)

    from lark_mcp_bridge.config import BridgeSettings
    from lark_mcp_bridge.discovery import discover_tools

    # 无缓存
    settings = BridgeSettings(no_cache=True, cache_dir="/tmp/bench_cache_nocache")
    times_no_cache = []
    for i in range(3):
        start = time.perf_counter()
        tools = discover_tools(settings=settings)
        elapsed = (time.perf_counter() - start) * 1000
        times_no_cache.append(elapsed)
        print(f"  无缓存 #{i+1}: {elapsed:.0f}ms ({len(tools)} tools)")

    # 有缓存
    cache_dir = Path("/tmp/bench_cache_withcache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    settings_cached = BridgeSettings(no_cache=False, cache_dir=str(cache_dir))
    # 先跑一次填充缓存
    discover_tools(settings=settings_cached)
    times_cached = []
    for i in range(5):
        start = time.perf_counter()
        tools = discover_tools(settings=settings_cached)
        elapsed = (time.perf_counter() - start) * 1000
        times_cached.append(elapsed)

    print(f"\n  无缓存平均: {statistics.mean(times_no_cache):.0f}ms")
    print(f"  有缓存平均: {statistics.mean(times_cached):.1f}ms")
    print(f"  缓存加速比: {statistics.mean(times_no_cache) / statistics.mean(times_cached):.0f}x")
    return tools


def measure_tool_call_latency():
    """测量单次 tool call 延迟。"""
    print("\n" + "=" * 60)
    print("2. Tool call 延迟（lark-cli calendar +agenda）")
    print("=" * 60)

    from lark_mcp_bridge.config import BridgeSettings
    from lark_mcp_bridge.executor import execute

    settings = BridgeSettings()
    times = []
    for i in range(10):
        start = time.perf_counter()
        result = execute(["calendar", "+agenda", "--format", "json"], settings=settings)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        status = "ok" if result.success else f"err:{result.error_code}"
        if i == 0:
            print(f"  首次调用: {elapsed:.0f}ms ({status})")

    times_sorted = sorted(times)
    p50 = times_sorted[len(times_sorted) // 2]
    p95 = times_sorted[int(len(times_sorted) * 0.95)]
    p99 = times_sorted[-1]  # 10 次取最大值近似 P99

    print(f"\n  样本数: {len(times)}")
    print(f"  P50: {p50:.0f}ms")
    print(f"  P95: {p95:.0f}ms")
    print(f"  P99: {p99:.0f}ms")
    print(f"  平均: {statistics.mean(times):.0f}ms")
    print(f"  最小: {min(times):.0f}ms")
    print(f"  最大: {max(times):.0f}ms")


def measure_subprocess_cold_start():
    """测量 subprocess 冷启动开销。"""
    print("\n" + "=" * 60)
    print("3. subprocess 冷启动开销（lark-cli --version）")
    print("=" * 60)

    times = []
    for i in range(10):
        start = time.perf_counter()
        subprocess.run(
            ["lark-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    print(f"  平均: {statistics.mean(times):.0f}ms")
    print(f"  最小: {min(times):.0f}ms")
    print(f"  最大: {max(times):.0f}ms")
    print(f"  标准差: {statistics.stdev(times):.0f}ms")


def estimate_token_consumption(tools):
    """估算 MCP tool list 的 token 消耗。"""
    print("\n" + "=" * 60)
    print("4. MCP tool list token 估算")
    print("=" * 60)

    # 模拟完整 tool list JSON
    full_list = []
    for t in tools:
        full_list.append({
            "name": t.name,
            "description": t.description,
            "inputSchema": t.input_schema,
        })

    full_json = json.dumps(full_list, ensure_ascii=False)
    # 粗略估算：1 token ≈ 4 字符（英文），中文约 1-2 字符/token
    char_count = len(full_json)
    token_estimate = char_count // 3  # 保守估算

    print(f"  全部 {len(tools)} 个 tool:")
    print(f"    JSON 字符数: {char_count:,}")
    print(f"    Token 估算: ~{token_estimate:,}")

    # 渐进式暴露：只暴露手工 tool（约 10 个）
    manual_tools = 10
    manual_ratio = manual_tools / len(tools)
    print(f"\n  渐进式暴露（仅 {manual_tools} 个手工 tool）:")
    print(f"    Token 估算: ~{int(token_estimate * manual_ratio):,}")
    print(f"    节省: {(1 - manual_ratio) * 100:.0f}%")


def main():
    print("lark-mcp-bridge 性能基准")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tools = measure_discovery()
    measure_tool_call_latency()
    measure_subprocess_cold_start()
    estimate_token_consumption(tools)

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print("  - 如果 P95 < 2000ms 且冷启动 < 200ms，Phase 4 进程池优先级低")
    print("  - 如果 token 节省 > 80%，渐进式暴露策略有效")


if __name__ == "__main__":
    main()
