"""MCP访问控制单元测试."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.models import ApiResponse


def _make_groups_response(groups_data):
    """构建模拟的 list_groups ApiResponse."""
    return ApiResponse(success=True, data={"groups": groups_data})


def _make_groups_list(mcp_access="writable"):
    """构建模拟的分组列表.

    Args:
        mcp_access: mcp_access 值，可以是 "writable"/"readable"/"disabled"
    """
    return [
        {"name": "features", "mcp_access": mcp_access, "count": 5},
        {"name": "fixes", "mcp_access": "writable", "count": 3},
        {"name": "notes", "mcp_access": "writable", "count": 10},
        {"name": "standards", "mcp_access": "writable", "count": 2},
    ]


class TestCheckMcpAccess:
    """_check_mcp_access 函数测试."""

    @patch("src.mcp_server.tools._shared._get_client")
    def test_writable_read_allowed(self, mock_get_client):
        """writable 组读操作应允许."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("writable")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "read")
        assert result is None

    @patch("src.mcp_server.tools._shared._get_client")
    def test_writable_write_allowed(self, mock_get_client):
        """writable 组写操作应允许."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("writable")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "write")
        assert result is None

    @patch("src.mcp_server.tools._shared._get_client")
    def test_readable_read_allowed(self, mock_get_client):
        """readable 组读操作应允许."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("readable")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "read")
        assert result is None

    @patch("src.mcp_server.tools._shared._get_client")
    def test_readable_write_denied(self, mock_get_client):
        """readable 组写操作应拒绝."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("readable")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "write")
        assert result is not None
        assert "只读" in result

    @patch("src.mcp_server.tools._shared._get_client")
    def test_disabled_read_denied(self, mock_get_client):
        """disabled 组读操作应拒绝."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("disabled")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "read")
        assert result is not None
        assert "禁止" in result

    @patch("src.mcp_server.tools._shared._get_client")
    def test_disabled_write_denied(self, mock_get_client):
        """disabled 组写操作应拒绝."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("disabled")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "write")
        assert result is not None
        assert "禁止" in result

    @patch("src.mcp_server.tools._shared._get_client")
    def test_group_not_found(self, mock_get_client):
        """不存在的分组应返回错误."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = _make_groups_response(
            _make_groups_list("writable")
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "nonexistent", "read")
        assert result is not None
        assert "未找到" in result

    @patch("src.mcp_server.tools._shared._get_client")
    def test_api_failure(self, mock_get_client):
        """API失败应返回错误."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        mock_client.list_groups.return_value = ApiResponse(
            success=False, error="项目不存在"
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "read")
        assert result is not None
        assert "失败" in result

    @patch("src.mcp_server.tools._shared._get_client")
    def test_default_mcp_access_writable(self, mock_get_client):
        """缺少 mcp_access 字段时默认为 writable."""
        from src.mcp_server.tools._shared import _check_mcp_access
        mock_client = MagicMock()
        # 不含 mcp_access 字段
        mock_client.list_groups.return_value = _make_groups_response(
            [{"name": "features", "count": 5}]
        )
        mock_get_client.return_value = mock_client

        result = _check_mcp_access("proj-1", "features", "write")
        assert result is None


class TestMcpToolAccessControl:
    """MCP工具函数访问控制集成测试."""

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_add_disabled_group(self, mock_get_client, mock_check):
        """project_add: disabled组应返回错误."""
        from src.mcp_server.tools.project import project_add
        mock_check.return_value = "分组 'standards' 已禁止MCP访问"

        result = project_add(project_id="proj-1", group="standards", summary="test")
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "禁止" in parsed["error"]
        mock_get_client.assert_not_called()

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_add_writable_group(self, mock_get_client, mock_check):
        """project_add: writable组应正常执行."""
        from src.mcp_server.tools.project import project_add
        mock_check.return_value = None
        mock_client = MagicMock()
        mock_client.project_add.return_value = ApiResponse(
            success=True, data={"item_id": "feat_20260422_1"}
        )
        mock_get_client.return_value = mock_client

        result = project_add(project_id="proj-1", group="features", summary="test")
        parsed = json.loads(result)
        assert parsed["success"] is True

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_update_readable_group(self, mock_get_client, mock_check):
        """project_update: readable组应拒绝写操作."""
        from src.mcp_server.tools.project import project_update
        mock_check.return_value = "分组 'notes' 对MCP客户端为只读，无法执行写操作"

        result = project_update(
            project_id="proj-1", group="notes", item_id="note_001"
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "只读" in parsed["error"]
        mock_get_client.assert_not_called()

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_delete_disabled_group(self, mock_get_client, mock_check):
        """project_delete: disabled组应返回错误."""
        from src.mcp_server.tools.project import project_delete
        mock_check.return_value = "分组 'standards' 已禁止MCP访问"

        result = project_delete(project_id="proj-1", group="standards", item_id="std_001")
        parsed = json.loads(result)
        assert parsed["success"] is False
        mock_get_client.assert_not_called()

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_get_disabled_group(self, mock_get_client, mock_check):
        """project_get: disabled组应拒绝读操作."""
        from src.mcp_server.tools.project import project_get
        mock_check.return_value = "分组 'standards' 已禁止MCP访问"

        result = project_get(project_id="proj-1", group_name="standards")
        parsed = json.loads(result)
        assert parsed["success"] is False
        mock_get_client.assert_not_called()

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_get_no_group_name(self, mock_get_client, mock_check):
        """project_get: 不传group_name时不检查访问控制."""
        from src.mcp_server.tools.project import project_get
        mock_client = MagicMock()
        mock_client.project_get.return_value = ApiResponse(
            success=True, data={"id": "proj-1"}
        )
        mock_get_client.return_value = mock_client

        result = project_get(project_id="proj-1")
        parsed = json.loads(result)
        assert parsed["success"] is True
        mock_check.assert_not_called()

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_project_item_tag_manage_readable_group(self, mock_get_client, mock_check):
        """project_item_tag_manage: readable组应拒绝写操作."""
        from src.mcp_server.tools.project import project_item_tag_manage
        mock_check.return_value = "分组 'notes' 对MCP客户端为只读，无法执行写操作"

        result = project_item_tag_manage(
            project_id="proj-1", group_name="notes",
            item_id="note_001", operation="add", tag="test"
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "只读" in parsed["error"]
        mock_get_client.assert_not_called()
