"""分组管理 API 路由."""

import logging

from fastapi import APIRouter, Query, Path, Body, HTTPException, Request

from clients.business_async_client import BusinessApiAsyncClient
from src.models.requests.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupSettingsUpdateRequest,
    ItemCreateRequest,
    ItemUpdateRequest,
    ItemTagManageRequest,
)
from src.models.responses.api_responses import (
    GroupListResponse,
    GroupSettingsResponse,
    GroupOperationResponse,
    ItemListResponse,
    ItemDetailResponse,
    ItemOperationResponse,
    MessageResponse,
)
from src.rest_api.utils.handlers import handle_result

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# 支持的分组类型
VALID_GROUPS = ["features", "notes", "fixes", "standards"]


def _validate_group(group: str) -> str:
    """验证分组名称."""
    if group not in VALID_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分组类型: {group}，必须是 {VALID_GROUPS} 之一"
        )
    return group


# ===================
# 自定义组管理 API（放在通用路由之前，避免被通用路由匹配）
# ===================

@router.post("/projects/{project_id}/groups", response_model=GroupOperationResponse)
async def create_custom_group(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    body: GroupCreateRequest = Body(...),
):
    """创建自定义组."""
    client = _get_async_client(request)
    result = await client.create_custom_group(
        project_id=project_id,
        group_name=body.group_name,
        content_max_bytes=body.content_max_bytes,
        summary_max_bytes=body.summary_max_bytes,
        allow_related=body.allow_related,
        allowed_related_to=body.allowed_related_to,
        enable_status=body.enable_status,
        enable_severity=body.enable_severity,
        description=body.description,
    )
    return await handle_result(result)


@router.put("/projects/{project_id}/groups/{group_name}", response_model=GroupOperationResponse)
async def update_group(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Path(..., description="组名称"),
    body: GroupUpdateRequest = Body(...),
):
    """更新组配置（支持内置组和自定义组）."""
    client = _get_async_client(request)
    result = await client.update_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=body.content_max_bytes,
        summary_max_bytes=body.summary_max_bytes,
        allow_related=body.allow_related,
        allowed_related_to=body.allowed_related_to,
        enable_status=body.enable_status,
        enable_severity=body.enable_severity,
        max_tags=body.max_tags,
        status_values=body.status_values,
        severity_values=body.severity_values,
        required_fields=body.required_fields,
        description=body.description,
    )
    return await handle_result(result)


@router.delete("/projects/{project_id}/groups/{group_name}", response_model=GroupOperationResponse)
async def delete_custom_group(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Path(..., description="自定义组名称"),
):
    """删除自定义组."""
    client = _get_async_client(request)
    result = await client.delete_custom_group(project_id, group_name)
    return await handle_result(result)


# ===================
# 组设置 API
# ===================

@router.get("/projects/{project_id}/group-settings", response_model=GroupSettingsResponse)
async def get_group_settings(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """获取组设置."""
    client = _get_async_client(request)
    result = await client.get_group_settings(project_id)
    return await handle_result(result)


@router.put("/projects/{project_id}/group-settings", response_model=GroupOperationResponse)
async def update_group_settings(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    body: GroupSettingsUpdateRequest = Body(...),
):
    """更新组设置."""
    import json

    rules = None
    if body and body.default_related_rules:
        try:
            rules = json.loads(body.default_related_rules)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="default_related_rules JSON 格式无效")

    client = _get_async_client(request)
    result = await client.update_group_settings(
        project_id=project_id,
        default_related_rules=rules,
    )
    return await handle_result(result)


# ===================
# 分组条目管理 API
# ===================

@router.get("/projects/{project_id}/{group}", response_model=ItemListResponse)
async def list_group_items(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称 (features/notes/fixes/standards)"),
    status: str = Query("", description="状态过滤 (pending/in_progress/completed)"),
    severity: str = Query("", description="严重程度过滤 (critical/high/medium/low)"),
    tags: str = Query("", description="标签过滤（逗号分隔，OR 逻辑）"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    summary_pattern: str = Query("", description="摘要正则过滤"),
    created_after: str = Query("", description="创建时间起始 (YYYY-MM-DD)"),
    created_before: str = Query("", description="创建时间截止 (YYYY-MM-DD)"),
    updated_after: str = Query("", description="修改时间起始 (YYYY-MM-DD)"),
    updated_before: str = Query("", description="修改时间截止 (YYYY-MM-DD)"),
):
    """获取分组内的条目列表."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group_name": group,
        "page": page,
        "size": size,
        "view_mode": view_mode,
    }

    if status:
        kwargs["status"] = status
    if severity:
        kwargs["severity"] = severity
    if tags:
        kwargs["tags"] = tags
    if summary_pattern:
        kwargs["summary_pattern"] = summary_pattern
    if created_after:
        kwargs["created_after"] = created_after
    if created_before:
        kwargs["created_before"] = created_before
    if updated_after:
        kwargs["updated_after"] = updated_after
    if updated_before:
        kwargs["updated_before"] = updated_before

    client = _get_async_client(request)
    result = await client.project_get(**kwargs)
    return await handle_result(result)


@router.get("/projects/{project_id}/{group}/{item_id}", response_model=ItemDetailResponse)
async def get_group_item(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
):
    """获取单个条目详情."""
    group = _validate_group(group)

    client = _get_async_client(request)
    result = await client.project_get(
        project_id=project_id,
        group_name=group,
        item_id=item_id,
    )
    return await handle_result(result, error_status=404)


@router.post("/projects/{project_id}/{group}", response_model=ItemOperationResponse)
async def create_group_item(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    body: ItemCreateRequest = Body(...),
):
    """创建分组条目."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group": group,
        "summary": body.summary,
        "content": body.content,
        "tags": body.tags,
    }

    if body.status:
        kwargs["status"] = body.status
    if body.severity:
        kwargs["severity"] = body.severity
    if body.related:
        kwargs["related"] = body.related

    client = _get_async_client(request)
    result = await client.project_add(**kwargs)
    return await handle_result(result, message="条目创建成功")


@router.put("/projects/{project_id}/{group}/{item_id}", response_model=ItemOperationResponse)
async def update_group_item(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
    body: ItemUpdateRequest = Body(...),
):
    """更新分组条目."""
    group = _validate_group(group)

    client = _get_async_client(request)
    result = await client.project_update(
        project_id=project_id,
        group=group,
        item_id=item_id,
        content=body.content,
        summary=body.summary,
        status=body.status,
        severity=body.severity,
        tags=body.tags,
        related=body.related,
    )
    return await handle_result(result, message="条目更新成功")


@router.delete("/projects/{project_id}/{group}/{item_id}", response_model=ItemOperationResponse)
async def delete_group_item(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
):
    """删除分组条目."""
    group = _validate_group(group)

    client = _get_async_client(request)
    result = await client.project_delete(
        project_id=project_id,
        group=group,
        item_id=item_id,
    )
    return await handle_result(result, message="条目删除成功")


@router.put("/projects/{project_id}/{group}/{item_id}/tags", response_model=ItemOperationResponse)
async def manage_item_tags(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
    body: ItemTagManageRequest = Body(...),
):
    """管理条目标签."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group_name": group,
        "item_id": item_id,
        "operation": body.operation,
    }

    if body.operation == "set":
        kwargs["tags"] = body.tags
    else:
        kwargs["tag"] = body.tag

    client = _get_async_client(request)
    result = await client.manage_item_tags(**kwargs)
    return await handle_result(result, message="标签操作成功")


# ===================
# 兼容 Business API 路径格式的端点
# ===================

@router.post("/groups/custom", response_model=GroupOperationResponse)
async def create_custom_group_compat(
    request: Request,
    project_id: str = Query(..., description="项目 ID"),
    group_name: str = Query(..., description="自定义组名称"),
    content_max_bytes: int = Query(240, description="content 字段最大字节数"),
    summary_max_bytes: int = Query(90, description="summary 字段最大字节数"),
    allow_related: bool = Query(False, description="是否允许关联"),
    allowed_related_to: str = Query("", description="允许关联的目标组列表（逗号分隔）"),
    enable_status: bool = Query(True, description="是否开启 status 字段"),
    enable_severity: bool = Query(False, description="是否开启 severity 字段"),
    description: str = Query("", description="组描述"),
):
    """创建自定义组 (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.create_custom_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity,
        description=description,
    )
    return await handle_result(result)


@router.put("/groups/custom", response_model=GroupOperationResponse)
async def update_group_compat(
    request: Request,
    project_id: str = Query(..., description="项目 ID"),
    group_name: str = Query(..., description="组名称"),
    content_max_bytes: int = Query(None, description="content 字段最大字节数"),
    summary_max_bytes: int = Query(None, description="summary 字段最大字节数"),
    allow_related: bool = Query(None, description="是否允许关联"),
    allowed_related_to: str = Query(None, description="允许关联的目标组列表（逗号分隔）"),
    enable_status: bool = Query(None, description="是否开启 status 字段"),
    enable_severity: bool = Query(None, description="是否开启 severity 字段"),
    description: str = Query(None, description="组描述"),
):
    """更新组配置（兼容 Business API 路径）."""
    client = _get_async_client(request)
    result = await client.update_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity,
        description=description,
    )
    return await handle_result(result)


@router.get("/groups/settings", response_model=GroupSettingsResponse)
async def get_group_settings_compat(
    request: Request,
    project_id: str = Query(..., description="项目 ID"),
):
    """获取组设置 (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.get_group_settings(project_id)
    return await handle_result(result)


@router.put("/groups/settings", response_model=GroupOperationResponse)
async def update_group_settings_compat(
    request: Request,
    project_id: str = Query(..., description="项目 ID"),
    default_related_rules: str = Query(None, description="默认关联规则（JSON 字符串）"),
):
    """更新组设置 (兼容 Business API 路径)."""
    import json

    rules = None
    if default_related_rules:
        try:
            rules = json.loads(default_related_rules)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="default_related_rules JSON 格式无效")

    client = _get_async_client(request)
    result = await client.update_group_settings(
        project_id=project_id,
        default_related_rules=rules,
    )
    return await handle_result(result)
