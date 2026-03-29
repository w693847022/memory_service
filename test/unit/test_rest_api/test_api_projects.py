"""项目管理 API 单元测试."""

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
    with patch("src.rest_api.routers.projects.mcp_client") as mock:
        yield mock


class TestProjectList:
    """测试项目列表 API."""

    def test_list_projects_success(self, client, mock_mcp_client):
        """测试成功获取项目列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "projects": [
                    {"id": "proj_001", "name": "项目A"},
                    {"id": "proj_002", "name": "项目B"},
                ],
                "total": 2,
                "page": 1
            }
        }

        response = client.get("/api/projects?page=1&size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["total"] == 2

    def test_list_projects_with_filters(self, client, mock_mcp_client):
        """测试带过滤条件获取项目列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"projects": [], "total": 0}
        }

        response = client.get(
            "/api/projects?name_pattern=test&view_mode=detail"
        )

        assert response.status_code == 200
        mock_mcp_client.call_tool.assert_called_once()

    def test_list_projects_mcp_error(self, client, mock_mcp_client):
        """测试 MCP 调用错误."""
        mock_mcp_client.call_tool.return_value = {
            "success": False,
            "error": "MCP 连接失败"
        }

        response = client.get("/api/projects")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestRegisterProject:
    """测试项目注册 API."""

    def test_register_project_success(self, client, mock_mcp_client):
        """测试成功注册项目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"id": "proj_new", "name": "新项目"}
        }

        response = client.post(
            "/api/projects",
            params={
                "name": "新项目",
                "path": "/path/to/project",
                "summary": "项目摘要",
                "tags": "tag1,tag2"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "proj_new"

    def test_register_project_missing_name(self, client):
        """测试缺少必填参数."""
        response = client.post("/api/projects")

        assert response.status_code == 422  # Validation error


class TestGetProject:
    """测试获取项目详情 API."""

    def test_get_project_success(self, client, mock_mcp_client):
        """测试成功获取项目详情."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "id": "proj_001",
                "name": "项目A",
                "info": {"description": "测试项目"}
            }
        }

        response = client.get("/api/projects/proj_001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "proj_001"

    def test_get_project_not_found(self, client, mock_mcp_client):
        """测试项目不存在."""
        mock_mcp_client.call_tool.return_value = {
            "success": False,
            "error": "项目不存在"
        }

        response = client.get("/api/projects/not_exist")

        assert response.status_code == 404


class TestUpdateProject:
    """测试更新项目 API."""

    def test_update_project_success(self, client, mock_mcp_client):
        """测试成功更新项目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"id": "proj_001", "summary": "新摘要"}
        }

        response = client.put(
            "/api/projects/proj_001",
            params={"summary": "新摘要"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteProject:
    """测试删除项目 API."""

    def test_delete_project_archive(self, client, mock_mcp_client):
        """测试归档项目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.delete(
            "/api/projects/proj_001?mode=archive"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_project_permanent(self, client, mock_mcp_client):
        """测试永久删除项目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True
        }

        response = client.delete(
            "/api/projects/proj_001?mode=delete"
        )

        assert response.status_code == 200


class TestRenameProject:
    """测试重命名项目 API."""

    def test_rename_project_success(self, client, mock_mcp_client):
        """测试成功重命名项目."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {"old_name": "旧名称", "new_name": "新名称"}
        }

        response = client.put(
            "/api/projects/proj_001/rename",
            params={"new_name": "新名称"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["new_name"] == "新名称"


class TestProjectGroups:
    """测试项目分组 API."""

    def test_list_groups_success(self, client, mock_mcp_client):
        """测试成功获取分组列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "groups": ["features", "notes", "fixes", "standards"]
            }
        }

        response = client.get("/api/projects/proj_001/groups")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "groups" in data["data"]


class TestProjectTags:
    """测试项目标签 API."""

    def test_list_tags_success(self, client, mock_mcp_client):
        """测试成功获取标签列表."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "tags": [
                    {"tag": "api", "summary": "API相关"},
                    {"tag": "frontend", "summary": "前端相关"}
                ]
            }
        }

        response = client.get("/api/projects/proj_001/tags")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["tags"]) == 2
