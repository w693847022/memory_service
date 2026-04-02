"""统计 API 单元测试."""

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


@pytest.fixture
def mock_mcp_client():
    """Mock business client."""
    mock_client = Mock()
    mock_client.project_stats.return_value = _resp({
        "success": True,
        "data": {
            "total_projects": 10,
            "total_items": 100,
            "total_tags": 50
        }
    })
    mock_client.stats_summary.return_value = _resp({
        "success": True,
        "data": {"summary": "统计数据汇总"}
    })
    mock_client.stats_cleanup.return_value = _resp({
        "success": True,
        "data": {"deleted_count": 100, "retention_days": 30}
    })
    with patch("rest_api.business_client._get_client", return_value=mock_client):
        yield mock_client


class TestGetStats:
    """测试获取统计信息 API."""

    def test_get_stats_all(self, client, mock_mcp_client):
        """测试获取全局统计."""
        mock_mcp_client.project_stats.return_value = _resp({
            "success": True,
            "data": {
                "total_projects": 10,
                "total_items": 100,
                "total_tags": 50
            }
        })

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_projects"] == 10

    def test_get_stats_by_type(self, client, mock_mcp_client):
        """测试按类型获取统计."""
        mock_mcp_client.stats_summary.return_value = _resp({
            "success": True,
            "data": {
                "type": "tool",
                "stats": {
                    "project_list": 150,
                    "project_add": 80
                }
            }
        })

        response = client.get("/api/stats?type=tool")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == "tool"


class TestGetStatsSummary:
    """测试获取统计摘要 API."""

    def test_get_summary_all(self, client, mock_mcp_client):
        """测试获取全部摘要."""
        mock_mcp_client.stats_summary.return_value = _resp({
            "success": True,
            "data": {
                "summary": "统计数据汇总"
            }
        })

        response = client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_summary_by_tool(self, client, mock_mcp_client):
        """测试按工具获取摘要."""
        mock_mcp_client.stats_summary.return_value = _resp({
            "success": True,
            "data": {
                "tool_name": "project_list",
                "call_count": 150,
                "last_called": "2026-03-29T12:00:00"
            }
        })

        response = client.get(
            "/api/stats/summary?type=tool&tool_name=project_list"
        )

        assert response.status_code == 200
        mock_mcp_client.stats_summary.assert_called_once()

    def test_get_summary_by_project(self, client, mock_mcp_client):
        """测试按项目获取摘要."""
        mock_mcp_client.stats_summary.return_value = _resp({
            "success": True,
            "data": {
                "project_id": "proj_001",
                "tool_usage": {}
            }
        })

        response = client.get(
            "/api/stats/summary?type=project&project_id=proj_001"
        )

        assert response.status_code == 200

    def test_get_summary_by_date(self, client, mock_mcp_client):
        """测试按日期获取摘要."""
        mock_mcp_client.stats_summary.return_value = _resp({
            "success": True,
            "data": {
                "date": "2026-03-29",
                "daily_stats": {}
            }
        })

        response = client.get(
            "/api/stats/summary?type=daily&date=2026-03-29"
        )

        assert response.status_code == 200


class TestCleanupStats:
    """测试清理统计数据 API."""

    def test_cleanup_stats_default(self, client, mock_mcp_client):
        """测试使用默认保留天数清理."""
        mock_mcp_client.stats_cleanup.return_value = _resp({
            "success": True,
            "data": {
                "deleted_count": 100,
                "retention_days": 30
            }
        })

        response = client.delete("/api/stats/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cleanup_stats_custom_days(self, client, mock_mcp_client):
        """测试使用自定义保留天数清理."""
        mock_mcp_client.stats_cleanup.return_value = _resp({
            "success": True,
            "data": {
                "deleted_count": 200,
                "retention_days": 60
            }
        })

        response = client.delete("/api/stats/cleanup?retention_days=60")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cleanup_stats_error(self, client, mock_mcp_client):
        """测试清理失败."""
        mock_mcp_client.stats_cleanup.return_value = _resp({
            "success": False,
            "error": "清理失败"
        })

        response = client.delete("/api/stats/cleanup")

        assert response.status_code == 400
