"""REST API 自定义组条目 CRUD E2E 测试.

验证 REST API 对自定义组（包括 frontend_ 前缀）的条目 CRUD 操作支持。
此测试用于捕获 fix_20260425_1 所修复的 bug：REST API 硬编码分组校验导致自定义组条目操作被拒绝。

测试链路: REST API (18001) → Business API (18002)

覆盖场景:
  - 普通自定义组的条目 CRUD
  - frontend_ 前缀自定义组的条目 CRUD
  - 条目列表查询、详情获取、更新、删除
  - 标签管理
"""

import pytest
import sys
from pathlib import Path

# 添加 test 目录到路径
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from e2e.utils import RestClient, McpClient


pytestmark = pytest.mark.rest


def _register_tag(mcp_client: McpClient, project_id: str, tag_name: str = "test"):
    """注册测试标签（已存在则跳过）."""
    result = mcp_client.call_tool(
        "tag_register", project_id=project_id, tag_name=tag_name, summary="测试标签"
    )
    assert result["success"] is True or "已经注册" in result.get("error", "")


def _setup_project_and_group(rest_client: RestClient, mcp_client: McpClient,
                              project_name: str, group_name: str,
                              enable_status: bool = True) -> dict:
    """注册项目、注册标签、创建自定义组，返回 {"project_id": ..., "group_name": ...}."""
    reg = rest_client.post("/api/projects", json={"name": project_name})
    assert reg["success"] is True, f"注册项目失败: {reg}"
    pid = reg["data"]["project_id"]

    _register_tag(mcp_client, pid)

    grp = rest_client.post(f"/api/projects/{pid}/groups", json={
        "group_name": group_name,
        "enable_status": enable_status,
        "description": "测试自定义组",
    })
    assert grp["success"] is True, f"创建自定义组失败: {grp}"

    return {"project_id": pid, "group_name": group_name}


@pytest.mark.e2e
class TestCustomGroupItemCRUD:
    """测试普通自定义组的条目 CRUD 操作."""

    def test_create_item_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 在自定义组中创建条目."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_create", "my_tasks"
        )

        result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={
                "summary": "测试条目",
                "content": "测试内容",
                "status": "pending",
                "tags": "test",
            },
        )
        assert result["success"] is True, f"创建条目失败: {result}"
        assert "data" in result
        assert result["data"]["group"] == "my_tasks"

    def test_list_items_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 获取自定义组的条目列表."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_list", "my_backlog"
        )

        # 添加 2 个条目
        for i in range(2):
            rest_client.post(
                f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
                json={"summary": f"条目{i+1}", "content": f"内容{i+1}", "status": "pending", "tags": "test"},
            )

        # 获取列表
        result = rest_client.get(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            params={"view_mode": "summary"},
        )
        assert result["success"] is True, f"获取列表失败: {result}"
        assert result["data"]["total"] >= 2

    def test_get_item_detail_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 获取自定义组中单个条目详情."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_get", "my_notes"
        )

        # 创建条目
        create_result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "详情测试", "content": "详情内容", "status": "pending", "tags": "test"},
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item"]["id"]

        # 获取详情
        result = rest_client.get(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
        )
        assert result["success"] is True, f"获取详情失败: {result}"
        assert result["data"]["item"]["id"] == item_id
        assert result["data"]["item"]["summary"] == "详情测试"

    def test_update_item_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 更新自定义组中的条目."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_update", "my_work"
        )

        # 创建条目
        create_result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "原始摘要", "content": "原始内容", "status": "pending", "tags": "test"},
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item"]["id"]

        # 更新条目
        result = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
            json={"summary": "更新摘要", "status": "completed"},
        )
        assert result["success"] is True, f"更新条目失败: {result}"

    def test_delete_item_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 删除自定义组中的条目."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_delete", "my_temp"
        )

        # 创建条目
        create_result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "待删除", "content": "删除内容", "status": "pending", "tags": "test"},
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item"]["id"]

        # 删除条目
        result = rest_client.delete(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
        )
        assert result["success"] is True, f"删除条目失败: {result}"

    def test_manage_tags_in_custom_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 管理自定义组条目的标签，覆盖 TagService add/remove 路径."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_custom_item_tags", "my_tagged"
        )

        # 注册第二个标签供 add 操作使用
        _register_tag(mcp_client, ctx["project_id"], "test2")

        # 创建条目（带一个标签）
        create_result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "标签测试", "content": "标签内容", "status": "pending", "tags": "test"},
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item"]["id"]
        assert create_result["data"]["item"]["tags"] == ["test"]

        # 添加新标签（走 TagService.add_item_tag，标签不在 item.tags 中，会触发 save）
        result = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}/tags",
            json={"operation": "add", "tag": "test2"},
        )
        assert result["success"] is True, f"添加标签失败: {result}"
        assert "test2" in result["data"]["tags"]

        # 移除标签（走 TagService.remove_item_tag，标签在 item.tags 中，会触发 save）
        result = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}/tags",
            json={"operation": "remove", "tag": "test2"},
        )
        assert result["success"] is True, f"移除标签失败: {result}"
        assert "test2" not in result["data"]["tags"]
        assert "test" in result["data"]["tags"]


@pytest.mark.e2e
class TestFrontendGroupItemCRUD:
    """测试 frontend_ 前缀自定义组的条目 CRUD 操作."""

    def test_create_item_in_frontend_group(self, rest_client: RestClient, mcp_client: McpClient):
        """通过 REST API 在 frontend_ 前缀组中创建条目."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_frontend_item_create", "frontend_graph"
        )

        result = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "前端条目", "content": "前端内容", "status": "pending", "tags": "test"},
        )
        assert result["success"] is True, f"创建 frontend_ 组条目失败: {result}"
        assert result["data"]["group"] == "frontend_graph"

    def test_full_crud_in_frontend_group(self, rest_client: RestClient, mcp_client: McpClient):
        """在 frontend_ 前缀组中完成完整 CRUD 流程."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_frontend_full_crud", "frontend_data"
        )

        # Create
        create = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "完整CRUD测试", "content": "初始内容", "status": "pending", "tags": "test"},
        )
        assert create["success"] is True
        item_id = create["data"]["item"]["id"]

        # Read (detail)
        read = rest_client.get(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
        )
        assert read["success"] is True
        assert read["data"]["item"]["summary"] == "完整CRUD测试"

        # Update
        update = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
            json={"summary": "更新后摘要", "status": "completed"},
        )
        assert update["success"] is True

        # Delete
        delete = rest_client.delete(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}",
        )
        assert delete["success"] is True

    def test_manage_tags_in_frontend_group(self, rest_client: RestClient, mcp_client: McpClient):
        """在 frontend_ 前缀组中通过 TagService 添加/移除标签."""
        ctx = _setup_project_and_group(
            rest_client, mcp_client, "e2e_frontend_item_tags", "frontend_tagged"
        )

        # 注册额外标签
        _register_tag(mcp_client, ctx["project_id"], "frontend_tag")

        # 创建条目
        create = rest_client.post(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}",
            json={"summary": "前端标签测试", "content": "内容", "status": "pending", "tags": "test"},
        )
        assert create["success"] is True
        item_id = create["data"]["item"]["id"]

        # 添加标签（走 TagService.add_item_tag）
        add = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}/tags",
            json={"operation": "add", "tag": "frontend_tag"},
        )
        assert add["success"] is True, f"前端组添加标签失败: {add}"
        assert "frontend_tag" in add["data"]["tags"]

        # 移除标签（走 TagService.remove_item_tag）
        remove = rest_client.put(
            f"/api/projects/{ctx['project_id']}/{ctx['group_name']}/{item_id}/tags",
            json={"operation": "remove", "tag": "frontend_tag"},
        )
        assert remove["success"] is True, f"前端组移除标签失败: {remove}"
        assert "frontend_tag" not in remove["data"]["tags"]
        assert "test" in remove["data"]["tags"]

    def test_invalid_group_returns_error(self, rest_client: RestClient):
        """通过 REST API 操作不存在的分组应返回错误（由 Business 层处理）."""
        reg = rest_client.post("/api/projects", json={"name": "e2e_invalid_group"})
        pid = reg["data"]["project_id"]

        # 尝试在不存在的分组中创建条目，应抛出 HTTPError(400)
        import requests
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            rest_client.post(
                f"/api/projects/{pid}/nonexistent_group",
                json={"summary": "测试", "content": "内容", "tags": "test"},
            )
        assert "400" in str(exc_info.value), "操作不存在的分组应返回 400"
