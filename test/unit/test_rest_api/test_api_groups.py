"""分组管理 API 单元测试."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from src.rest_api.main import app


@pytest.fixture
def client():
    """创建测试客户端."""
    return TestClient(app)


@pytest.fixture
def mock_mcp_client():
    """Mock MCP 客户端."""
    with patch("src.rest_api.routers.groups.mcp_client") as mock:
        yield mock


class TestListGroupItems:
    """测试分组条目列表 API."""

    def test_list_features_success(self, client, mock_mcp_client):
        """测试成功获取功能列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "items": [
                    {"id": "feat_001", "summary": "功能A", "status": "pending"}
                ],
                "total": 1
            }
        }

        response = client.get("/api/projects/proj_001/features")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_notes_success(self, client, mock_mcp_client):
        """测试成功获取笔记列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"items": [], "total": 0}
        }

        response = client.get("/api/projects/proj_001/notes")

        assert response.status_code == 200

    def test_list_items_with_filters(self, client, mock_mcp_client):
        """测试带过滤条件获取列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"items": [], "total": 0}
        }

        response = client.get(
            "/api/projects/proj_001/features?status=pending&page=1&size=10"
        )

        assert response.status_code == 200
        mock_mcp_client.call_tool.assert_called_once()

    def test_list_items_invalid_group(self, client):
        """测试无效分组类型."""
        response = client.get("/api/projects/proj_001/invalid_group")

        assert response.status_code == 400
        data = response.json()
        assert "无效的分组类型" in data["detail"]


class TestGetGroupItem:
    """测试获取分组条目详情 API."""

    def test_get_item_success(self, client, mock_mcp_client):
        """测试成功获取条目详情."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "id": "feat_001",
                "summary": "功能A",
                "content": "详细内容",
                "status": "pending"
            }
        }

        response = client.get("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "feat_001"

    def test_get_item_not_found(self, client, mock_mcp_client):
        """测试条目不存在."""
        mock_mcp_client.call_tool.return_value = {
            "success": False,
            "error": "条目不存在"
        }

        response = client.get("/api/projects/proj_001/features/not_exist")

        assert response.status_code == 404


class TestCreateGroupItem:
    """测试创建分组条目 API."""

    def test_create_feature_success(self, client, mock_mcp_client):
        """测试成功创建功能."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"id": "feat_new", "summary": "新功能"}
        }

        response = client.post(
            "/api/projects/proj_001/features",
            params={
                "summary": "新功能",
                "content": "功能描述",
                "status": "pending",
                "tags": "api,frontend"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "feat_new"

    def test_create_note_success(self, client, mock_mcp_client):
        """测试成功创建笔记."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"id": "note_new", "summary": "新笔记"}
        }

        response = client.post(
            "/api/projects/proj_001/notes",
            params={
                "summary": "新笔记",
                "content": "笔记内容",
                "tags": "documentation"
            }
        )

        assert response.status_code == 200

    def test_create_item_missing_summary(self, client):
        """测试缺少必填参数."""
        response = client.post("/api/projects/proj_001/features")

        assert response.status_code == 422  # Validation error


class TestUpdateGroupItem:
    """测试更新分组条目 API."""

    def test_update_item_success(self, client, mock_mcp_client):
        """测试成功更新条目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"id": "feat_001", "summary": "更新后的摘要"}
        }

        response = client.put(
            "/api/projects/proj_001/features/feat_001",
            params={"summary": "更新后的摘要"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteGroupItem:
    """测试删除分组条目 API."""

    def test_delete_item_success(self, client, mock_mcp_client):
        """测试成功删除条目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.delete("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_item_error(self, client, mock_mcp_client):
        """测试删除失败."""
        mock_mcp_client.call_tool.return_value = {
            "success": False,
            "error": "删除失败"
        }

        response = client.delete("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 400


class TestManageItemTags:
    """测试管理条目标签 API."""

    def test_set_tags_success(self, client, mock_mcp_client):
        """测试设置标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"tags": ["api", "frontend"]}
        }

        response = client.put(
            "/api/projects/proj_001/features/feat_001/tags",
            params={
                "operation": "set",
                "tags": "api,frontend"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_tag_success(self, client, mock_mcp_client):
        """测试添加标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"tags": ["api", "new_tag"]}
        }

        response = client.put(
            "/api/projects/proj_001/features/feat_001/tags",
            params={
                "operation": "add",
                "tag": "new_tag"
            }
        )

        assert response.status_code == 200

    def test_remove_tag_success(self, client, mock_mcp_client):
        """测试移除标签."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"tags": ["api"]}
        }

        response = client.put(
            "/api/projects/proj_001/features/feat_001/tags",
            params={
                "operation": "remove",
                "tag": "frontend"
            }
        )

        assert response.status_code == 200
