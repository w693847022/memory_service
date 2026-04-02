"""REST API 测试共享 fixtures."""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from rest_api.main import app


@pytest.fixture
def client():
    """创建测试客户端."""
    return TestClient(app)
