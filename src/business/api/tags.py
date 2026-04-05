"""Business API - Tags 路由."""

from fastapi import APIRouter, HTTPException

from business.models.response import ApiResponse

# 全局服务实例
_tag_service = None


def init_services(tag_service):
    """初始化服务实例."""
    global _tag_service
    _tag_service = tag_service


router = APIRouter(prefix="/api", tags=["tags"])


@router.post("/tags/register")
async def tag_register(project_id: str, tag_name: str, summary: str, aliases: str = ""):
    """注册项目标签."""
    alias_list = [a.strip() for a in aliases.split(",")] if aliases else []
    result = await _tag_service.register_tag(project_id=project_id, tag_name=tag_name, summary=summary, aliases=alias_list)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "tag_name": tag_name, "tag_info": result.get("tag_info", {})}, message="标签注册成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.put("/tags/update")
async def tag_update(project_id: str, tag_name: str, summary: str = None):
    """更新已注册标签."""
    result = await _tag_service.update_tag(project_id=project_id, tag_name=tag_name, summary=summary)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "tag_name": tag_name, "updated": True}, message="标签更新成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/tags/delete")
async def tag_delete(project_id: str, tag_name: str, force: str = "false"):
    """删除标签注册."""
    force_flag = force.lower() == "true"
    result = await _tag_service.delete_tag(project_id=project_id, tag_name=tag_name, force=force_flag)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "tag_name": tag_name, "force": force_flag, "deleted": True}, message="标签删除成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/tags/merge")
async def tag_merge(project_id: str, old_tag: str, new_tag: str):
    """合并标签."""
    result = await _tag_service.merge_tags(project_id=project_id, old_tag=old_tag, new_tag=new_tag)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "old_tag": old_tag, "new_tag": new_tag, "merged": True}, message="标签合并成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))
