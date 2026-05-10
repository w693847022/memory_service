"""统计 API 路由."""

import logging

from fastapi import APIRouter, Query, Body, Request

from clients.business_async_client import BusinessApiAsyncClient
from src.models.requests.stats import StatsCleanupRequest
from src.models.responses.api_responses import StatsResponse, MessageResponse
from src.rest_api.utils.handlers import handle_result

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_async_client(request: Request) -> BusinessApiAsyncClient:
    """获取异步客户端."""
    return request.app.state.async_client


# ===================
# 统计 API
# ===================

@router.get("/stats", response_model=StatsResponse)
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

    return await handle_result(result)


@router.get("/stats/summary", response_model=StatsResponse)
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
    return await handle_result(result)


@router.delete("/stats/cleanup", response_model=MessageResponse)
async def cleanup_stats(
    request: Request,
    body: StatsCleanupRequest = Body(...),
):
    """清理过期统计数据."""
    client = _get_async_client(request)
    result = await client.stats_cleanup(retention_days=body.retention_days)
    return await handle_result(result, message="统计数据清理成功")
