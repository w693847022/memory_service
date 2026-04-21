"""REST API 请求模型和工具函数单元测试."""

import pytest
from fastapi import HTTPException

from src.models.requests.project import ProjectRegisterRequest, ProjectRenameRequest
from src.models.requests.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupSettingsUpdateRequest,
    ItemCreateRequest,
    ItemUpdateRequest,
    ItemTagManageRequest,
)
from src.models.requests.tag import (
    TagRegisterRequest,
    TagUpdateRequest,
    TagDeleteRequest,
    TagMergeRequest,
)
from src.models.requests.stats import StatsSummaryRequest, StatsCleanupRequest
from src.models.responses.common import PagedData
from src.models.response import ApiResponse
from src.rest_api.utils.handlers import handle_result


# ===================
# 请求模型测试
# ===================

class TestProjectRequests:
    """项目请求模型测试."""

    def test_register_request_defaults(self):
        req = ProjectRegisterRequest(name="test-project")
        assert req.name == "test-project"
        assert req.path == ""
        assert req.summary == ""
        assert req.tags == ""

    def test_register_request_all_fields(self):
        req = ProjectRegisterRequest(
            name="my-project",
            path="/home/user/project",
            summary="A test project",
            tags="api,test",
        )
        assert req.name == "my-project"
        assert req.path == "/home/user/project"
        assert req.tags == "api,test"

    def test_rename_request(self):
        req = ProjectRenameRequest(new_name="renamed-project")
        assert req.new_name == "renamed-project"


class TestGroupRequests:
    """分组请求模型测试."""

    def test_group_create_defaults(self):
        req = GroupCreateRequest(group_name="custom_group")
        assert req.group_name == "custom_group"
        assert req.content_max_bytes == 240
        assert req.enable_status is True
        assert req.enable_severity is False

    def test_group_update_all_optional(self):
        req = GroupUpdateRequest()
        assert req.content_max_bytes is None
        assert req.summary_max_bytes is None

    def test_item_create_required(self):
        req = ItemCreateRequest(summary="Test item")
        assert req.summary == "Test item"
        assert req.content == ""
        assert req.severity == "medium"

    def test_item_update_all_optional(self):
        req = ItemUpdateRequest()
        assert req.summary is None
        assert req.content is None

    def test_tag_manage_request(self):
        req = ItemTagManageRequest(operation="add", tag="feature")
        assert req.operation == "add"
        assert req.tag == "feature"

    def test_tag_manage_set_operation(self):
        req = ItemTagManageRequest(operation="set", tags="api,test,docs")
        assert req.operation == "set"
        assert req.tags == "api,test,docs"


class TestTagRequests:
    """标签请求模型测试."""

    def test_tag_register(self):
        req = TagRegisterRequest(
            project_id="test-uuid",
            tag_name="feature",
            summary="A feature tag",
        )
        assert req.project_id == "test-uuid"
        assert req.tag_name == "feature"
        assert req.aliases == ""

    def test_tag_delete_defaults(self):
        req = TagDeleteRequest(
            project_id="test-uuid",
            tag_name="old_tag",
        )
        assert req.force == "false"

    def test_tag_merge(self):
        req = TagMergeRequest(
            project_id="test-uuid",
            old_tag="old",
            new_tag="new",
        )
        assert req.old_tag == "old"
        assert req.new_tag == "new"


class TestStatsRequests:
    """统计请求模型测试."""

    def test_stats_summary_defaults(self):
        req = StatsSummaryRequest()
        assert req.type == ""
        assert req.tool_name == ""

    def test_stats_cleanup_defaults(self):
        req = StatsCleanupRequest()
        assert req.retention_days == 30


# ===================
# 响应模型测试
# ===================

class TestPagedData:
    """分页数据模型测试."""

    def test_defaults(self):
        paged = PagedData()
        assert paged.items == []
        assert paged.total == 0
        assert paged.page == 1
        assert paged.size == 0

    def test_with_data(self):
        paged = PagedData(items=[1, 2, 3], total=100, page=2, size=10)
        assert len(paged.items) == 3
        assert paged.total == 100


# ===================
# 工具函数测试
# ===================

class TestHandleResult:
    """handle_result 工具函数测试."""

    @pytest.mark.asyncio
    async def test_success_result(self):
        result = ApiResponse(success=True, data={"id": "123"})
        response = await handle_result(result)
        assert response["success"] is True
        assert response["data"] == {"id": "123"}

    @pytest.mark.asyncio
    async def test_success_with_custom_message(self):
        result = ApiResponse(success=True, data=None)
        response = await handle_result(result, message="操作成功")
        assert response["success"] is True
        assert response["message"] == "操作成功"

    @pytest.mark.asyncio
    async def test_success_with_result_message(self):
        result = ApiResponse(success=True, data=None, message="来自业务层的消息")
        response = await handle_result(result)
        assert response["message"] == "来自业务层的消息"

    @pytest.mark.asyncio
    async def test_custom_message_overrides_result_message(self):
        result = ApiResponse(success=True, data=None, message="业务消息")
        response = await handle_result(result, message="自定义消息")
        assert response["message"] == "自定义消息"

    @pytest.mark.asyncio
    async def test_failure_raises_http_exception(self):
        result = ApiResponse(success=False, error="Not found")
        with pytest.raises(HTTPException) as exc_info:
            await handle_result(result, error_status=404)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_failure_default_status(self):
        result = ApiResponse(success=False, error="Bad request")
        with pytest.raises(HTTPException) as exc_info:
            await handle_result(result)
        assert exc_info.value.status_code == 400
