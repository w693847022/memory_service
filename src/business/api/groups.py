"""Business API - Groups 路由."""

from fastapi import APIRouter, HTTPException, Body

from src.models.group import UnifiedGroupConfig
from src.models.enums import GroupType
from src.models import ApiResponse

# 全局服务实例
_storage = None
_project_service = None
_groups_service = None


def init_services(storage, project_service=None, groups_service=None):
    """初始化服务实例."""
    global _storage, _project_service, _groups_service
    _storage = storage
    _project_service = project_service
    _groups_service = groups_service


router = APIRouter(prefix="/api", tags=["groups"])


# 内部服务函数（barrier 由 GroupsService 层处理，API 层不加 barrier 避免双重锁死锁）
async def _create_custom_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = 240,
    summary_max_bytes: int = 90,
    allow_related: bool = False,
    allowed_related_to: str = "",
    enable_status: bool = True,
    enable_severity: bool = False
):
    """创建自定义组（内部函数）."""
    allowed_list = [g.strip() for g in allowed_related_to.split(",") if g.strip()] if allowed_related_to else []
    result = await _groups_service.create_custom_group(
        project_id, group_name, content_max_bytes, summary_max_bytes,
        allow_related, allowed_list, enable_status, enable_severity
    )
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "创建自定义组失败"))
    return result


async def _update_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = None,
    summary_max_bytes: int = None,
    allow_related: bool = None,
    allowed_related_to: str = None,
    enable_status: bool = None,
    enable_severity: bool = None
):
    """更新组配置（内部函数）."""
    config_data = {}
    if content_max_bytes is not None:
        config_data["content_max_bytes"] = content_max_bytes
    if summary_max_bytes is not None:
        config_data["summary_max_bytes"] = summary_max_bytes
    if allow_related is not None:
        config_data["allow_related"] = allow_related
    if allowed_related_to is not None:
        config_data["allowed_related_to"] = [g.strip() for g in allowed_related_to.split(",") if g.strip()]
    if enable_status is not None:
        config_data["enable_status"] = enable_status
    if enable_severity is not None:
        config_data["enable_severity"] = enable_severity
    result = await _groups_service.update_group_config(project_id, group_name, config_data)
    if not result.get("success", False):
        error_msg = result.get("error", "更新组配置失败")
        status_code = 404 if "不存在" in error_msg or "无效的分组类型" in error_msg else 400
        raise HTTPException(status_code=status_code, detail=error_msg)
    return result


async def _delete_custom_group(project_id: str, group_name: str):
    """删除自定义组（内部函数）."""
    result = await _groups_service.delete_custom_group(project_id, group_name)
    if not result.get("success", False):
        error_msg = result.get("error", "删除自定义组失败")
        status_code = 404 if "不存在" in error_msg else 400
        raise HTTPException(status_code=status_code, detail=error_msg)
    return result


async def _update_group_settings(project_id: str, default_related_rules: dict = None):
    """更新组设置（内部函数）."""
    result = await _groups_service.update_group_settings(project_id, default_related_rules)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "更新组设置失败"))
    return result


# 路由函数（调用内部函数）
@router.post("/groups/custom")
async def create_custom_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = 240,
    summary_max_bytes: int = 90,
    allow_related: bool = False,
    allowed_related_to: str = "",
    enable_status: bool = True,
    enable_severity: bool = False
):
    """创建自定义组."""
    return await _create_custom_group(
        project_id, group_name, content_max_bytes, summary_max_bytes,
        allow_related, allowed_related_to, enable_status, enable_severity
    )


@router.put("/groups/custom")
async def update_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = None,
    summary_max_bytes: int = None,
    allow_related: bool = None,
    allowed_related_to: str = None,
    enable_status: bool = None,
    enable_severity: bool = None
):
    """更新组配置."""
    return await _update_group(
        project_id, group_name, content_max_bytes, summary_max_bytes,
        allow_related, allowed_related_to, enable_status, enable_severity
    )


@router.delete("/groups/custom")
async def delete_custom_group(project_id: str, group_name: str):
    """删除自定义组."""
    return await _delete_custom_group(project_id, group_name)


@router.get("/groups/settings")
async def get_group_settings(project_id: str, group: str = ""):
    """获取组设置（支持单组查询）."""
    if group:
        # 获取单个组配置
        if _groups_service is None:
            raise HTTPException(status_code=500, detail="组服务未初始化")
        result = await _groups_service.get_group_config_for_api(project_id, group)
        if result["success"]:
            return ApiResponse(success=True, data={"config": result.get("config")}).to_dict()
        raise HTTPException(status_code=404, detail=result.get("error"))
    else:
        # 获取全局设置（保持向后兼容）
        group_configs = await _storage.get_group_configs(project_id)
        settings = group_configs.get("group_settings", {})
        return ApiResponse(success=True, data={"settings": settings}).to_dict()


@router.put("/groups/settings")
async def update_group_settings(
    project_id: str,
    group: str = "",
    default_related_rules: dict = None,
    config: dict = Body(None)
):
    """更新组设置（支持单组更新）."""
    if group:
        # 更新单个组配置
        if config is None:
            raise HTTPException(status_code=400, detail="更新组配置时必须提供 config 参数")
        if _groups_service is None:
            raise HTTPException(status_code=500, detail="组服务未初始化")
        result = await _groups_service.update_group_config(project_id, group, config)
        if result["success"]:
            return ApiResponse(success=True, message=result.get("message")).to_dict()
        raise HTTPException(status_code=400, detail=result.get("error"))
    else:
        # 更新全局设置（保持向后兼容）
        return await _update_group_settings(project_id, default_related_rules)
