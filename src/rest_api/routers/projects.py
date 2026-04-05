"""项目管理 API 路由."""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, Path, HTTPException, Request

from clients.business_async_client import BusinessApiAsyncClient

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# ===================
# 项目管理 API
# ===================

@router.get("/projects")
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
    if result.success:
        return {"success": True, "data": result.data}
    raise HTTPException(status_code=400, detail=result.error)


@router.post("/projects")
async def register_project(
    request: Request,
    name: str = Query(..., description="项目名称"),
    path: str = Query("", description="项目路径"),
    summary: str = Query("", description="项目摘要"),
    tags: str = Query("", description="项目标签（逗号分隔）"),
):
    """注册新项目."""
    client = _get_async_client(request)
    result = await client.register_project(
        name=name,
        path=path,
        summary=summary,
        tags=tags,
    )
    if result.success:
        return {"success": True, "data": result.data, "message": "项目注册成功"}
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/projects/{project_id}")
async def get_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目详情."""
    client = _get_async_client(request)
    result = await client.get_project(project_id=project_id)
    if result.success:
        return {"success": True, "data": result.data}
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
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    mode: str = Query("archive", pattern="^(archive|delete)$", description="操作模式"),
):
    """删除或归档项目."""
    client = _get_async_client(request)
    result = await client.remove_project(
        project_id=project_id,
        mode=mode,
    )
    if result.success:
        action = "归档" if mode == "archive" else "删除"
        return {"success": True, "message": f"项目{action}成功"}
    raise HTTPException(status_code=400, detail=result.error)


@router.put("/projects/{project_id}/rename")
async def rename_project(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
    new_name: str = Query(..., description="新项目名称"),
):
    """重命名项目."""
    client = _get_async_client(request)
    result = await client.rename_project(
        project_id=project_id,
        new_name=new_name,
    )
    if result.success:
        return {"success": True, "data": result.data, "message": "项目重命名成功"}
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/projects/{project_id}/groups")
async def list_project_groups(
    request: Request,
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目的所有分组."""
    client = _get_async_client(request)
    result = await client.list_groups(project_id=project_id)
    if result.success:
        return {"success": True, "data": result.data}
    raise HTTPException(status_code=404, detail=result.error)


@router.get("/projects/{project_id}/tags")
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
    if result.success:
        return {"success": True, "data": result.data}
    raise HTTPException(status_code=400, detail=result.error)