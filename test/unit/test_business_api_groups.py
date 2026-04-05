"""Business API Groups 单元测试.

测试 business/api/groups.py 中的 5 个接口:
1. create_custom_group - POST /api/groups/custom
2. update_group - PUT /api/groups/custom
3. delete_custom_group - DELETE /api/groups/custom
4. get_group_settings - GET /api/groups/settings
5. update_group_settings - PUT /api/groups/settings
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, AsyncMock
from fastapi import HTTPException
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from business.api.groups import (
    router,
    init_services,
    create_custom_group,
    update_group,
    delete_custom_group,
    get_group_settings,
    update_group_settings,
)


@pytest.fixture
def mock_storage():
    """创建 Mock Storage 服务."""
    from unittest.mock import Mock, AsyncMock

    # 创建异步上下文管理器
    @asynccontextmanager
    async def _async_context_manager(*args, **kwargs):
        yield

    mock = Mock()
    # 模拟异步方法
    mock.get_group_configs = AsyncMock(return_value={
        "groups": {},
        "group_settings": {}
    })
    mock.save_group_configs = AsyncMock(return_value=True)

    # 模拟 barrier 对象及其异步上下文管理器方法
    mock_barrier = Mock()
    mock_barrier.group_create = Mock(return_value=_async_context_manager())
    mock_barrier.group_update = Mock(return_value=_async_context_manager())
    mock_barrier.group_delete = Mock(return_value=_async_context_manager())
    mock_barrier.group_settings = Mock(return_value=_async_context_manager())
    mock.barrier = mock_barrier

    return mock


@pytest.fixture
def mock_storage_with_groups():
    """创建带有预置组配置的 Mock Storage 服务."""
    from unittest.mock import Mock, AsyncMock

    # 创建异步上下文管理器
    @asynccontextmanager
    async def _async_context_manager(*args, **kwargs):
        yield

    mock = Mock()
    # 模拟异步方法
    mock.get_group_configs = AsyncMock(return_value={
        "groups": {
            "custom_api": {
                "content_max_bytes": 240,
                "summary_max_bytes": 90,
                "allow_related": False,
                "allowed_related_to": [],
                "enable_status": True,
                "enable_severity": False,
                "status_values": [],
                "severity_values": [],
                "required_fields": ["content", "summary"],
                "is_builtin": False,
            }
        },
        "group_settings": {
            "default_related_rules": {
                "features": ["notes"]
            }
        }
    })
    mock.save_group_configs = AsyncMock(return_value=True)

    # 模拟 barrier 对象及其异步上下文管理器方法
    mock_barrier = Mock()
    mock_barrier.group_create = Mock(return_value=_async_context_manager())
    mock_barrier.group_update = Mock(return_value=_async_context_manager())
    mock_barrier.group_delete = Mock(return_value=_async_context_manager())
    mock_barrier.group_settings = Mock(return_value=_async_context_manager())
    mock.barrier = mock_barrier

    return mock


class TestCreateCustomGroup:
    """测试 create_custom_group 接口."""

    @pytest.mark.asyncio
    async def test_create_custom_group_success(self, mock_storage):
        """测试成功创建自定义组."""
        init_services(mock_storage)

        response = await create_custom_group(
            project_id="proj_001",
            group_name="apis",
            content_max_bytes=500,
            summary_max_bytes=100,
            allow_related=True,
            allowed_related_to="notes,features",
            enable_status=True,
            enable_severity=False
        )

        data = response
        assert "success" in data
        assert data["success"] is True
        assert "apis" in data["message"]
        mock_storage.get_group_configs.assert_called_once_with("proj_001")
        mock_storage.save_group_configs.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_custom_group_duplicate_name(self, mock_storage_with_groups):
        """测试创建重复名称的自定义组."""
        init_services(mock_storage_with_groups)

        with pytest.raises(HTTPException) as exc_info:
            await create_custom_group(
                project_id="proj_001",
                group_name="custom_api"
            )

        assert exc_info.value.status_code == 400
        assert "已存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_custom_group_save_failure(self, mock_storage):
        """测试保存配置失败."""
        mock_storage.save_group_configs = AsyncMock(return_value=False)
        init_services(mock_storage)

        with pytest.raises(HTTPException) as exc_info:
            await create_custom_group(
                project_id="proj_001",
                group_name="apis"
            )

        assert exc_info.value.status_code == 400
        assert "保存配置失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_custom_group_empty_related_to(self, mock_storage):
        """测试 allowed_related_to 为空字符串时的处理."""
        init_services(mock_storage)

        response = await create_custom_group(
            project_id="proj_001",
            group_name="simple_group",
            allow_related=False,
            allowed_related_to=""
        )

        data = response
        assert data["success"] is True

        # 验证 allowed_related_to 被正确解析为空列表
        call_args = mock_storage.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["groups"]["simple_group"]["allowed_related_to"] == []


class TestUpdateGroup:
    """测试 update_group 接口."""

    @pytest.mark.asyncio
    async def test_update_group_success(self, mock_storage_with_groups):
        """测试成功更新组配置."""
        init_services(mock_storage_with_groups)

        response = await update_group(
            project_id="proj_001",
            group_name="custom_api",
            content_max_bytes=500,
            allow_related=True
        )

        data = response
        assert data["success"] is True
        assert "custom_api" in data["message"]

        # 验证更新后的值
        call_args = mock_storage_with_groups.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["groups"]["custom_api"]["content_max_bytes"] == 500
        assert saved_config["groups"]["custom_api"]["allow_related"] is True

    @pytest.mark.asyncio
    async def test_update_group_not_found(self, mock_storage):
        """测试更新不存在的组."""
        init_services(mock_storage)

        with pytest.raises(HTTPException) as exc_info:
            await update_group(
                project_id="proj_001",
                group_name="nonexistent_group"
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_group_save_failure(self, mock_storage_with_groups):
        """测试保存配置失败."""
        mock_storage_with_groups.save_group_configs = AsyncMock(return_value=False)
        init_services(mock_storage_with_groups)

        with pytest.raises(HTTPException) as exc_info:
            await update_group(
                project_id="proj_001",
                group_name="custom_api",
                content_max_bytes=500
            )

        assert exc_info.value.status_code == 400
        assert "保存配置失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_group_with_allowed_related_to(self, mock_storage_with_groups):
        """测试更新 allowed_related_to 字段."""
        init_services(mock_storage_with_groups)

        response = await update_group(
            project_id="proj_001",
            group_name="custom_api",
            allowed_related_to="notes,features,standards"
        )

        data = response
        assert data["success"] is True

        # 验证 allowed_related_to 被正确解析
        call_args = mock_storage_with_groups.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["groups"]["custom_api"]["allowed_related_to"] == ["notes", "features", "standards"]

    @pytest.mark.asyncio
    async def test_update_group_partial_update(self, mock_storage_with_groups):
        """测试部分更新字段（其他字段保持不变）."""
        init_services(mock_storage_with_groups)

        response = await update_group(
            project_id="proj_001",
            group_name="custom_api",
            summary_max_bytes=200
        )

        data = response
        assert data["success"] is True

        # 验证其他字段保持不变
        call_args = mock_storage_with_groups.save_group_configs.call_args
        saved_config = call_args[0][1]
        # content_max_bytes 应该保持原值 240
        assert saved_config["groups"]["custom_api"]["content_max_bytes"] == 240
        # summary_max_bytes 应该被更新为 200
        assert saved_config["groups"]["custom_api"]["summary_max_bytes"] == 200


class TestDeleteCustomGroup:
    """测试 delete_custom_group 接口."""

    @pytest.mark.asyncio
    async def test_delete_custom_group_success(self, mock_storage_with_groups):
        """测试成功删除自定义组."""
        init_services(mock_storage_with_groups)

        response = await delete_custom_group(
            project_id="proj_001",
            group_name="custom_api"
        )

        data = response
        assert data["success"] is True
        assert "已删除" in data["message"]

        # 验证组已被删除
        call_args = mock_storage_with_groups.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert "custom_api" not in saved_config["groups"]

    @pytest.mark.asyncio
    async def test_delete_custom_group_not_found(self, mock_storage):
        """测试删除不存在的自定义组."""
        init_services(mock_storage)

        with pytest.raises(HTTPException) as exc_info:
            await delete_custom_group(
                project_id="proj_001",
                group_name="nonexistent"
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_builtin_group(self, mock_storage):
        """测试不能删除内置组.

        注意：内置组（如 features）不在自定义组配置中，
        因此会先触发 404（组不存在），而不是 400（内置组不可删除）。
        这是设计行为：内置组通过不同机制管理。
        """
        init_services(mock_storage)
        mock_storage.get_group_configs = AsyncMock(return_value={
            "groups": {},
            "group_settings": {}
        })

        with pytest.raises(HTTPException) as exc_info:
            await delete_custom_group(
                project_id="proj_001",
                group_name="features"
            )

        # 内置组不在 groups 中，返回 404 而不是 400
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_custom_group_save_failure(self, mock_storage_with_groups):
        """测试保存配置失败."""
        mock_storage_with_groups.save_group_configs = AsyncMock(return_value=False)
        init_services(mock_storage_with_groups)

        with pytest.raises(HTTPException) as exc_info:
            await delete_custom_group(
                project_id="proj_001",
                group_name="custom_api"
            )

        assert exc_info.value.status_code == 400
        assert "保存配置失败" in exc_info.value.detail


class TestGetGroupSettings:
    """测试 get_group_settings 接口."""

    @pytest.mark.asyncio
    async def test_get_group_settings_success(self, mock_storage_with_groups):
        """测试成功获取组设置."""
        init_services(mock_storage_with_groups)

        response = await get_group_settings(project_id="proj_001")

        data = response
        assert data["success"] is True
        assert "settings" in data["data"]
        assert "group_settings" in data["data"]
        assert "default_related_rules" in data["data"]["settings"]

    @pytest.mark.asyncio
    async def test_get_group_settings_empty(self, mock_storage):
        """测试获取空的组设置."""
        mock_storage.get_group_configs = AsyncMock(return_value={
            "groups": {},
            "group_settings": {}
        })
        init_services(mock_storage)

        response = await get_group_settings(project_id="proj_001")

        data = response
        assert data["success"] is True
        assert data["data"]["settings"] == {}

    @pytest.mark.asyncio
    async def test_get_group_settings_with_rules(self, mock_storage_with_groups):
        """测试获取带有关联规则的组设置."""
        init_services(mock_storage_with_groups)

        response = await get_group_settings(project_id="proj_001")

        data = response
        assert data["success"] is True
        rules = data["data"]["settings"]["default_related_rules"]
        assert rules["features"] == ["notes"]


class TestUpdateGroupSettings:
    """测试 update_group_settings 接口."""

    @pytest.mark.asyncio
    async def test_update_group_settings_success(self, mock_storage):
        """测试成功更新组设置."""
        init_services(mock_storage)

        new_rules = {"features": ["notes"], "fixes": ["features", "notes"]}
        response = await update_group_settings(
            project_id="proj_001",
            default_related_rules=new_rules
        )

        data = response
        assert data["success"] is True
        assert "更新成功" in data["message"]

        # 验证保存的值
        call_args = mock_storage.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["group_settings"]["default_related_rules"] == new_rules

    @pytest.mark.asyncio
    async def test_update_group_settings_save_failure(self, mock_storage):
        """测试保存配置失败."""
        mock_storage.save_group_configs = AsyncMock(return_value=False)
        init_services(mock_storage)

        with pytest.raises(HTTPException) as exc_info:
            await update_group_settings(
                project_id="proj_001",
                default_related_rules={"features": ["notes"]}
            )

        assert exc_info.value.status_code == 400
        assert "保存配置失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_group_settings_empty_rules(self, mock_storage):
        """测试更新空的关联规则."""
        init_services(mock_storage)

        response = await update_group_settings(
            project_id="proj_001",
            default_related_rules={}
        )

        data = response
        assert data["success"] is True

        # 验证保存的值
        call_args = mock_storage.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["group_settings"]["default_related_rules"] == {}

    @pytest.mark.asyncio
    async def test_update_group_settings_existing_project(self, mock_storage_with_groups):
        """测试更新已有配置的项目的组设置."""
        init_services(mock_storage_with_groups)

        new_rules = {"standards": ["notes"]}
        response = await update_group_settings(
            project_id="proj_001",
            default_related_rules=new_rules
        )

        data = response
        assert data["success"] is True

        # 验证更新了现有配置
        call_args = mock_storage_with_groups.save_group_configs.call_args
        saved_config = call_args[0][1]
        assert saved_config["group_settings"]["default_related_rules"] == new_rules
        # groups 配置应该保持不变
        assert "custom_api" in saved_config["groups"]
