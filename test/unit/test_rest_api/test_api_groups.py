"""分组管理 API 单元测试."""

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
    # 设置默认返回值
    mock_client.project_get.return_value = _resp({
        "success": True,
        "data": {"items": [], "total": 0}
    })
    mock_client.project_add.return_value = _resp({
        "success": True,
        "data": {"id": "feat_new", "summary": "新功能"}
    })
    mock_client.project_update.return_value = _resp({
        "success": True,
        "data": {"id": "feat_001", "summary": "更新后的摘要"}
    })
    mock_client.project_delete.return_value = _resp({"success": True})
    mock_client.manage_item_tags.return_value = _resp({
        "success": True,
        "data": {"tags": ["api", "frontend"]}
    })
    mock_client.create_custom_group.return_value = _resp({
        "success": True,
        "message": "自定义组 'apis' 创建成功"
    })
    mock_client.update_group.return_value = _resp({
        "success": True,
        "message": "自定义组 'apis' 更新成功"
    })
    mock_client.delete_custom_group.return_value = _resp({
        "success": True,
        "message": "自定义组 'apis' 已删除"
    })
    mock_client.get_group_settings.return_value = _resp({
        "success": True,
        "data": {
            "settings": {
                "default_related_rules": {
                    "features": ["notes"],
                    "fixes": ["features", "notes"]
                }
            }
        }
    })
    mock_client.update_group_settings.return_value = _resp({
        "success": True,
        "message": "组设置更新成功"
    })
    with patch("rest_api.business_client._get_client", return_value=mock_client):
        yield mock_client


class TestListGroupItems:
    """测试分组条目列表 API."""

    def test_list_features_success(self, client, mock_mcp_client):
        """测试成功获取功能列表."""
        mock_mcp_client.project_get.return_value = _resp({
            "success": True,
            "data": {
                "items": [
                    {"id": "feat_001", "summary": "功能A", "status": "pending"}
                ],
                "total": 1
            }
        })

        response = client.get("/api/projects/proj_001/features")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_notes_success(self, client, mock_mcp_client):
        """测试成功获取笔记列表."""
        mock_mcp_client.project_get.return_value = _resp({
            "success": True,
            "data": {"items": [], "total": 0}
        })

        response = client.get("/api/projects/proj_001/notes")

        assert response.status_code == 200

    def test_list_items_with_filters(self, client, mock_mcp_client):
        """测试带过滤条件获取列表."""
        mock_mcp_client.project_get.return_value = _resp({
            "success": True,
            "data": {"items": [], "total": 0}
        })

        response = client.get(
            "/api/projects/proj_001/features?status=pending&page=1&size=10"
        )

        assert response.status_code == 200
        mock_mcp_client.project_get.assert_called_once()

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
        mock_mcp_client.project_get.return_value = _resp({
            "success": True,
            "data": {
                "id": "feat_001",
                "summary": "功能A",
                "content": "详细内容",
                "status": "pending"
            }
        })

        response = client.get("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "feat_001"

    def test_get_item_not_found(self, client, mock_mcp_client):
        """测试条目不存在."""
        mock_mcp_client.project_get.return_value = _resp({
            "success": False,
            "error": "条目不存在"
        })

        response = client.get("/api/projects/proj_001/features/not_exist")

        assert response.status_code == 404


class TestCreateGroupItem:
    """测试创建分组条目 API."""

    def test_create_feature_success(self, client, mock_mcp_client):
        """测试成功创建功能."""
        mock_mcp_client.project_add.return_value = _resp({
            "success": True,
            "data": {"id": "feat_new", "summary": "新功能"}
        })

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
        mock_mcp_client.project_add.return_value = _resp({
            "success": True,
            "data": {"id": "note_new", "summary": "新笔记"}
        })

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
        mock_mcp_client.project_update.return_value = _resp({
            "success": True,
            "data": {"id": "feat_001", "summary": "更新后的摘要"}
        })

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
        mock_mcp_client.project_delete.return_value = _resp({"success": True})

        response = client.delete("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_item_error(self, client, mock_mcp_client):
        """测试删除失败."""
        mock_mcp_client.project_delete.return_value = _resp({
            "success": False,
            "error": "删除失败"
        })

        response = client.delete("/api/projects/proj_001/features/feat_001")

        assert response.status_code == 400


class TestManageItemTags:
    """测试管理条目标签 API."""

    def test_set_tags_success(self, client, mock_mcp_client):
        """测试设置标签."""
        mock_mcp_client.manage_item_tags.return_value = _resp({
            "success": True,
            "data": {"tags": ["api", "frontend"]}
        })

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
        mock_mcp_client.manage_item_tags.return_value = _resp({
            "success": True,
            "data": {"tags": ["api", "new_tag"]}
        })

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
        mock_mcp_client.manage_item_tags.return_value = _resp({
            "success": True,
            "data": {"tags": ["api"]}
        })

        response = client.put(
            "/api/projects/proj_001/features/feat_001/tags",
            params={
                "operation": "remove",
                "tag": "frontend"
            }
        )

        assert response.status_code == 200


class TestCreateCustomGroup:
    """测试创建自定义组 API."""

    def test_create_custom_group_success(self, client):
        """测试成功创建自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_custom_group.return_value = _resp({
                "success": True,
                "message": "自定义组 'apis' 创建成功"
            })
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/projects/proj_001/groups",
                params={
                    "group_name": "apis",
                    "content_max_bytes": 500,
                    "summary_max_bytes": 100,
                    "allow_related": True,
                    "allowed_related_to": "notes,features",
                    "enable_status": True,
                    "enable_severity": False
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_create_custom_group_reserved_name(self, client):
        """测试创建自定义组时保留字段冲突."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_custom_group.return_value = _resp({
                "success": False,
                "error": "组名 'id' 与系统配置字段冲突"
            })
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/projects/proj_001/groups",
                params={"group_name": "id"}
            )

            assert response.status_code == 400
            data = response.json()
            assert "冲突" in data["detail"]

    def test_create_custom_group_duplicate_name(self, client):
        """测试创建重复名称的自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_custom_group.return_value = _resp({
                "success": False,
                "error": "自定义组 'apis' 已存在"
            })
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/projects/proj_001/groups",
                params={"group_name": "apis"}
            )

            assert response.status_code == 400
            assert "已存在" in response.json()["detail"]


class TestUpdateCustomGroup:
    """测试更新自定义组 API."""

    def test_update_custom_group_success(self, client):
        """测试成功更新自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.update_group.return_value = _resp({
                "success": True,
                "message": "自定义组 'apis' 更新成功"
            })
            mock_get_client.return_value = mock_client

            response = client.put(
                "/api/projects/proj_001/groups/apis",
                params={
                    "content_max_bytes": 1000,
                    "allow_related": True
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_update_custom_group_not_found(self, client):
        """测试更新不存在的自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.update_group.return_value = _resp({
                "success": False,
                "error": "组 'nonexistent' 不存在"
            })
            mock_get_client.return_value = mock_client

            response = client.put(
                "/api/projects/proj_001/groups/nonexistent",
                params={"content_max_bytes": 1000}
            )

            assert response.status_code == 400
            assert "不存在" in response.json()["detail"]


class TestDeleteCustomGroup:
    """测试删除自定义组 API."""

    def test_delete_custom_group_success(self, client):
        """测试成功删除自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.delete_custom_group.return_value = _resp({
                "success": True,
                "message": "自定义组 'apis' 已删除"
            })
            mock_get_client.return_value = mock_client

            response = client.delete("/api/projects/proj_001/groups/apis")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_delete_custom_group_not_found(self, client):
        """测试删除不存在的自定义组."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.delete_custom_group.return_value = _resp({
                "success": False,
                "error": "自定义组 'nonexistent' 不存在"
            })
            mock_get_client.return_value = mock_client

            response = client.delete("/api/projects/proj_001/groups/nonexistent")

            assert response.status_code == 400
            assert "不存在" in response.json()["detail"]


class TestGetGroupSettings:
    """测试获取组设置 API."""

    def test_get_group_settings_success(self, client):
        """测试成功获取组设置."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_group_settings.return_value = _resp({
                "success": True,
                "data": {
                    "settings": {
                        "default_related_rules": {
                            "features": ["notes"],
                            "fixes": ["features", "notes"]
                        }
                    }
                }
            })
            mock_get_client.return_value = mock_client

            response = client.get("/api/projects/proj_001/group-settings")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "settings" in data["data"]
            assert "default_related_rules" in data["data"]["settings"]

    def test_get_group_settings_error(self, client):
        """测试获取组设置失败."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_group_settings.return_value = _resp({
                "success": False,
                "error": "项目不存在"
            })
            mock_get_client.return_value = mock_client

            response = client.get("/api/projects/proj_001/group-settings")

            assert response.status_code == 400


class TestUpdateGroupSettings:
    """测试更新组设置 API."""

    def test_update_group_settings_success(self, client):
        """测试成功更新组设置."""
        with patch("rest_api.business_client._get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.update_group_settings.return_value = _resp({
                "success": True,
                "message": "组设置更新成功"
            })
            mock_get_client.return_value = mock_client

            response = client.put(
                "/api/projects/proj_001/group-settings",
                params={
                    "default_related_rules": '{"features": ["notes", "fixes"]}'
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_update_group_settings_invalid_json(self, client):
        """测试更新组设置时 JSON 格式无效."""
        response = client.put(
            "/api/projects/proj_001/group-settings",
            params={
                "default_related_rules": "invalid json"
            }
        )

        assert response.status_code == 400
        assert "JSON" in response.json()["detail"]
