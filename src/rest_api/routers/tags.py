"""标签管理 API 路由."""

import logging

from fastapi import APIRouter, Query, Path, Body, Request

from clients.business_async_client import BusinessApiAsyncClient
from src.models.response import ApiResponse
from src.models.requests.tag import (
    TagRegisterRequest,
    TagUpdateRequest,
    TagDeleteRequest,
    TagMergeRequest,
)
from src.rest_api.utils.handlers import handle_result

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# ===================
# 兼容 Business API 路径格式的端点
# ===================

@router.post("/tags/register", response_model=ApiResponse)
async def register_tag_compat(
    request: Request,
    body: TagRegisterRequest = Body(...),
):
    """注册项目标签 (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.tag_register(
        project_id=body.project_id,
        tag_name=body.tag_name,
        summary=body.summary,
        aliases=body.aliases,
    )
    return await handle_result(result, message="标签注册成功")


@router.put("/tags/update", response_model=ApiResponse)
async def update_tag_compat(
    request: Request,
    body: TagUpdateRequest = Body(...),
):
    """更新已注册标签的语义信息 (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.tag_update(
        project_id=body.project_id,
        tag_name=body.tag_name,
        summary=body.summary,
    )
    return await handle_result(result, message="标签更新成功")


@router.delete("/tags/delete", response_model=ApiResponse)
async def delete_tag_compat(
    request: Request,
    body: TagDeleteRequest = Body(...),
):
    """删除标签注册 (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.tag_delete(
        project_id=body.project_id,
        tag_name=body.tag_name,
        force=body.force,
    )
    return await handle_result(result, message="标签删除成功")


@router.post("/tags/merge", response_model=ApiResponse)
async def merge_tags_compat(
    request: Request,
    body: TagMergeRequest = Body(...),
):
    """合并标签：将所有 old_tag 的引用迁移到 new_tag (兼容 Business API 路径)."""
    client = _get_async_client(request)
    result = await client.tag_merge(
        project_id=body.project_id,
        old_tag=body.old_tag,
        new_tag=body.new_tag,
    )
    return await handle_result(result, message="标签合并成功")


# ===================
# 原有标签管理 API
# ===================

@router.get("/tags", response_model=ApiResponse)
async def list_tags(
    request: Request,
    project_id: str = Query(..., description="项目 ID"),
    group_name: str = Query("", description="分组名称"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
    summary_pattern: str = Query("", description="摘要正则过滤"),
    tag_name_pattern: str = Query("", description="标签名正则过滤"),
):
    """获取项目标签列表."""
    client = _get_async_client(request)
    result = await client.project_tags_info(
        project_id=project_id,
        group_name=group_name,
        view_mode=view_mode,
        page=page,
        size=size,
        summary_pattern=summary_pattern,
        tag_name_pattern=tag_name_pattern,
    )
    return await handle_result(result)


@router.post("/tags", response_model=ApiResponse)
async def register_tag(
    request: Request,
    body: TagRegisterRequest = Body(...),
):
    """注册项目标签."""
    client = _get_async_client(request)
    result = await client.tag_register(
        project_id=body.project_id,
        tag_name=body.tag_name,
        summary=body.summary,
        aliases=body.aliases,
    )
    return await handle_result(result, message="标签注册成功")


@router.put("/tags/{tag_name}", response_model=ApiResponse)
async def update_tag(
    request: Request,
    tag_name: str = Path(..., description="标签名称"),
    body: TagUpdateRequest = Body(...),
):
    """更新已注册标签的语义信息."""
    client = _get_async_client(request)
    result = await client.tag_update(
        project_id=body.project_id,
        tag_name=tag_name,
        summary=body.summary,
    )
    return await handle_result(result, message="标签更新成功")


@router.delete("/tags/{tag_name}", response_model=ApiResponse)
async def delete_tag(
    request: Request,
    tag_name: str = Path(..., description="标签名称"),
    body: TagDeleteRequest = Body(...),
):
    """删除标签注册."""
    client = _get_async_client(request)
    result = await client.tag_delete(
        project_id=body.project_id,
        tag_name=tag_name,
        force=body.force,
    )
    return await handle_result(result, message="标签删除成功")
