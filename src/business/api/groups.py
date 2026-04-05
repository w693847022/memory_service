"""Business API - Groups 路由."""

from fastapi import APIRouter, HTTPException

from business.core.groups import UnifiedGroupConfig, GroupType, all_group_names
from business.models.response import ApiResponse

# 全局服务实例
_storage = None


def init_services(storage):
    """初始化服务实例."""
    global _storage
    _storage = storage


router = APIRouter(prefix="/api", tags=["groups"])


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
    async with _storage.barrier.group_create(project_id):
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
            return ApiResponse(success=True, message=f"自定义组 '{group_name}' 创建成功").to_dict()
    raise HTTPException(status_code=400, detail="保存配置失败")


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
    async with _storage.barrier.group_update(project_id):
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
            return ApiResponse(success=True, message=f"组 '{group_name}' 更新成功").to_dict()
    raise HTTPException(status_code=400, detail="保存配置失败")


@router.delete("/groups/custom")
async def delete_custom_group(project_id: str, group_name: str):
    """删除自定义组."""
    async with _storage.barrier.group_delete(project_id, group_name):
        group_configs = await _storage.get_group_configs(project_id)
        groups = group_configs.get("groups", {})

        if group_name not in groups:
            raise HTTPException(status_code=404, detail=f"自定义组 '{group_name}' 不存在")

        if group_name in all_group_names():
            raise HTTPException(status_code=400, detail="不能删除内置组")

        del groups[group_name]
        group_configs["groups"] = groups

        if await _storage.save_group_configs(project_id, group_configs):
            return ApiResponse(success=True, message=f"自定义组 '{group_name}' 已删除").to_dict()
    raise HTTPException(status_code=400, detail="保存配置失败")


@router.get("/groups/settings")
async def get_group_settings(project_id: str):
    """获取组设置."""
    group_configs = await _storage.get_group_configs(project_id)
    settings = group_configs.get("group_settings", {})
    return ApiResponse(success=True, data={"settings": settings, "group_settings": settings}).to_dict()


@router.put("/groups/settings")
async def update_group_settings(project_id: str, default_related_rules: dict = None):
    """更新组设置."""
    async with _storage.barrier.group_settings(project_id):
        group_configs = await _storage.get_group_configs(project_id)

        if default_related_rules is not None:
            if "group_settings" not in group_configs:
                group_configs["group_settings"] = {}
            group_configs["group_settings"]["default_related_rules"] = default_related_rules

        if await _storage.save_group_configs(project_id, group_configs):
            return ApiResponse(success=True, message="组设置更新成功").to_dict()
    raise HTTPException(status_code=400, detail="保存配置失败")
