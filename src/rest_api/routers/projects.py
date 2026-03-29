"""项目管理 API 路由."""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, Path, HTTPException

from ..mcp_client import get_mcp_client
from ..main import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()
mcp_client = get_mcp_client()


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
    result = mcp_client.call_tool(
        "project_list",
        page=page,
        size=size,
        view_mode=view_mode,
        name_pattern=name_pattern,
        include_archived=include_archived,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/projects")
async def register_project(
    name: str = Query(..., description="项目名称"),
    path: str = Query("", description="项目路径"),
    summary: str = Query("", description="项目摘要"),
    tags: str = Query("", description="项目标签（逗号分隔）"),
):
    """注册新项目."""
    result = mcp_client.call_tool(
        "project_register",
        name=name,
        path=path,
        summary=summary,
        tags=tags,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"), message="项目注册成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目详情."""
    result = mcp_client.call_tool("project_get", project_id=project_id)
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=404, detail=result.get("error"))


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str = Path(..., description="项目 ID"),
    summary: str = Query(None, description="项目摘要"),
    tags: str = Query(None, description="项目标签（逗号分隔）"),
):
    """更新项目信息."""
    kwargs = {"project_id": project_id}
    if summary is not None:
        kwargs["summary"] = summary
    if tags is not None:
        kwargs["tags"] = tags

    result = mcp_client.call_tool("project_update", **kwargs)
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"), message="项目更新成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str = Path(..., description="项目 ID"),
    mode: str = Query("archive", pattern="^(archive|delete)$", description="操作模式"),
):
    """删除或归档项目."""
    result = mcp_client.call_tool(
        "project_remove",
        project_id=project_id,
        mode=mode,
    )
    if result.get("success"):
        action = "归档" if mode == "archive" else "删除"
        return ApiResponse.success(message=f"项目{action}成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.put("/projects/{project_id}/rename")
async def rename_project(
    project_id: str = Path(..., description="项目 ID"),
    new_name: str = Query(..., description="新项目名称"),
):
    """重命名项目."""
    result = mcp_client.call_tool(
        "project_rename",
        project_id=project_id,
        new_name=new_name,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"), message="项目重命名成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/projects/{project_id}/groups")
async def list_project_groups(
    project_id: str = Path(..., description="项目 ID"),
):
    """获取项目的所有分组."""
    result = mcp_client.call_tool(
        "project_groups_list",
        project_id=project_id,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=404, detail=result.get("error"))


@router.get("/projects/{project_id}/tags")
async def list_project_tags(
    project_id: str = Path(..., description="项目 ID"),
    group_name: str = Query("", description="分组名称"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
):
    """获取项目的标签信息."""
    result = mcp_client.call_tool(
        "project_tags_info",
        project_id=project_id,
        group_name=group_name,
        view_mode=view_mode,
        page=page,
        size=size,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=400, detail=result.get("error"))
