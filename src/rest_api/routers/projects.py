"""项目管理 API 路由."""

import logging

from fastapi import APIRouter, Query, Path, Body, HTTPException, Request

from clients.business_async_client import BusinessApiAsyncClient
from src.models.requests.project import ProjectRegisterRequest, ProjectRenameRequest
from src.models.responses.api_responses import (
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectOperationResponse,
    GroupListResponse,
    TagInfoResponse,
)
from src.rest_api.utils.handlers import handle_result

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# ===================
# 项目管理 API
# ===================

@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    name_pattern: str = Query("", description="项目名称正则过滤"),
    include_archived: bool = Query(False, description="包含归档项目"),
):
    """获取项目列表."""
    client = _get_async_client(request)
    result = await client.project_list(
        page=page,
        size=size,
        view_mode=view_mode,
        name_pattern=name_pattern,
        include_archived=include_archived,
    )
    return await handle_result(result)


@router.post("/projects", response_model=ProjectOperationResponse)
async def register_project(
    request: Request,
    body: ProjectRegisterRequest = Body(...),
):
    """注册新项目."""
    client = _get_async_client(request)
    result = await client.register_project(
        name=body.name,
        path=body.path,
        summary=body.summary,
        tags=body.tags,
    )
    return await handle_result(result, message="项目注册成功")


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目详情."""
    client = _get_async_client(request)
    result = await client.get_project(project_id=project_id)
    return await handle_result(result, error_status=404)


@router.put("/projects/{project_id}", response_model=ProjectOperationResponse)
async def update_project(
    project_id: str = Path(..., description="项目 ID"),
):
    """更新项目信息."""
    raise HTTPException(status_code=400, detail="此接口暂不支持，请使用 /projects/{project_id}/rename 重命名项目")


@router.post("/projects/{project_id}/archive", response_model=ProjectOperationResponse)
async def archive_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """归档项目."""
    client = _get_async_client(request)
    result = await client.archive_project(
        project_id=project_id,
    )
    return await handle_result(result, message="项目归档成功")


@router.delete("/projects/{project_id}", response_model=ProjectOperationResponse)
async def delete_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """永久删除已归档项目。仅 archived 状态的项目可删除，active 项目需先调用归档接口后再删除."""
    client = _get_async_client(request)
    result = await client.delete_project(
        project_id=project_id,
    )
    return await handle_result(result, message="项目删除成功")


@router.put("/projects/{project_id}/rename", response_model=ProjectOperationResponse)
async def rename_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    body: ProjectRenameRequest = Body(...),
):
    """重命名项目."""
    client = _get_async_client(request)
    result = await client.rename_project(
        project_id=project_id,
        new_name=body.new_name,
    )
    return await handle_result(result, message="项目重命名成功")


@router.get("/projects/{project_id}/groups", response_model=GroupListResponse)
async def list_project_groups(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目的所有分组."""
    client = _get_async_client(request)
    result = await client.list_groups(project_id=project_id)
    return await handle_result(result, error_status=404)


@router.get("/projects/{project_id}/tags", response_model=TagInfoResponse)
async def list_project_tags(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Query("", description="分组名称"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
):
    """获取项目的标签信息."""
    client = _get_async_client(request)
    result = await client.project_tags_info(
        project_id=project_id,
        group_name=group_name,
        view_mode=view_mode,
        page=page,
        size=size,
    )
    return await handle_result(result)
