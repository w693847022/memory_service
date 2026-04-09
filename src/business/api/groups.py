"""Business API - Groups 路由."""

from fastapi import APIRouter, HTTPException, Body

from business.core.groups import UnifiedGroupConfig, GroupType, all_group_names
from business.core.barrier_decorator import barrier
from business.core.barrier_constants import OperationLevel
from src.models import ApiResponse

# 全局服务实例
_storage = None
_project_service = None


def init_services(storage, project_service=None):
    """初始化服务实例."""
    global _storage, _project_service
    _storage = storage
    _project_service = project_service


router = APIRouter(prefix="/api", tags=["groups"])


# 内部服务函数（使用装饰器）
@barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
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
    group_configs = await _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name in groups:
        raise HTTPException(status_code=400, detail=f"自定义组 '{group_name}' 已存在")

    new_group = UnifiedGroupConfig(
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=[g.strip() for g in allowed_related_to.split(",") if g.strip()] if allowed_related_to else [],
        enable_status=enable_status,
        enable_severity=enable_severity,
    )

    groups[group_name] = new_group.to_dict()
    group_configs["groups"] = groups

    if await _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"自定义组 '{group_name}' 创建成功"}
    raise HTTPException(status_code=400, detail="保存配置失败")


@barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
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
    group_configs = await _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name not in groups:
        raise HTTPException(status_code=404, detail=f"组 '{group_name}' 不存在")

    existing = groups[group_name]
    config = UnifiedGroupConfig.from_dict(existing) if isinstance(existing, dict) else existing

    if content_max_bytes is not None:
        config.content_max_bytes = content_max_bytes
    if summary_max_bytes is not None:
        config.summary_max_bytes = summary_max_bytes
    if allow_related is not None:
        config.allow_related = allow_related
    if allowed_related_to is not None:
        config.allowed_related_to = [g.strip() for g in allowed_related_to.split(",") if g.strip()]
    if enable_status is not None:
        config.enable_status = enable_status
    if enable_severity is not None:
        config.enable_severity = enable_severity

    groups[group_name] = config.to_dict()
    group_configs["groups"] = groups

    if await _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"组 '{group_name}' 更新成功"}
    raise HTTPException(status_code=400, detail="保存配置失败")


@barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
async def _delete_custom_group(project_id: str, group_name: str):
    """删除自定义组（内部函数）."""
    group_configs = await _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name not in groups:
        raise HTTPException(status_code=404, detail=f"自定义组 '{group_name}' 不存在")

    if group_name in all_group_names():
        raise HTTPException(status_code=400, detail="不能删除内置组")

    del groups[group_name]
    group_configs["groups"] = groups

    if await _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"自定义组 '{group_name}' 已删除"}
    raise HTTPException(status_code=400, detail="保存配置失败")


@barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
async def _update_group_settings(project_id: str, default_related_rules: dict = None):
    """更新组设置（内部函数）."""
    group_configs = await _storage.get_group_configs(project_id)

    if default_related_rules is not None:
        if "group_settings" not in group_configs:
            group_configs["group_settings"] = {}
        group_configs["group_settings"]["default_related_rules"] = default_related_rules

    if await _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": "组设置更新成功"}
    raise HTTPException(status_code=400, detail="保存配置失败")


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
        if _project_service is None:
            raise HTTPException(status_code=500, detail="项目服务未初始化")
        result = await _project_service.get_group_config(project_id, group)
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
        if _project_service is None:
            raise HTTPException(status_code=500, detail="项目服务未初始化")
        result = await _project_service.update_group_config(project_id, group, config)
        if result["success"]:
            return ApiResponse(success=True, message=result.get("message")).to_dict()
        raise HTTPException(status_code=400, detail=result.get("error"))
    else:
        # 更新全局设置（保持向后兼容）
        return await _update_group_settings(project_id, default_related_rules)
