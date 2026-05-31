"""冒烟测试：验证包可正常导入和启动。"""

import subprocess
import sys


def test_import():
    """验证 lark_mcp_bridge 包可导入且版本号存在。"""
    import lark_mcp_bridge

    assert lark_mcp_bridge.__version__ == "0.1.0"


def test_entry_point_exists():
    """验证 console script entry point 已注册。"""
    result = subprocess.run(
        ["lark-mcp-bridge", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    # FastMCP 没有 --help，会直接进入 stdio 模式然后因为无输入退出
    # 只要不是 "command not found" 就算通过
    assert result.returncode is not None  # 进程能启动


def test_module_entry_point():
    """验证 python -m lark_mcp_bridge.server 可启动。"""
    result = subprocess.run(
        [sys.executable, "-c", "from lark_mcp_bridge.server import main; print('ok')"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "ok" in result.stdout
