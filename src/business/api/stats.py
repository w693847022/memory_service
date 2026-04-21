"""Business API - Stats 路由."""

from fastapi import APIRouter, HTTPException

from src.models import ApiResponse
from src.models.responses.api_responses import (
    StatsResponse,
    MessageResponse,
)
from src.models.responses.data_types import (
    GlobalStatsData,
    ToolStatsData,
    ProjectStatsData,
    DailyStatsData,
    StatsCleanupResult,
)

# 全局服务实例
_storage = None
_stats_service = None


def init_services(storage, stats_service):
    """初始化服务实例."""
    global _storage, _stats_service
    _storage = storage
    _stats_service = stats_service


def _get_storage():
    """获取存储服务实例（类型安全）."""
    assert _storage is not None, "Storage service not initialized"
    return _storage


def _get_stats_service():
    """获取统计服务实例（类型安全）."""
    assert _stats_service is not None, "Stats service not initialized"
    return _stats_service


router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def project_stats():
    """获取全局统计信息."""
    await _get_storage().refresh_projects_cache()
    all_projects = await _get_storage().list_all_projects()
    total_projects = len(all_projects)

    all_tags = []
    feature_stats = {"pending": 0, "in_progress": 0, "completed": 0}
    total_features = 0
    total_notes = 0
    feature_tag_counts = {}
    note_tag_counts = {}

    for pid in all_projects.keys():
        project_data = await _get_storage().get_project_data(pid)
        if project_data is None:
            continue
        all_tags.extend(project_data.metadata.tags)
        features = project_data.get_items("features")
        total_features += len(features)
        for feature in features:
            status = feature.status or "pending"
            if status in feature_stats:
                feature_stats[status] += 1
            for tag in feature.tags:
                feature_tag_counts[tag] = feature_tag_counts.get(tag, 0) + 1
        notes = project_data.get_items("notes")
        total_notes += len(notes)
        for note in notes:
            for tag in note.tags:
                note_tag_counts[tag] = note_tag_counts.get(tag, 0) + 1

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    stats = {
        "total_projects": total_projects,
        "total_features": total_features,
        "total_notes": total_notes,
        "feature_status": feature_stats,
        "top_project_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_feature_tags": sorted(feature_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_note_tags": sorted(note_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    }

    return StatsResponse(success=True, data=stats, message="获取统计成功")


@router.get("/stats/summary", response_model=StatsResponse)
async def stats_summary(type: str = "", tool_name: str = "", project_id: str = "", date: str = ""):
    """获取统计摘要."""
    if type == "tool" or type == "工具":
        if tool_name:
            result = _get_stats_service().get_tool_stats(tool_name)
            if not result["success"]:
                error_msg = result.get("error")
                if error_msg is None:
                    error_msg = "获取工具统计失败"
                raise HTTPException(status_code=400, detail=error_msg)
            return StatsResponse(success=True, data={
                "type": "tool", "tool_name": tool_name, "total": result['total'],
                "first_called": result.get('first_called'), "last_called": result.get('last_called'),
                "by_project": result.get("by_project", {}), "by_client": result.get("by_client", {}),
                "by_ip": result.get("by_ip", {})
            }, message=f"工具 '{tool_name}' 调用统计")
        else:
            result = _get_stats_service().get_tool_stats()
            if not result["success"]:
                error_msg = result.get("error")
                if error_msg is None:
                    error_msg = "获取工具统计失败"
                raise HTTPException(status_code=400, detail=error_msg)
            return StatsResponse(success=True, data={"type": "tool", "tools": result["tools"]}, message="所有工具调用统计")

    elif type == "project" or type == "项目":
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id 参数不能为空")
        result = _get_stats_service().get_project_stats(project_id)
        if not result["success"]:
            error_msg = result.get("error")
            if error_msg is None:
                error_msg = "获取项目统计失败"
            raise HTTPException(status_code=400, detail=error_msg)
        return StatsResponse(success=True, data={"type": "project", "project_id": project_id, "total_calls": result['total_calls'], "tools_called": result["tools_called"]}, message=f"项目 '{project_id}' 调用统计")

    elif type == "client" or type == "客户端":
        result = _get_stats_service().get_client_stats()
        if not result["success"]:
            error_msg = result.get("error")
            if error_msg is None:
                error_msg = "获取客户端统计失败"
            raise HTTPException(status_code=400, detail=error_msg)
        return StatsResponse(success=True, data={"type": "client", "clients": result["clients"]}, message="客户端调用统计")

    elif type == "ip" or type == "IP":
        result = _get_stats_service().get_ip_stats()
        if not result["success"]:
            error_msg = result.get("error")
            if error_msg is None:
                error_msg = "获取IP统计失败"
            raise HTTPException(status_code=400, detail=error_msg)
        return StatsResponse(success=True, data={"type": "ip", "ips": result["ips"]}, message="IP地址调用统计")

    elif type == "daily" or type == "每日":
        if date:
            result = _get_stats_service().get_daily_stats(date)
            if not result["success"]:
                error_msg = result.get("error")
                if error_msg is None:
                    error_msg = "获取每日统计失败"
                raise HTTPException(status_code=400, detail=error_msg)
            return StatsResponse(success=True, data={"type": "daily", "date": date, "total_calls": result['total_calls'], "tools": result["tools"]}, message=f"日期 '{date}' 统计")
        else:
            result = _get_stats_service().get_daily_stats()
            if not result["success"]:
                error_msg = result.get("error")
                if error_msg is None:
                    error_msg = "获取每日统计失败"
                raise HTTPException(status_code=400, detail=error_msg)
            return StatsResponse(success=True, data={"type": "daily", "recent_days": result["recent_days"], "stats": result["stats"]}, message="最近7天统计")

    elif type == "full" or type == "完整":
        result = _get_stats_service().get_full_summary()
        if not result["success"]:
            error_msg = result.get("error")
            if error_msg is None:
                error_msg = "获取完整统计失败"
            raise HTTPException(status_code=400, detail=error_msg)
        return StatsResponse(success=True, data={"type": "full", "metadata": result["metadata"], "tool_stats": result["tool_stats"], "client_stats": result["client_stats"], "ip_stats": result["ip_stats"], "daily_stats": result["daily_stats"]}, message="完整统计")

    else:
        result = _get_stats_service().get_full_summary()
        if not result["success"]:
            error_msg = result.get("error")
            if error_msg is None:
                error_msg = "获取统计摘要失败"
            raise HTTPException(status_code=400, detail=error_msg)
        return StatsResponse(success=True, data={"type": "summary", "metadata": result["metadata"], "tool_stats": result["tool_stats"], "client_stats": result["client_stats"], "daily_stats": result["daily_stats"]}, message="统计摘要")


@router.delete("/stats/cleanup", response_model=StatsResponse)
async def stats_cleanup(retention_days: int = 30):
    """清理过期统计数据."""
    result = _get_stats_service().cleanup_stats(retention_days)
    if not result["success"]:
        error_msg = result.get("error")
        if error_msg is None:
            error_msg = "清理统计数据失败"
        raise HTTPException(status_code=400, detail=error_msg)
    return StatsResponse(success=True, data={
        "retention_days": retention_days,
        "cutoff_date": result["cleanup_result"]['cutoff_date'],
        "cleanup_details": {
            "daily_stats_removed": result["cleanup_result"]['daily_stats_removed'],
            "tools_removed": result["cleanup_result"]['tools_removed'],
            "projects_cleaned": result["cleanup_result"]['projects_cleaned'],
            "clients_cleaned": result["cleanup_result"]['clients_cleaned'],
            "ips_cleaned": result["cleanup_result"]['ips_cleaned']
        },
        "storage_before": result["before"],
        "storage_after": result["after"]
    }, message="统计数据清理完成")
