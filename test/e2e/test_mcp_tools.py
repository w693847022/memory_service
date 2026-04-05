"""MCP Server 端到端测试.

测试 MCP Server (8000) → Business API (8002) 的转发功能。
使用 MCP 协议 (JSON-RPC 2.0) 调用 MCP Server 工具接口。
"""

import pytest
import sys
from pathlib import Path

# 添加 test 目录到路径
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from e2e.utils import McpClient


pytestmark = pytest.mark.mcp


@pytest.mark.e2e
class TestMcpProjectTools:
    """测试项目管理相关 MCP 工具."""

    def test_project_register(self, mcp_client: McpClient):
        """测试 project_register 工具."""
        result = mcp_client.call_tool(
            "project_register",
            name="测试项目",
            path="/tmp/test_project",
            summary="项目摘要",
            tags="test,e2e"
        )

        assert result["success"] is True, f"注册项目失败: {result}"
        assert "data" in result
        assert "project_id" in result["data"]

    def test_project_list(self, mcp_client: McpClient):
        """测试 project_list 工具."""
        # 先注册一个项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="列表测试项目"
        )
        assert register_result["success"] is True

        # 获取项目列表
        result = mcp_client.call_tool("project_list")

        assert result["success"] is True
        assert "data" in result
        assert "projects" in result["data"]

    def test_project_get(self, mcp_client: McpClient):
        """测试 project_get 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="查询测试项目"
        )
        project_id = register_result["data"]["project_id"]

        # 查询项目
        result = mcp_client.call_tool(
            "project_get",
            project_id=project_id
        )

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["info"]["name"] == "查询测试项目"

    def test_project_rename(self, mcp_client: McpClient):
        """测试 project_rename 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="旧名称_mcp"
        )
        project_id = register_result["data"]["project_id"]

        # 重命名
        result = mcp_client.call_tool(
            "project_rename",
            project_id=project_id,
            new_name="新名称_mcp"
        )

        assert result["success"] is True

        # 验证重命名成功
        get_result = mcp_client.call_tool("project_get", project_id=project_id)
        assert get_result["data"]["info"]["name"] == "新名称_mcp"

    def test_project_remove(self, mcp_client: McpClient):
        """测试 project_remove 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="待删除项目"
        )
        project_id = register_result["data"]["project_id"]

        # 删除项目
        result = mcp_client.call_tool(
            "project_remove",
            project_id=project_id,
            mode="delete"
        )

        assert result["success"] is True

    def test_project_groups_list(self, mcp_client: McpClient):
        """测试 project_groups_list 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="分组测试项目"
        )
        project_id = register_result["data"]["project_id"]

        # 获取分组列表
        result = mcp_client.call_tool(
            "project_groups_list",
            project_id=project_id
        )

        assert result["success"] is True
        assert "data" in result
        assert "groups" in result["data"]

    def test_project_tags_info(self, mcp_client: McpClient):
        """测试 project_tags_info 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签测试项目"
        )
        project_id = register_result["data"]["project_id"]

        # 获取标签信息
        result = mcp_client.call_tool(
            "project_tags_info",
            project_id=project_id
        )

        assert result["success"] is True
        assert "data" in result


@pytest.mark.e2e
class TestMcpItemTools:
    """测试条目管理相关 MCP 工具."""

    def test_project_add_feature(self, mcp_client: McpClient):
        """测试 project_add 添加功能."""
        # 先注册项目并注册标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="功能测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="测试标签"
        )

        # 添加功能
        result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="features",
            summary="测试功能",
            content="功能详细描述",
            status="pending",
            tags="test"
        )

        assert result["success"] is True
        assert "data" in result
        assert "item_id" in result["data"]

    def test_project_add_note(self, mcp_client: McpClient):
        """测试 project_add 添加笔记."""
        # 先注册项目并注册标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="笔记测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="测试标签"
        )

        # 添加笔记
        result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="notes",
            summary="测试笔记",
            content="笔记内容",
            tags="test"
        )

        assert result["success"] is True

    def test_project_add_fix(self, mcp_client: McpClient):
        """测试 project_add 添加修复."""
        # 先注册项目并注册标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="修复测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="测试标签"
        )

        # 添加修复
        result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="fixes",
            summary="修复bug",
            content="修复描述",
            status="completed",
            severity="medium",
            tags="test"
        )

        assert result["success"] is True

    def test_project_update(self, mcp_client: McpClient):
        """测试 project_update 工具."""
        # 先注册项目并添加条目
        register_result = mcp_client.call_tool(
            "project_register",
            name="更新测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="测试标签"
        )

        add_result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="features",
            summary="原始功能",
            content="原始内容",
            status="pending",
            tags="test"
        )
        item_id = add_result["data"]["item_id"]

        # 更新条目
        result = mcp_client.call_tool(
            "project_update",
            project_id=project_id,
            group="features",
            item_id=item_id,
            summary="更新后的功能",
            status="in_progress"
        )

        assert result["success"] is True

    def test_project_delete(self, mcp_client: McpClient):
        """测试 project_delete 工具."""
        # 先注册项目并添加条目
        register_result = mcp_client.call_tool(
            "project_register",
            name="删除测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="测试标签"
        )

        add_result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="features",
            summary="待删除功能",
            content="内容",
            status="pending",
            tags="test"
        )
        item_id = add_result["data"]["item_id"]

        # 删除条目
        result = mcp_client.call_tool(
            "project_delete",
            project_id=project_id,
            group="features",
            item_id=item_id
        )

        assert result["success"] is True

    def test_project_item_tag_manage(self, mcp_client: McpClient):
        """测试 project_item_tag_manage 工具."""
        # 先注册项目并注册标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签管理测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test1",
            summary="测试标签1"
        )
        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test2",
            summary="测试标签2"
        )

        add_result = mcp_client.call_tool(
            "project_add",
            project_id=project_id,
            group="features",
            summary="测试功能",
            content="内容",
            status="pending",
            tags="test1"
        )
        item_id = add_result["data"]["item_id"]

        # 替换标签
        result = mcp_client.call_tool(
            "project_item_tag_manage",
            project_id=project_id,
            group_name="features",
            item_id=item_id,
            operation="set",
            tags="test2"
        )

        assert result["success"] is True


@pytest.mark.e2e
class TestMcpTagTools:
    """测试标签管理相关 MCP 工具."""

    def test_tag_register(self, mcp_client: McpClient):
        """测试 tag_register 工具."""
        # 先注册项目
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签注册测试项目"
        )
        project_id = register_result["data"]["project_id"]

        # 注册标签
        result = mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="api",
            summary="API相关",
            aliases="接口"
        )

        assert result["success"] is True

    def test_tag_update(self, mcp_client: McpClient):
        """测试 tag_update 工具."""
        # 先注册项目和标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签更新测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="test",
            summary="原始摘要"
        )

        # 更新标签
        result = mcp_client.call_tool(
            "tag_update",
            project_id=project_id,
            tag_name="test",
            summary="新摘要"
        )

        assert result["success"] is True

    def test_tag_delete(self, mcp_client: McpClient):
        """测试 tag_delete 工具."""
        # 先注册项目和标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签删除测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="unused",
            summary="未使用标签"
        )

        # 删除标签
        result = mcp_client.call_tool(
            "tag_delete",
            project_id=project_id,
            tag_name="unused",
            force="true"
        )

        assert result["success"] is True

    def test_tag_merge(self, mcp_client: McpClient):
        """测试 tag_merge 工具."""
        # 先注册项目和两个标签
        register_result = mcp_client.call_tool(
            "project_register",
            name="标签合并测试项目"
        )
        project_id = register_result["data"]["project_id"]

        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="old_tag",
            summary="旧标签"
        )
        mcp_client.call_tool(
            "tag_register",
            project_id=project_id,
            tag_name="new_tag",
            summary="新标签"
        )

        # 合并标签
        result = mcp_client.call_tool(
            "tag_merge",
            project_id=project_id,
            old_tag="old_tag",
            new_tag="new_tag"
        )

        assert result["success"] is True
