"""frontend_ 前缀限制和 max_items 设置单元测试."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.models import ApiResponse
from src.models.group import UnifiedGroupConfig, DEFAULT_GROUP_CONFIGS, FRONTEND_GROUP_PREFIX


class TestMaxItemsField:
    """UnifiedGroupConfig max_items 字段测试."""

    def test_default_max_items_is_zero(self):
        """默认 max_items 应为 0（无限制）."""
        config = UnifiedGroupConfig()
        assert config.max_items == 0

    def test_custom_max_items(self):
        """自定义 max_items 应正确设置."""
        config = UnifiedGroupConfig(max_items=100)
        assert config.max_items == 100

    def test_max_items_zero_means_unlimited(self):
        """max_items=0 表示无限制."""
        config = UnifiedGroupConfig(max_items=0)
        assert config.max_items == 0

    def test_from_dict_with_max_items(self):
        """from_dict 应正确加载 max_items."""
        config = UnifiedGroupConfig.from_dict({"max_items": 50})
        assert config.max_items == 50

    def test_from_dict_default_max_items(self):
        """from_dict 不提供 max_items 时默认为 0."""
        config = UnifiedGroupConfig.from_dict({})
        assert config.max_items == 0

    def test_to_dict_includes_max_items(self):
        """to_dict 应包含 max_items 字段."""
        config = UnifiedGroupConfig(max_items=10)
        d = config.to_dict()
        assert "max_items" in d
        assert d["max_items"] == 10


class TestDefaultGroupConfigsMaxItems:
    """默认组配置 max_items 字段测试."""

    def test_all_defaults_have_max_items(self):
        """所有默认组配置都应包含 max_items 字段."""
        for group_name, group_config in DEFAULT_GROUP_CONFIGS.items():
            assert "max_items" in group_config, f"{group_name} 缺少 max_items 字段"

    def test_all_defaults_max_items_is_zero(self):
        """所有默认组配置的 max_items 应为 0（无限制）."""
        for group_name, group_config in DEFAULT_GROUP_CONFIGS.items():
            assert group_config["max_items"] == 0, f"{group_name} 的 max_items 应为 0"


class TestFrontendGroupPrefix:
    """frontend_ 前缀常量测试."""

    def test_frontend_prefix_constant_exists(self):
        """FRONTEND_GROUP_PREFIX 常量应存在."""
        assert FRONTEND_GROUP_PREFIX == "frontend_"

    def test_frontend_prefix_starts_with(self):
        """frontend_ 前缀检测应正确工作."""
        assert "frontend_tasks".startswith(FRONTEND_GROUP_PREFIX)
        assert "frontend_".startswith(FRONTEND_GROUP_PREFIX)
        assert not "mygroup".startswith(FRONTEND_GROUP_PREFIX)
        assert not "my_frontend".startswith(FRONTEND_GROUP_PREFIX)


class TestMcpCreateCustomGroup:
    """MCP create_custom_group 工具函数测试."""

    @patch("src.mcp_server.tools.group._get_client")
    def test_frontend_prefix_rejected(self, mock_get_client):
        """frontend_ 前缀应被拒绝."""
        from src.mcp_server.tools.group import create_custom_group
        result = create_custom_group(
            project_id="proj-1",
            group_name="frontend_tasks",
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "frontend_" in parsed["error"]
        assert "MCP" in parsed["error"]
        mock_get_client.assert_not_called()

    @patch("src.mcp_server.tools.group._get_client")
    def test_frontend_prefix_exact_rejected(self, mock_get_client):
        """frontend_ 精确前缀应被拒绝."""
        from src.mcp_server.tools.group import create_custom_group
        result = create_custom_group(
            project_id="proj-1",
            group_name="frontend_",
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "frontend_" in parsed["error"]

    @patch("src.mcp_server.tools.group._get_client")
    def test_normal_name_allowed(self, mock_get_client):
        """正常名称应允许创建."""
        from src.mcp_server.tools.group import create_custom_group
        mock_client = MagicMock()
        mock_client.create_custom_group.return_value = ApiResponse(
            success=True, data={"project_id": "proj-1", "group_name": "mygroup"}
        )
        mock_get_client.return_value = mock_client

        result = create_custom_group(
            project_id="proj-1",
            group_name="mygroup",
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
        mock_client.create_custom_group.assert_called_once()

    @patch("src.mcp_server.tools.group._get_client")
    def test_max_items_passed_through(self, mock_get_client):
        """max_items 应正确传递到 Business 层."""
        from src.mcp_server.tools.group import create_custom_group
        mock_client = MagicMock()
        mock_client.create_custom_group.return_value = ApiResponse(
            success=True, data={"project_id": "proj-1", "group_name": "limited"}
        )
        mock_get_client.return_value = mock_client

        result = create_custom_group(
            project_id="proj-1",
            group_name="limited",
            max_items=50,
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
        call_kwargs = mock_client.create_custom_group.call_args[1]
        assert call_kwargs["max_items"] == 50

    @patch("src.mcp_server.tools.group._get_client")
    def test_non_frontend_prefix_with_underscore_allowed(self, mock_get_client):
        """非 frontend_ 前缀但有下划线的名称应允许."""
        from src.mcp_server.tools.group import create_custom_group
        mock_client = MagicMock()
        mock_client.create_custom_group.return_value = ApiResponse(
            success=True, data={"project_id": "proj-1", "group_name": "my_group"}
        )
        mock_get_client.return_value = mock_client

        result = create_custom_group(
            project_id="proj-1",
            group_name="my_group",
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
