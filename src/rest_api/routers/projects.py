"""项目管理 API 路由."""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, Path, HTTPException

from ..business_client import (
    api_project_list, api_register_project, api_get_project, api_rename_project,
    api_remove_project, api_list_groups, api_project_tags_info,
    api_project_get, api_project_add, api_project_update, api_project_delete,
    api_manage_item_tags,
)
from ..main import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================
# 项目管理 API
# ===================

@router.get("/projects")
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    name_pattern: str = Query("", description="项目名称正则过滤"),
    include_archived: bool = Query(False, description="包含归档项目"),
):
    """获取项目列表."""
    result = api_project_list(
        page=page,
        size=size,
        view_mode=view_mode,
        name_pattern=name_pattern,
        include_archived=include_archived,
    )
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=400, detail=result.error)


@router.post("/projects")
async def register_project(
    name: str = Query(..., description="项目名称"),
    path: str = Query("", description="项目路径"),
    summary: str = Query("", description="项目摘要"),
    tags: str = Query("", description="项目标签（逗号分隔）"),
):
    """注册新项目."""
    result = api_register_project(
        name=name,
        path=path,
        summary=summary,
        tags=tags,
    )
    if result.success:
        return ApiResponse.success_resp(data=result.data, message="项目注册成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目详情."""
    result = api_get_project(project_id=project_id)
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=404, detail=result.error)


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str = Path(..., description="项目 ID"),
    summary: str = Query(None, description="项目摘要"),
    tags: str = Query(None, description="项目标签（逗号分隔）"),
):
    """更新项目信息."""
    # 项目更新暂不支持通过此接口，直接用重命名接口
    raise HTTPException(status_code=400, detail="此接口暂不支持，请使用 /projects/{project_id}/rename 重命名项目")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str = Path(..., description="项目 ID"),
    mode: str = Query("archive", pattern="^(archive|delete)$", description="操作模式"),
):
    """删除或归档项目."""
    result = api_remove_project(
        project_id=project_id,
        mode=mode,
    )
    if result.success:
        action = "归档" if mode == "archive" else "删除"
        return ApiResponse.success_resp(message=f"项目{action}成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/rename")
async def rename_project(
    project_id: str = Path(..., description="项目 ID"),
    new_name: str = Query(..., description="新项目名称"),
):
    """重命名项目."""
    result = api_rename_project(
        project_id=project_id,
        new_name=new_name,
    )
    if result.success:
        return ApiResponse.success_resp(data=result.data, message="项目重命名成功")
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/projects/{project_id}/groups")
async def list_project_groups(
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目的所有分组."""
    result = api_list_groups(project_id=project_id)
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=404, detail=result.error)


@router.get("/projects/{project_id}/tags")
async def list_project_tags(
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Query("", description="分组名称"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
):
    """获取项目的标签信息."""
    result = api_project_tags_info(
        project_id=project_id,
        group_name=group_name,
        view_mode=view_mode,
        page=page,
        size=size,
    )
    if result.success:
        return ApiResponse.success_resp(data=result.data)
    raise HTTPException(status_code=400, detail=result.error)