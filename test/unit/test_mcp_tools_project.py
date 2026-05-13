"""MCP 工具 project_add/project_update 单元测试."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.models import ApiResponse


def _make_success_response():
    """构建成功的 ApiResponse."""
    return ApiResponse(success=True, message="操作成功", data={"item_id": "feat_20260512_1"})


class TestProjectAdd:
    """project_add 工具测试."""

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_dict_content_converted_to_json(self, mock_get_client, mock_check_access):
        """dict 类型的 content 应自动转为 JSON 字符串."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_add.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_add
        result = project_add(
            project_id="proj-1",
            group="features",
            content={"key": "value", "num": 42},
            summary="测试"
        )

        call_kwargs = mock_client.project_add.call_args.kwargs
        assert call_kwargs["content"] == '{"key": "value", "num": 42}'

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_str_content_unchanged(self, mock_get_client, mock_check_access):
        """str 类型的 content 应保持不变."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_add.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_add
        result = project_add(
            project_id="proj-1",
            group="features",
            content="原始内容",
            summary="测试"
        )

        call_kwargs = mock_client.project_add.call_args.kwargs
        assert call_kwargs["content"] == "原始内容"

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_list_content_converted_to_json(self, mock_get_client, mock_check_access):
        """list 类型的 content 应自动转为 JSON 字符串."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_add.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_add
        result = project_add(
            project_id="proj-1",
            group="features",
            content=[{"id": 1}, {"id": 2}],
            summary="测试"
        )

        call_kwargs = mock_client.project_add.call_args.kwargs
        assert call_kwargs["content"] == '[{"id": 1}, {"id": 2}]'

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_dict_content_ensure_ascii_false(self, mock_get_client, mock_check_access):
        """dict 类型的 content 含 unicode 字符时应保持可读（ensure_ascii=False）."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_add.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_add
        result = project_add(
            project_id="proj-1",
            group="features",
            content={"label": "中文"},
            summary="测试"
        )

        call_kwargs = mock_client.project_add.call_args.kwargs
        assert call_kwargs["content"] == '{"label": "中文"}'
        # 确保不是 ensure_ascii=True 的转义形式
        assert "\\u" not in call_kwargs["content"]


class TestProjectUpdate:
    """project_update 工具测试."""

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_dict_content_converted_to_json(self, mock_get_client, mock_check_access):
        """dict 类型的 content 应自动转为 JSON 字符串."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_update.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_update
        result = project_update(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content={"update": "value"},
            summary="更新测试"
        )

        call_kwargs = mock_client.project_update.call_args.kwargs
        assert call_kwargs["content"] == '{"update": "value"}'

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_str_content_unchanged(self, mock_get_client, mock_check_access):
        """str 类型的 content 应保持不变."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_update.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_update
        result = project_update(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content="原始更新内容",
            summary="更新测试"
        )

        call_kwargs = mock_client.project_update.call_args.kwargs
        assert call_kwargs["content"] == "原始更新内容"

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_list_content_converted_to_json(self, mock_get_client, mock_check_access):
        """list 类型的 content 应自动转为 JSON 字符串."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_update.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_update
        result = project_update(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content=[{"update": 1}, {"update": 2}],
            summary="更新测试"
        )

        call_kwargs = mock_client.project_update.call_args.kwargs
        assert call_kwargs["content"] == '[{"update": 1}, {"update": 2}]'

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_dict_content_ensure_ascii_false(self, mock_get_client, mock_check_access):
        """dict 类型的 content 含 unicode 字符时应保持可读（ensure_ascii=False）."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_update.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_update
        result = project_update(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content={"label": "中文"},
            summary="更新测试"
        )

        call_kwargs = mock_client.project_update.call_args.kwargs
        assert call_kwargs["content"] == '{"label": "中文"}'
        assert "\\u" not in call_kwargs["content"]

    @patch("src.mcp_server.tools.project._check_mcp_access")
    @patch("src.mcp_server.tools.project._get_client")
    def test_dict_related_converted_to_json(self, mock_get_client, mock_check_access):
        """dict 类型的 related 应自动转为 JSON 字符串（现有功能回归测试）."""
        mock_check_access.return_value = None
        mock_client = MagicMock()
        mock_client.project_update.return_value = _make_success_response()
        mock_get_client.return_value = mock_client

        from src.mcp_server.tools.project import project_update
        result = project_update(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            related={"features": ["feat_20260512_2"]},
        )

        call_kwargs = mock_client.project_update.call_args.kwargs
        assert call_kwargs["related"] == '{"features": ["feat_20260512_2"]}'


class TestContentTypeAnnotation:
    """验证 content 参数类型注解允许 dict/list 通过 Pydantic 校验."""

    def test_project_add_content_accepts_dict(self):
        """project_add 的 content 参数类型注解应允许 dict 通过 Pydantic 校验."""
        import inspect
        from pydantic import create_model
        from src.mcp_server.tools.project import project_add

        sig = inspect.signature(project_add)
        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        ToolModel = create_model("project_add_model", **fields)
        validated = ToolModel(
            project_id="proj-1",
            group="features",
            content={"key": "value"},
            summary="测试"
        )
        assert validated.content == {"key": "value"}

    def test_project_add_content_accepts_list(self):
        """project_add 的 content 参数类型注解应允许 list 通过 Pydantic 校验."""
        import inspect
        from pydantic import create_model
        from src.mcp_server.tools.project import project_add

        sig = inspect.signature(project_add)
        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        ToolModel = create_model("project_add_model", **fields)
        validated = ToolModel(
            project_id="proj-1",
            group="features",
            content=[1, 2, 3],
            summary="测试"
        )
        assert validated.content == [1, 2, 3]

    def test_project_update_content_accepts_dict(self):
        """project_update 的 content 参数类型注解应允许 dict 通过 Pydantic 校验."""
        import inspect
        from pydantic import create_model
        from src.mcp_server.tools.project import project_update

        sig = inspect.signature(project_update)
        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        ToolModel = create_model("project_update_model", **fields)
        validated = ToolModel(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content={"update": "value"},
        )
        assert validated.content == {"update": "value"}

    def test_project_update_content_accepts_list(self):
        """project_update 的 content 参数类型注解应允许 list 通过 Pydantic 校验."""
        import inspect
        from pydantic import create_model
        from src.mcp_server.tools.project import project_update

        sig = inspect.signature(project_update)
        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        ToolModel = create_model("project_update_model", **fields)
        validated = ToolModel(
            project_id="proj-1",
            group="features",
            item_id="feat_20260512_1",
            content=["a", "b"],
        )
        assert validated.content == ["a", "b"]
