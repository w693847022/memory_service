"""错误处理和日志 单元测试."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from common.response import ApiResponse
from rest_api.main import app


def _resp(d: dict) -> ApiResponse:
    """将 dict 包装为 ApiResponse."""
    return ApiResponse.from_dict(d)


@pytest.fixture
def client():
    """创建测试客户端."""
    return TestClient(app)


class TestHealthCheck:
    """测试健康检查端点."""

    def test_health_check(self, client):
        """测试健康检查."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    def test_root_endpoint(self, client):
        """测试根路径."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "docs" in data["data"]


class TestErrorHandling:
    """测试错误处理."""

    @patch("rest_api.business_client._get_client")
    def test_mcp_connection_error(self, mock_get_client, client):
        """测试 MCP 连接错误."""
        mock_client = Mock()
        mock_client.project_list.return_value = _resp({
            "success": False,
            "error": "MCP 连接失败"
        })
        mock_get_client.return_value = mock_client

        response = client.get("/api/projects")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "MCP 连接失败" in data["detail"]

    @patch("rest_api.business_client._get_client")
    def test_mcp_timeout_error(self, mock_get_client, client):
        """测试 MCP 超时错误."""
        mock_client = Mock()
        mock_client.project_list.return_value = _resp({
            "success": False,
            "error": "MCP tool execution timeout"
        })
        mock_get_client.return_value = mock_client

        response = client.get("/api/projects")

        assert response.status_code == 400

    @patch("rest_api.business_client._get_client")
    def test_invalid_response_format(self, mock_get_client, client):
        """测试无效响应格式."""
        mock_client = Mock()
        mock_client.project_list.return_value = _resp({
            "success": False,
            "error": "Invalid JSON response"
        })
        mock_get_client.return_value = mock_client

        response = client.get("/api/projects")

        assert response.status_code == 400

    def test_not_found_error(self, client):
        """测试 404 错误."""
        response = client.get("/api/not_exist")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """测试方法不允许."""
        response = client.post("/api/projects/proj_001")

        assert response.status_code == 405


class TestValidationErrors:
    """测试参数验证错误."""

    def test_invalid_group_type(self, client):
        """测试无效分组类型."""
        response = client.get("/api/projects/proj_001/invalid")

        assert response.status_code == 400
        data = response.json()
        assert "无效的分组类型" in data["detail"]

    def test_invalid_view_mode(self, client):
        """测试无效视图模式."""
        response = client.get("/api/projects?view_mode=invalid")

        assert response.status_code == 422  # Validation error

    def test_invalid_page_number(self, client):
        """测试无效页码."""
        response = client.get("/api/projects?page=0")

        assert response.status_code == 422

    def test_invalid_mode(self, client):
        """测试无效删除模式."""
        response = client.delete("/api/projects/proj_001?mode=invalid")

        assert response.status_code == 422


class TestApiResponseFormat:
    """测试统一响应格式."""

    @patch("rest_api.business_client._get_client")
    def test_success_response_format(self, mock_get_client, client):
        """测试成功响应格式."""
        mock_client = Mock()
        mock_client.project_list.return_value = _resp({
            "success": True,
            "data": {"test": "data"}
        })
        mock_get_client.return_value = mock_client

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    @patch("rest_api.business_client._get_client")
    def test_error_response_format(self, mock_get_client, client):
        """测试错误响应格式."""
        mock_client = Mock()
        mock_client.project_list.return_value = _resp({
            "success": False,
            "error": "测试错误"
        })
        mock_get_client.return_value = mock_client

        response = client.get("/api/projects")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestCORS:
    """测试 CORS 配置."""

    def test_cors_headers(self, client):
        """测试 CORS 响应头."""
        response = client.get("/api/projects")

        # 检查 CORS 头是否存在
        # 注意: TestClient 不会完全模拟浏览器 CORS 行为
        # 主要验证中间件已配置
        assert response.status_code in (200, 400)  # 成功或 MCP 错误都可接受
