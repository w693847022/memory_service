"""REST API 端到端测试.

测试 REST API (8001) → Business API (8002) 的转发功能。
使用 HTTP REST 调用 REST API 接口。
"""

import pytest
import sys
from pathlib import Path

# 添加 test 目录到路径
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from e2e.utils import RestClient


pytestmark = pytest.mark.rest


@pytest.mark.e2e
class TestRestProjects:
    """测试项目管理 REST API."""

    def test_list_projects(self, rest_client: RestClient):
        """测试获取项目列表."""
        # 先注册一个项目
        rest_client.post("/api/projects", params={
            "name": "测试项目",
            "path": "/tmp/test"
        })

        # 获取项目列表
        result = rest_client.get("/api/projects")

        assert result["success"] is True
        assert "data" in result
        assert "projects" in result["data"]
        assert result["data"]["total"] >= 1

    def test_register_project(self, rest_client: RestClient):
        """测试注册项目."""
        result = rest_client.post("/api/projects", params={
            "name": "新项目",
            "path": "/tmp/new_project",
            "summary": "项目摘要",
            "tags": "test,e2e"
        })

        assert result["success"] is True
        assert "data" in result
        assert "project_id" in result["data"]

    def test_get_project(self, rest_client: RestClient):
        """测试获取项目详情."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "查询测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 获取项目详情
        result = rest_client.get(f"/api/projects/{project_id}")

        assert result["success"] is True
        assert result["data"]["info"]["name"] == "查询测试项目"

    def test_rename_project(self, rest_client: RestClient):
        """测试重命名项目."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "rest_rename_old"
        })
        project_id = register_result["data"]["project_id"]

        # 重命名
        result = rest_client.put(
            f"/api/projects/{project_id}/rename",
            params={"new_name": "rest_rename_new"}
        )

        assert result["success"] is True        # 验证重命名成功
        get_result = rest_client.get(f"/api/projects/{project_id}")
        assert get_result["data"]["info"]["name"] == "rest_rename_new"

    def test_delete_project(self, rest_client: RestClient):
        """测试删除项目."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "待删除项目"
        })
        project_id = register_result["data"]["project_id"]

        # 删除项目
        result = rest_client.delete(
            f"/api/projects/{project_id}",
            params={"mode": "delete"}
        )

        assert result["success"] is True

    def test_list_project_groups(self, rest_client: RestClient):
        """测试获取项目分组列表."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "分组测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 获取分组列表
        result = rest_client.get(f"/api/projects/{project_id}/groups")

        assert result["success"] is True
        assert "data" in result
        assert "groups" in result["data"]

    def test_list_project_tags(self, rest_client: RestClient):
        """测试获取项目标签信息."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "标签测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 获取标签信息
        result = rest_client.get(f"/api/projects/{project_id}/tags")

        assert result["success"] is True
        assert "data" in result


@pytest.mark.e2e
class TestRestGroups:
    """测试分组管理 REST API."""

    def test_create_custom_group(self, rest_client: RestClient):
        """测试创建自定义分组."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "自定义分组测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 创建自定义分组
        result = rest_client.post("/api/groups/custom", params={
            "project_id": project_id,
            "group_name": "custom_backlog",
            "content_max_bytes": 500,
            "summary_max_bytes": 100
        })

        assert result["success"] is True

    def test_get_group_settings(self, rest_client: RestClient):
        """测试获取分组设置."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "分组设置测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 获取分组设置
        result = rest_client.get("/api/groups/settings", params={
            "project_id": project_id
        })

        assert result["success"] is True
        assert "data" in result


@pytest.mark.e2e
class TestRestTags:
    """测试标签管理 REST API."""

    def test_register_tag(self, rest_client: RestClient):
        """测试注册标签."""
        # 先注册项目
        register_result = rest_client.post("/api/projects", params={
            "name": "标签注册测试项目"
        })
        project_id = register_result["data"]["project_id"]

        # 注册标签
        result = rest_client.post("/api/tags/register", params={
            "project_id": project_id,
            "tag_name": "api",
            "summary": "API相关",
            "aliases": "接口"
        })

        assert result["success"] is True

    def test_update_tag(self, rest_client: RestClient):
        """测试更新标签."""
        # 先注册项目和标签
        register_result = rest_client.post("/api/projects", params={
            "name": "标签更新测试项目"
        })
        project_id = register_result["data"]["project_id"]

        rest_client.post("/api/tags/register", params={
            "project_id": project_id,
            "tag_name": "test_update_tag",
            "summary": "原始摘要"
        })

        # 更新标签
        result = rest_client.put("/api/tags/update", params={
            "project_id": project_id,
            "tag_name": "test_update_tag",
            "summary": "新摘要"
        })

        assert result["success"] is True

    def test_delete_tag(self, rest_client: RestClient):
        """测试删除标签."""
        # 先注册项目和标签
        register_result = rest_client.post("/api/projects", params={
            "name": "标签删除测试项目"
        })
        project_id = register_result["data"]["project_id"]

        rest_client.post("/api/tags/register", params={
            "project_id": project_id,
            "tag_name": "unused",
            "summary": "未使用标签"
        })

        # 删除标签
        result = rest_client.delete("/api/tags/delete", params={
            "project_id": project_id,
            "tag_name": "unused",
            "force": "true"
        })

        assert result["success"] is True

    def test_merge_tags(self, rest_client: RestClient):
        """测试合并标签."""
        # 先注册项目和两个标签
        register_result = rest_client.post("/api/projects", params={
            "name": "标签合并测试项目"
        })
        project_id = register_result["data"]["project_id"]

        rest_client.post("/api/tags/register", params={
            "project_id": project_id,
            "tag_name": "old_tag",
            "summary": "旧标签"
        })
        rest_client.post("/api/tags/register", params={
            "project_id": project_id,
            "tag_name": "new_tag",
            "summary": "新标签"
        })

        # 合并标签
        result = rest_client.post("/api/tags/merge", params={
            "project_id": project_id,
            "old_tag": "old_tag",
            "new_tag": "new_tag"
        })

        assert result["success"] is True


@pytest.mark.e2e
class TestRestStats:
    """测试统计 REST API."""

    def test_project_stats(self, rest_client: RestClient):
        """测试获取全局统计."""
        result = rest_client.get("/api/stats")

        assert result["success"] is True
        assert "data" in result

    def test_stats_summary(self, rest_client: RestClient):
        """测试获取统计摘要."""
        result = rest_client.get("/api/stats/summary", params={
            "type": "tool_call",
            "page": 1,
            "size": 10
        })

        assert result["success"] is True
        assert "data" in result


@pytest.mark.e2e
class TestRestHealth:
    """测试健康检查 REST API."""

    def test_health_check(self, rest_client: RestClient):
        """测试健康检查接口."""
        result = rest_client.get("/health")

        assert result["success"] is True
        assert result["data"]["status"] == "healthy"

    def test_root_endpoint(self, rest_client: RestClient):
        """测试根路径."""
        result = rest_client.get("/")

        assert result["success"] is True
        assert "data" in result
        assert "name" in result["data"]
