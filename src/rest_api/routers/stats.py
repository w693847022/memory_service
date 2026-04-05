"""统计 API 路由."""

import logging

from fastapi import APIRouter, Query, HTTPException, Request

from clients.business_async_client import BusinessApiAsyncClient

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# ===================
# 统计 API
# ===================

@router.get("/stats")
async def get_stats(
    request: Request,
    type: str = Query("", description="统计类型 (tool/project/client/ip/daily/full)"),
):
    """获取全局统计信息."""
    client = _get_async_client(request)
    if type:
        result = await client.stats_summary(type=type)
    else:
        result = await client.project_stats()

    if result.success:
        return {"success": True, "data": result.data}
    raise HTTPException(status_code=400, detail=result.error)


@router.get("/stats/summary")
async def get_stats_summary(
    request: Request,
    type: str = Query("", description="统计类型 (tool/project/client/ip/daily/full)"),
    tool_name: str = Query("", description="工具名称 (type=tool 时)"),
    project_id: str = Query("", description="项目 ID (type=project 时)"),
    date: str = Query("", description="日期 YYYY-MM-DD (type=daily 时)"),
):
    """获取统计摘要."""
    client = _get_async_client(request)
    kwargs = {}
    if type:
        kwargs["type"] = type
    if tool_name:
        kwargs["tool_name"] = tool_name
    if project_id:
        kwargs["project_id"] = project_id
    if date:
        kwargs["date"] = date

    result = await client.stats_summary(**kwargs)
    if result.success:
        return {"success": True, "data": result.data}
    raise HTTPException(status_code=400, detail=result.error)


@router.delete("/stats/cleanup")
async def cleanup_stats(
    request: Request,
    retention_days: int = Query(30, ge=1, description="保留天数"),
):
    """清理过期统计数据."""
    client = _get_async_client(request)
    result = await client.stats_cleanup(retention_days=retention_days)
    if result.success:
        return {"success": True, "message": "统计数据清理成功"}
    raise HTTPException(status_code=400, detail=result.error)