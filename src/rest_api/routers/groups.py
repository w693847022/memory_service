"""分组管理 API 路由."""

import logging
from typing import Optional, List

from fastapi import APIRouter, Query, Path, HTTPException

from ..business_client import (
    api_project_get, api_project_add, api_project_update, api_project_delete,
    api_manage_item_tags, api_create_custom_group, api_update_group,
    api_delete_custom_group, api_get_group_settings, api_update_group_settings,
)
from ..main import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()

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

@router.post("/projects/{project_id}/groups")
async def create_custom_group(
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Query(..., description="自定义组名称"),
    content_max_bytes: int = Query(240, description="content 字段最大字节数"),
    summary_max_bytes: int = Query(90, description="summary 字段最大字节数"),
    allow_related: bool = Query(False, description="是否允许关联"),
    allowed_related_to: str = Query("", description="允许关联的目标组列表（逗号分隔）"),
    enable_status: bool = Query(True, description="是否开启 status 字段"),
    enable_severity: bool = Query(False, description="是否开启 severity 字段"),
):
    """创建自定义组."""
    result = api_create_custom_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity,
    )
    if result.success:
        return ApiResponse.success_resp(message=result.message or "操作成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/groups/{group_name}")
async def update_group(
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Path(..., description="组名称"),
    content_max_bytes: int = Query(None, description="content 字段最大字节数"),
    summary_max_bytes: int = Query(None, description="summary 字段最大字节数"),
    allow_related: bool = Query(None, description="是否允许关联"),
    allowed_related_to: str = Query(None, description="允许关联的目标组列表（逗号分隔）"),
    enable_status: bool = Query(None, description="是否开启 status 字段"),
    enable_severity: bool = Query(None, description="是否开启 severity 字段"),
):
    """更新组配置（支持内置组和自定义组）."""
    result = api_update_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity,
    )
    if result.success:
        return ApiResponse.success_resp(message=result.message or "操作成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.delete("/projects/{project_id}/groups/{group_name}")
async def delete_custom_group(
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Path(..., description="自定义组名称"),
):
    """删除自定义组."""
    result = api_delete_custom_group(project_id, group_name)
    if result.success:
        return ApiResponse.success_resp(message=result.message or "操作成功")
    raise HTTPException(status_code=400, detail=result.error)


# ===================
# 组设置 API
# ===================

@router.get("/projects/{project_id}/group-settings")
async def get_group_settings(
    project_id: str = Path(..., description="项目 ID"),
):
    """获取组设置."""
    result = api_get_group_settings(project_id)
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/group-settings")
async def update_group_settings(
    project_id: str = Path(..., description="项目 ID"),
    default_related_rules: str = Query("", description="默认关联规则（JSON 字符串）"),
):
    """更新组设置."""
    import json

    rules = None
    if default_related_rules:
        try:
            rules = json.loads(default_related_rules)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="default_related_rules JSON 格式无效")

    result = api_update_group_settings(
        project_id=project_id,
        default_related_rules=rules,
    )
    if result.success:
        return ApiResponse.success_resp(message=result.message or "操作成功")
    raise HTTPException(status_code=400, detail=result.error)


# ===================
# 分组条目管理 API
# ===================

@router.get("/projects/{project_id}/{group}")
async def list_group_items(
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

    # 添加可选过滤条件
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

    result = api_project_get(**kwargs)
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/projects/{project_id}/{group}/{item_id}")
async def get_group_item(
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
):
    """获取单个条目详情."""
    group = _validate_group(group)

    result = api_project_get(
        project_id=project_id,
        group_name=group,
        item_id=item_id,
    )
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=404, detail=result.error)


@router.post("/projects/{project_id}/{group}")
async def create_group_item(
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    summary: str = Query(..., description="摘要"),
    content: str = Query("", description="内容"),
    status: str = Query("", description="状态 (仅 features/fixes)"),
    severity: str = Query("medium", description="严重程度 (仅 fixes)"),
    tags: str = Query("", description="标签（逗号分隔）"),
    related: str = Query("", description="关联条目 (JSON 字符串)"),
):
    """创建分组条目."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group": group,
        "summary": summary,
        "content": content,
        "tags": tags,
    }

    # 添加可选参数
    if status:
        kwargs["status"] = status
    if severity:
        kwargs["severity"] = severity
    if related:
        kwargs["related"] = related

    result = api_project_add(**kwargs)
    if result.success:
        return ApiResponse.success_resp(data=result.data, message="条目创建成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/{group}/{item_id}")
async def update_group_item(
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
    summary: str = Query(None, description="摘要"),
    content: str = Query(None, description="内容"),
    status: str = Query(None, description="状态"),
    severity: str = Query(None, description="严重程度"),
    tags: str = Query(None, description="标签（逗号分隔）"),
    related: str = Query(None, description="关联条目 (JSON 字符串)"),
):
    """更新分组条目."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group": group,
        "item_id": item_id,
    }

    # 添加可选参数
    if summary is not None:
        kwargs["summary"] = summary
    if content is not None:
        kwargs["content"] = content
    if status is not None:
        kwargs["status"] = status
    if severity is not None:
        kwargs["severity"] = severity
    if tags is not None:
        kwargs["tags"] = tags
    if related is not None:
        kwargs["related"] = related

    result = api_project_update(**kwargs)
    if result.success:
        return ApiResponse.success_resp(data=result.data, message="条目更新成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.delete("/projects/{project_id}/{group}/{item_id}")
async def delete_group_item(
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
):
    """删除分组条目."""
    group = _validate_group(group)

    result = api_project_delete(
        project_id=project_id,
        group=group,
        item_id=item_id,
    )
    if result.success:
        return ApiResponse.success_resp(message="条目删除成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/{group}/{item_id}/tags")
async def manage_item_tags(
    project_id: str = Path(..., description="项目 ID"),
    group: str = Path(..., description="分组名称"),
    item_id: str = Path(..., description="条目 ID"),
    operation: str = Query(..., pattern="^(set|add|remove)$", description="操作类型"),
    tag: str = Query("", description="单个标签"),
    tags: str = Query("", description="标签列表（逗号分隔，operation=set 时使用）"),
):
    """管理条目标签."""
    group = _validate_group(group)

    kwargs = {
        "project_id": project_id,
        "group_name": group,
        "item_id": item_id,
        "operation": operation,
    }

    if operation == "set":
        kwargs["tags"] = tags
    else:
        kwargs["tag"] = tag

    result = api_manage_item_tags(**kwargs)
    if result.success:
        return ApiResponse.success_resp(data=result.data, message="标签操作成功")
    raise HTTPException(status_code=400, detail=result.error)