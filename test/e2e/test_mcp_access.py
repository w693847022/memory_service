"""mcp_access 访问控制 E2E 测试.

测试流程:
  REST Client → 创建/更新分组 mcp_access → Business Server 持久化
  MCP Client  → 调用 MCP 工具 → MCP Server 检查 _check_mcp_access → Business Server 获取分组配置

覆盖场景:
  - 内置组 disabled: 读写均被拒绝
  - 内置组 readable: 读允许、写拒绝
  - 内置组 writable: 读写均允许
  - 自定义组 disabled: 写操作被拒绝（MCP 层拦截）
  - 恢复 writable 后权限恢复正常
"""

import pytest
import sys
from pathlib import Path

# 添加 test 目录到路径
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from e2e.utils import McpClient, RestClient


pytestmark = pytest.mark.mcp


def _register_project(mcp_client: McpClient, name: str) -> str:
    """注册测试项目并返回 project_id."""
    result = mcp_client.call_tool("project_register", name=name)
    assert result["success"] is True, f"注册项目失败: {result}"
    return result["data"]["project_id"]


def _register_tag(mcp_client: McpClient, project_id: str, tag_name: str = "test"):
    """注册测试标签（已存在则跳过）."""
    result = mcp_client.call_tool(
        "tag_register", project_id=project_id, tag_name=tag_name, summary="测试标签"
    )
    assert result["success"] is True or "已经注册" in result.get("error", "")


def _add_item(mcp_client: McpClient, project_id: str, group: str) -> str:
    """添加测试条目并返回 item_id."""
    result = mcp_client.call_tool(
        "project_add",
        project_id=project_id,
        group=group,
        summary="测试条目",
        content="测试内容",
        status="pending",
        tags="test",
    )
    assert result["success"] is True, f"添加条目失败: {result}"
    return result["data"]["item_id"]


def _set_mcp_access(rest_client: RestClient, project_id: str, group: str, mcp_access: str):
    """通过 REST API 更新分组 mcp_access."""
    result = rest_client.put(
        f"/api/projects/{project_id}/groups/{group}",
        json={"mcp_access": mcp_access},
    )
    assert result["success"] is True, f"更新 mcp_access 失败: {result}"


def _assert_denied(result: dict, reason: str = ""):
    """断言访问被拒绝."""
    assert result["success"] is False, f"期望被拒绝但操作成功了: {result}"
    assert "error" in result
    if reason == "disabled":
        assert "已禁止MCP访问" in result["error"]
    elif reason == "readonly":
        assert "只读" in result["error"]


def _assert_allowed(result: dict):
    """断言访问被允许."""
    assert result["success"] is True, f"期望成功但被拒绝: {result}"


@pytest.mark.e2e
class TestMcpAccessControl:
    """测试分组级别 MCP 访问控制.

    使用 features/notes/fixes 内置组进行测试，
    通过 REST API 动态修改 mcp_access 值来验证权限。
    """

    # ---- 场景1: disabled - 读写均被拒绝 ----

    def test_disabled_read_denied(self, mcp_client: McpClient, rest_client: RestClient):
        """disabled: 读操作被拒绝."""
        pid = _register_project(mcp_client, "mcp_access_disabled读")
        _register_tag(mcp_client, pid)
        _add_item(mcp_client, pid, "features")

        _set_mcp_access(rest_client, pid, "features", "disabled")

        # project_get 应被拒绝
        result = mcp_client.call_tool("project_get", project_id=pid, group_name="features")
        _assert_denied(result, "disabled")

        # project_tags_info 应被拒绝
        result = mcp_client.call_tool("project_tags_info", project_id=pid, group_name="features")
        _assert_denied(result, "disabled")

        # 恢复
        _set_mcp_access(rest_client, pid, "features", "writable")

    def test_disabled_write_denied(self, mcp_client: McpClient, rest_client: RestClient):
        """disabled: 写操作被拒绝."""
        pid = _register_project(mcp_client, "mcp_access_disabled写")
        _register_tag(mcp_client, pid)

        _set_mcp_access(rest_client, pid, "notes", "disabled")

        # project_add 应被拒绝
        result = mcp_client.call_tool(
            "project_add", project_id=pid, group="notes", summary="test", tags="test"
        )
        _assert_denied(result, "disabled")

        # 恢复
        _set_mcp_access(rest_client, pid, "notes", "writable")

    # ---- 场景2: readable - 读允许、写拒绝 ----

    def test_readable_read_allowed(self, mcp_client: McpClient, rest_client: RestClient):
        """readable: 读操作允许."""
        pid = _register_project(mcp_client, "mcp_access_readable读")
        _register_tag(mcp_client, pid)
        _add_item(mcp_client, pid, "features")

        _set_mcp_access(rest_client, pid, "features", "readable")

        # project_get 应允许
        result = mcp_client.call_tool("project_get", project_id=pid, group_name="features")
        _assert_allowed(result)

        # project_tags_info 应允许
        result = mcp_client.call_tool("project_tags_info", project_id=pid, group_name="features")
        _assert_allowed(result)

        # 恢复
        _set_mcp_access(rest_client, pid, "features", "writable")

    def test_readable_write_denied(self, mcp_client: McpClient, rest_client: RestClient):
        """readable: 写操作被拒绝."""
        pid = _register_project(mcp_client, "mcp_access_readable写")
        _register_tag(mcp_client, pid)
        item_id = _add_item(mcp_client, pid, "fixes")

        _set_mcp_access(rest_client, pid, "fixes", "readable")

        # project_add 应被拒绝
        result = mcp_client.call_tool(
            "project_add", project_id=pid, group="fixes", summary="test",
            content="c", severity="low", tags="test"
        )
        _assert_denied(result, "readonly")

        # project_update 应被拒绝
        result = mcp_client.call_tool(
            "project_update", project_id=pid, group="fixes",
            item_id=item_id, summary="updated"
        )
        _assert_denied(result, "readonly")

        # project_delete 应被拒绝
        result = mcp_client.call_tool(
            "project_delete", project_id=pid, group="fixes", item_id=item_id
        )
        _assert_denied(result, "readonly")

        # project_item_tag_manage 应被拒绝
        result = mcp_client.call_tool(
            "project_item_tag_manage",
            project_id=pid, group_name="fixes", item_id=item_id,
            operation="set", tags="test"
        )
        _assert_denied(result, "readonly")

        # 恢复
        _set_mcp_access(rest_client, pid, "fixes", "writable")

    # ---- 场景3: writable - 读写均允许 ----

    def test_writable_full_access(self, mcp_client: McpClient):
        """writable: 读写均允许."""
        pid = _register_project(mcp_client, "mcp_access_writable")
        _register_tag(mcp_client, pid)

        # features 默认 writable，验证写操作
        add_result = mcp_client.call_tool(
            "project_add",
            project_id=pid, group="features",
            summary="测试条目", content="内容", status="pending", tags="test",
        )
        _assert_allowed(add_result)
        item_id = add_result["data"]["item_id"]

        # project_update
        result = mcp_client.call_tool(
            "project_update", project_id=pid, group="features",
            item_id=item_id, summary="更新后",
        )
        _assert_allowed(result)

        # project_get
        result = mcp_client.call_tool("project_get", project_id=pid, group_name="features")
        _assert_allowed(result)

        # project_item_tag_manage
        result = mcp_client.call_tool(
            "project_item_tag_manage",
            project_id=pid, group_name="features", item_id=item_id,
            operation="set", tags="test",
        )
        _assert_allowed(result)

        # project_delete
        result = mcp_client.call_tool(
            "project_delete", project_id=pid, group="features", item_id=item_id
        )
        _assert_allowed(result)

    # ---- 场景4: 自定义组 disabled - MCP 层拦截 ----

    def test_custom_group_disabled_write_denied(self, mcp_client: McpClient, rest_client: RestClient):
        """自定义组 disabled: 写操作被 MCP 层拦截."""
        pid = _register_project(mcp_client, "mcp_access_custom_disabled")
        group = "custom_grp_disabled"

        # 通过 REST 创建自定义组, mcp_access=disabled
        rest_client.post(f"/api/projects/{pid}/groups", json={
            "group_name": group,
            "mcp_access": "disabled",
        })

        # MCP 写操作应在 _check_mcp_access 层被拦截
        result = mcp_client.call_tool(
            "project_add", project_id=pid, group=group, summary="test", tags="test"
        )
        _assert_denied(result, "disabled")

        # MCP 读操作也应被拦截
        result = mcp_client.call_tool("project_get", project_id=pid, group_name=group)
        _assert_denied(result, "disabled")

    # ---- 场景5: 恢复 writable 后权限恢复 ----

    def test_restore_writable_restores_access(self, mcp_client: McpClient, rest_client: RestClient):
        """从 readable 恢复为 writable 后权限恢复正常."""
        pid = _register_project(mcp_client, "mcp_access_restore")
        _register_tag(mcp_client, pid)

        # 先改为 readable
        _set_mcp_access(rest_client, pid, "features", "readable")

        # 验证写操作被拒绝
        result = mcp_client.call_tool(
            "project_add", project_id=pid, group="features", summary="test", tags="test"
        )
        _assert_denied(result, "readonly")

        # 恢复为 writable
        _set_mcp_access(rest_client, pid, "features", "writable")

        # 写操作应恢复
        add_result = mcp_client.call_tool(
            "project_add",
            project_id=pid, group="features",
            summary="恢复后添加", content="内容", status="pending", tags="test",
        )
        _assert_allowed(add_result)
        item_id = add_result["data"]["item_id"]

        # 读操作正常
        result = mcp_client.call_tool("project_get", project_id=pid, group_name="features")
        _assert_allowed(result)

        # 更新和删除正常
        result = mcp_client.call_tool(
            "project_update", project_id=pid, group="features",
            item_id=item_id, summary="更新",
        )
        _assert_allowed(result)

        result = mcp_client.call_tool(
            "project_delete", project_id=pid, group="features", item_id=item_id
        )
        _assert_allowed(result)
