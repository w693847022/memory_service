"""标签管理 API 路由."""

import logging

from fastapi import APIRouter, Query, Path, HTTPException

from ..business_client import (
    api_project_tags_info, api_tag_register, api_tag_update, api_tag_delete, api_tag_merge,
)
from ..main import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================
# 标签管理 API
# ===================

@router.get("/tags")
async def list_tags(
    project_id: str = Query(..., description="项目 ID"),
    group_name: str = Query("", description="分组名称"),
    view_mode: str = Query("summary", pattern="^(summary|detail)$", description="视图模式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(0, ge=0, description="每页条数"),
    summary_pattern: str = Query("", description="摘要正则过滤"),
    tag_name_pattern: str = Query("", description="标签名正则过滤"),
):
    """获取项目标签列表."""
    result = api_project_tags_info(
        project_id=project_id,
        group_name=group_name,
        view_mode=view_mode,
        page=page,
        size=size,
        summary_pattern=summary_pattern,
        tag_name_pattern=tag_name_pattern,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/tags")
async def register_tag(
    project_id: str = Query(..., description="项目 ID"),
    tag_name: str = Query(..., description="标签名称"),
    summary: str = Query(..., description="标签语义摘要"),
    aliases: str = Query("", description="别名（逗号分隔）"),
):
    """注册项目标签."""
    result = api_tag_register(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary,
        aliases=aliases,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"), message="标签注册成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.put("/tags/merge")
async def merge_tags(
    project_id: str = Query(..., description="项目 ID"),
    old_tag: str = Query(..., description="旧标签名称"),
    new_tag: str = Query(..., description="新标签名称"),
):
    """合并标签：将所有 old_tag 的引用迁移到 new_tag."""
    result = api_tag_merge(
        project_id=project_id,
        old_tag=old_tag,
        new_tag=new_tag,
    )
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"), message="标签合并成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.put("/tags/{tag_name}")
async def update_tag(
    project_id: str = Query(..., description="项目 ID"),
    tag_name: str = Path(..., description="标签名称"),
    summary: str = Query(..., description="新摘要"),
):
    """更新已注册标签的语义信息."""
    result = api_tag_update(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary,
    )
    if result.get("success"):
        return ApiResponse.success(message="标签更新成功")
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/tags/{tag_name}")
async def delete_tag(
    project_id: str = Query(..., description="项目 ID"),
    tag_name: str = Path(..., description="标签名称"),
    force: str = Query("false", description="是否强制删除"),
):
    """删除标签注册."""
    result = api_tag_delete(
        project_id=project_id,
        tag_name=tag_name,
        force=force,
    )
    if result.get("success"):
        return ApiResponse.success(message="标签删除成功")
    raise HTTPException(status_code=400, detail=result.get("error"))