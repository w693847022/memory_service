"""统计 API 路由."""

import logging

from fastapi import APIRouter, Query, HTTPException

from ..mcp_client import get_mcp_client
from ..main import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()
mcp_client = get_mcp_client()


# ===================
# 统计 API
# ===================

@router.get("/stats")
async def get_stats(
    type: str = Query("", description="统计类型 (tool/project/client/ip/daily/full)"),
):
    """获取全局统计信息."""
    if type:
        result = mcp_client.call_tool("stats_summary", type=type)
    else:
        result = mcp_client.call_tool("project_stats")

    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/stats/summary")
async def get_stats_summary(
    type: str = Query("", description="统计类型 (tool/project/client/ip/daily/full)"),
    tool_name: str = Query("", description="工具名称 (type=tool 时)"),
    project_id: str = Query("", description="项目 ID (type=project 时)"),
    date: str = Query("", description="日期 YYYY-MM-DD (type=daily 时)"),
):
    """获取统计摘要."""
    kwargs = {}
    if type:
        kwargs["type"] = type
    if tool_name:
        kwargs["tool_name"] = tool_name
    if project_id:
        kwargs["project_id"] = project_id
    if date:
        kwargs["date"] = date

    result = mcp_client.call_tool("stats_summary", **kwargs)
    if result.get("success"):
        return ApiResponse.success(data=result.get("data"))
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/stats/cleanup")
async def cleanup_stats(
    retention_days: int = Query(30, ge=1, description="保留天数"),
):
    """清理过期统计数据."""
    result = mcp_client.call_tool(
        "stats_cleanup",
        retention_days=retention_days,
    )
    if result.get("success"):
        return ApiResponse.success(message="统计数据清理成功")
    raise HTTPException(status_code=400, detail=result.get("error"))
