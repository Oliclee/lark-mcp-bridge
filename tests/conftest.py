"""pytest 共享 fixture。"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """返回 fixtures 目录路径。"""
    return FIXTURES_DIR


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run，用于不依赖真实 lark-cli 的测试。"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="{}",
            stderr="",
        )
        yield mock_run
