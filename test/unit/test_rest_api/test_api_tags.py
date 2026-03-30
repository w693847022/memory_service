"""标签管理 API 单元测试."""

import pytest
from unittest.mock import Mock, patch
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


@pytest.fixture
def mock_mcp_client():
    """Mock MCP 客户端."""
    with patch("rest_api.routers.tags.mcp_client") as mock:
        yield mock


class TestListTags:
    """测试标签列表 API."""

    def test_list_tags_success(self, client, mock_mcp_client):
        """测试成功获取标签列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "tags": [
                    {"tag": "api", "summary": "API相关"},
                    {"tag": "frontend", "summary": "前端相关"}
                ],
                "total": 2
            }
        }

        response = client.get(
            "/api/tags?project_id=proj_001&page=1&size=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["tags"]) == 2

    def test_list_tags_with_group_filter(self, client, mock_mcp_client):
        """测试按分组过滤标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"tags": [], "total": 0}
        }

        response = client.get(
            "/api/tags?project_id=proj_001&group_name=features"
        )

        assert response.status_code == 200

    def test_list_tags_missing_project_id(self, client):
        """测试缺少项目 ID."""
        response = client.get("/api/tags")

        assert response.status_code == 422  # Validation error


class TestRegisterTag:
    """测试标签注册 API."""

    def test_register_tag_success(self, client, mock_mcp_client):
        """测试成功注册标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"tag": "new_tag", "summary": "新标签"}
        }

        response = client.post(
            "/api/tags",
            params={
                "project_id": "proj_001",
                "tag_name": "new_tag",
                "summary": "新标签的语义描述",
                "aliases": "alias1,alias2"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_register_tag_missing_params(self, client):
        """测试缺少必填参数."""
        response = client.post(
            "/api/tags",
            params={"project_id": "proj_001"}
        )

        assert response.status_code == 422


class TestUpdateTag:
    """测试更新标签 API."""

    def test_update_tag_success(self, client, mock_mcp_client):
        """测试成功更新标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.put(
            "/api/tags/api",
            params={
                "project_id": "proj_001",
                "summary": "更新后的标签描述"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteTag:
    """测试删除标签 API."""

    def test_delete_tag_success(self, client, mock_mcp_client):
        """测试成功删除标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.delete(
            "/api/tags/old_tag?project_id=proj_001&force=false"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_tag_force(self, client, mock_mcp_client):
        """测试强制删除标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.delete(
            "/api/tags/old_tag?project_id=proj_001&force=true"
        )

        assert response.status_code == 200


class TestMergeTags:
    """测试标签合并 API."""

    def test_merge_tags_success(self, client, mock_mcp_client):
        """测试成功合并标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "old_tag": "old_api",
                "new_tag": "api",
                "migrated_count": 5
            }
        }

        response = client.put(
            "/api/tags/merge",
            params={
                "project_id": "proj_001",
                "old_tag": "old_api",
                "new_tag": "api"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["migrated_count"] == 5

    def test_merge_tags_error(self, client, mock_mcp_client):
        """测试合并标签失败."""
        mock_mcp_client.call_tool.return_value = {
            "success": False,
            "error": "目标标签不存在"
        }

        response = client.put(
            "/api/tags/merge",
            params={
                "project_id": "proj_001",
                "old_tag": "old_tag",
                "new_tag": "not_exist"
            }
        )

        assert response.status_code == 400
