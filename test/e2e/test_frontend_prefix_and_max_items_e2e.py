"""frontend_ 前缀限制和 max_items 设置 E2E 测试.

测试流程:
  MCP Client  → 调用 create_custom_group → 拒绝 frontend_ 前缀
  REST Client → 创建自定义组（含 frontend_ 前缀） → 允许
  MCP Client  → 向 max_items 限制的组添加条目 → 超限时拒绝

覆盖场景:
  - MCP 创建 frontend_ 前缀自定义组被拒绝
  - REST 创建 frontend_ 前缀自定义组成功
  - MCP 创建普通自定义组成功
  - max_items=0 时无限制
  - max_items>0 时超限被拒
  - max_items>0 时未超限允许
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


@pytest.mark.e2e
class TestFrontendPrefix:
    """测试 frontend_ 前缀限制."""

    def test_mcp_reject_frontend_prefix(self, mcp_client: McpClient):
        """MCP 创建 frontend_ 前缀自定义组应被拒绝."""
        pid = _register_project(mcp_client, "e2e_frontend_prefix")

        result = mcp_client.call_tool(
            "create_custom_group",
            project_id=pid,
            group_name="frontend_tasks",
        )
        assert result["success"] is False
        assert "frontend_" in result["error"]
        assert "MCP" in result["error"]

    def test_rest_allow_frontend_prefix(self, mcp_client: McpClient, rest_client: RestClient):
        """REST 创建 frontend_ 前缀自定义组应成功."""
        pid = _register_project(mcp_client, "e2e_frontend_rest")

        result = rest_client.post(
            f"/api/projects/{pid}/groups",
            json={
                "group_name": "frontend_notes",
                "description": "前端笔记",
            },
        )
        assert result["success"] is True

        # 验证组已创建
        groups_result = mcp_client.call_tool("project_groups_list", project_id=pid)
        assert groups_result["success"] is True
        group_names = [g["name"] for g in groups_result["data"]["groups"]]
        assert "frontend_notes" in group_names

    def test_mcp_create_normal_group(self, mcp_client: McpClient):
        """MCP 创建普通自定义组应成功."""
        pid = _register_project(mcp_client, "e2e_normal_group")

        result = mcp_client.call_tool(
            "create_custom_group",
            project_id=pid,
            group_name="my_custom",
            description="自定义组",
        )
        assert result["success"] is True

        # 验证组已创建
        groups_result = mcp_client.call_tool("project_groups_list", project_id=pid)
        assert groups_result["success"] is True
        group_names = [g["name"] for g in groups_result["data"]["groups"]]
        assert "my_custom" in group_names

    def test_mcp_create_with_max_items(self, mcp_client: McpClient):
        """MCP 创建带 max_items 的自定义组应成功."""
        pid = _register_project(mcp_client, "e2e_max_items_create")

        result = mcp_client.call_tool(
            "create_custom_group",
            project_id=pid,
            group_name="limited_group",
            max_items=3,
            enable_status=True,
        )
        assert result["success"] is True

        # 验证配置中 max_items 正确
        groups_result = mcp_client.call_tool("project_groups_list", project_id=pid)
        assert groups_result["success"] is True
        for g in groups_result["data"]["groups"]:
            if g["name"] == "limited_group":
                assert g["max_items"] == 3
                break
        else:
            pytest.fail("未找到 limited_group")


@pytest.mark.e2e
class TestMaxItemsEnforcement:
    """测试 max_items 条目数量限制."""

    def test_add_within_limit(self, mcp_client: McpClient, rest_client: RestClient):
        """max_items 限制内应允许添加."""
        pid = _register_project(mcp_client, "e2e_maxitems_within")
        _register_tag(mcp_client, pid)

        # 创建 max_items=3 的组
        rest_client.post(f"/api/projects/{pid}/groups", json={
            "group_name": "limited",
            "max_items": 3,
            "enable_status": True,
        })

        # 添加 2 个条目（未超限）
        for i in range(2):
            result = mcp_client.call_tool(
                "project_add",
                project_id=pid,
                group="limited",
                summary=f"条目{i+1}",
                content=f"内容{i+1}",
                status="pending",
                tags="test",
            )
            assert result["success"] is True, f"第{i+1}个条目添加失败: {result}"

    def test_add_exceeds_limit(self, mcp_client: McpClient, rest_client: RestClient):
        """max_items 超限应拒绝添加."""
        pid = _register_project(mcp_client, "e2e_maxitems_exceed")
        _register_tag(mcp_client, pid)

        # 创建 max_items=2 的组
        rest_client.post(f"/api/projects/{pid}/groups", json={
            "group_name": "small_group",
            "max_items": 2,
            "enable_status": True,
        })

        # 添加 2 个条目（达到上限）
        for i in range(2):
            result = mcp_client.call_tool(
                "project_add",
                project_id=pid,
                group="small_group",
                summary=f"条目{i+1}",
                content=f"内容{i+1}",
                status="pending",
                tags="test",
            )
            assert result["success"] is True, f"第{i+1}个条目添加失败: {result}"

        # 第 3 个条目应被拒绝
        result = mcp_client.call_tool(
            "project_add",
            project_id=pid,
            group="small_group",
            summary="超限条目",
            content="超限内容",
            status="pending",
            tags="test",
        )
        assert result["success"] is False
        assert "最大条目数量限制" in result["error"]
        assert "2" in result["error"]

    def test_max_items_zero_no_limit(self, mcp_client: McpClient, rest_client: RestClient):
        """max_items=0 时无限制."""
        pid = _register_project(mcp_client, "e2e_maxitems_zero")
        _register_tag(mcp_client, pid)

        # 创建 max_items=0 的组
        rest_client.post(f"/api/projects/{pid}/groups", json={
            "group_name": "unlimited",
            "max_items": 0,
            "enable_status": True,
        })

        # 添加多个条目都应成功
        for i in range(5):
            result = mcp_client.call_tool(
                "project_add",
                project_id=pid,
                group="unlimited",
                summary=f"条目{i+1}",
                content=f"内容{i+1}",
                status="pending",
                tags="test",
            )
            assert result["success"] is True, f"第{i+1}个条目添加失败: {result}"
