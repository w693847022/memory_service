"""Business API - Projects 路由."""

from typing import Optional, TYPE_CHECKING, Any, Union

from fastapi import APIRouter, HTTPException, Body

from src.models.group import (
    UnifiedGroupConfig,
    DEFAULT_GROUP_CONFIGS,
)
from business.item_validator import ItemValidator
from business.core.utils import paginate, resolve_default_size, validate_view_mode, validate_regex_pattern, apply_view_mode, parse_tags, validate_date, filter_tags_by_regex
from src.models import ApiResponse
from src.models.responses.api_responses import (
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectOperationResponse,
    GroupListResponse,
    ItemListResponse,
    ItemDetailResponse,
    ItemOperationResponse,
    TagInfoResponse,
)

# 全局服务实例（由 main.py 导入时注入）
_storage = None
_project_service = None
_tag_service = None
_groups_service = None


def init_services(storage, project_service, tag_service, groups_service=None):
    """初始化服务实例."""
    global _storage, _project_service, _tag_service, _groups_service
    _storage = storage
    _project_service = project_service
    _tag_service = tag_service
    _groups_service = groups_service


def _get_storage():
    """获取存储服务实例（类型安全）."""
    assert _storage is not None, "Storage service not initialized"
    return _storage


def _get_project_service():
    """获取项目服务实例（类型安全）."""
    assert _project_service is not None, "Project service not initialized"
    return _project_service


def _get_tag_service():
    """获取标签服务实例（类型安全）."""
    assert _tag_service is not None, "Tag service not initialized"
    return _tag_service


def _get_groups_service():
    """获取组服务实例（类型安全）."""
    assert _groups_service is not None, "Groups service not initialized"
    return _groups_service


router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects", response_model=ApiResponse[Any])
async def list_projects(
    view_mode: str = "summary",
    page: int = 1,
    size: int = 0,
    name_pattern: str = "",
    include_archived: bool = False
):
    """列出所有项目."""
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    name_regex, error_msg = validate_regex_pattern(name_pattern, "name_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    size = resolve_default_size(size, view_mode)
    result = await _get_project_service().list_projects(include_archived=include_archived)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())

    projects = result["data"]["projects"]
    total = result["data"]["total"]

    if name_regex:
        projects = [p for p in projects if name_regex.search(p.get("name", ""))]

    pr, err = paginate(projects, page, size)
    if err:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(err).model_dump())
    assert pr is not None
    projects, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

    filtered_projects = apply_view_mode(projects, view_mode, ["id", "name", "summary", "tags", "status"])
    if view_mode == "summary":
        for p in filtered_projects:
            if p.get("status") is None:
                p["status"] = "active"

    response_data = {
        "total": total,
        "filtered_total": filtered_total,
        "projects": filtered_projects
    }
    if pagination_meta:
        response_data.update(pagination_meta)
    if name_pattern:
        response_data["filters"] = {"name_pattern": name_pattern}

    return ApiResponse(success=True, data=response_data)


@router.post("/projects", response_model=ProjectOperationResponse)
async def register_project(
    name: str = Body(...),
    path: str = Body(""),
    summary: str = Body(""),
    tags: str = Body("")
):
    """注册新项目."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = await _get_project_service().register_project(name, path, summary, tag_list)
    if result["success"]:
        return ApiResponse(success=True, data=result["data"], message="项目注册成功")

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        # 直接返回冲突信息，不使用 ApiResponse.error_response 包装
        conflict_detail = {
            "error": error,
            "message": result.get("message", "项目已被其他操作修改，请刷新后重试"),
            "retryable": True
        }
        raise HTTPException(status_code=409, detail=conflict_detail)
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    """获取项目详情."""
    result = await _get_project_service().get_project(project_id)
    if result["success"]:
        return ApiResponse(success=True, data=result.get("data"))
    raise HTTPException(status_code=404, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.put("/projects/{project_id}/rename", response_model=ProjectOperationResponse)
async def rename_project(project_id: str, new_name: str):
    """重命名项目."""
    result = await _get_project_service().project_rename(project_id, new_name)
    if result["success"]:
        return ApiResponse(success=True, data=result["data"], message="项目重命名成功")
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.delete("/projects/{project_id}", response_model=ProjectOperationResponse)
async def delete_project(project_id: str):
    """永久删除项目."""
    result = await _get_project_service().delete_project(project_id)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id}, message="项目删除成功")
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.post("/projects/{project_id}/archive", response_model=ProjectOperationResponse)
async def archive_project(project_id: str):
    """归档项目."""
    result = await _get_project_service().archive_project(project_id)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "mode": "archive"}, message="项目归档成功")
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.get("/projects/{project_id}/groups", response_model=GroupListResponse)
async def list_groups(project_id: str):
    """列出项目的所有分组."""
    result = await _get_groups_service().list_groups(project_id)
    if result["success"]:
        return ApiResponse(success=True, data={"groups": result.get("groups")})
    raise HTTPException(status_code=404, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.get("/projects/{project_id}/tags", response_model=TagInfoResponse)
async def project_tags_info(
    project_id: str,
    group_name: str = "",
    tag_name: str = "",
    unregistered_only: bool = False,
    page: int = 1,
    size: int = 0,
    view_mode: str = "summary",
    summary_pattern: str = "",
    tag_name_pattern: str = ""
):
    """查询标签信息."""
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    tag_name_regex, error_msg = validate_regex_pattern(tag_name_pattern, "tag_name_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    size = resolve_default_size(size, view_mode)

    items_list = None
    total_count = 0
    data_key = "tags"
    total_key = "total_tags"
    summary_fields = ["tag", "summary"]
    extra_fields = {}
    msg_suffix = "已注册标签"

    if not group_name:
        result = await _get_tag_service().list_all_registered_tags(project_id)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
    elif tag_name:
        result = await _get_tag_service().query_by_tag(project_id, group_name, tag_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())
        items_list = result.get("items", [])
        total_count = result.get("total", 0)
        data_key = "items"
        total_key = "total"
        summary_fields = ["id", "summary", "tags"]
        extra_fields = {"group_name": group_name, "tag_name": tag_name, "tag_info": result.get("tag_info")}
        msg_suffix = "条目"
    elif unregistered_only:
        result = await _get_tag_service().list_unregistered_tags(project_id, group_name)
        data = {"project_id": project_id, "group_name": group_name, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])}
        return ApiResponse(success=True, data=data, message=f"共 {result.get('total_tags', 0)} 个未注册标签")
    else:
        all_configs = await _get_project_service().item_validator.get_all_configs(project_id)
        is_valid, error_msg = ItemValidator.validate_group_name(group_name, all_configs)
        if not is_valid:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())
        result = await _get_tag_service().list_group_tags(project_id, group_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
        extra_fields = {"group_name": group_name}
        msg_suffix = "标签"

    if summary_regex or tag_name_regex:
        items_list = filter_tags_by_regex(items_list, summary_regex, tag_name_regex)

    pr, err = paginate(items_list, page, size)
    if err:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(err).model_dump())
    assert pr is not None

    filtered_items = apply_view_mode(pr.items, view_mode, summary_fields)

    response_data = {
        "project_id": project_id,
        total_key: total_count,
        "filtered_total": pr.filtered_total,
        data_key: filtered_items
    }
    response_data.update(extra_fields)
    if pr.pagination_meta:
        response_data.update(pr.pagination_meta)

    if summary_pattern or tag_name_pattern:
        response_data["filters"] = {
            "summary_pattern": summary_pattern,
            "tag_name_pattern": tag_name_pattern
        }

    return ApiResponse(success=True, data=response_data, message=f"共 {pr.filtered_total} 个{msg_suffix}")


@router.get("/projects/{project_id}/items", response_model=Union[ItemListResponse, ItemDetailResponse, ApiResponse[Any]])
async def project_get(
    project_id: str,
    group_name: str = "",
    item_id: str = "",
    status: str = "",
    severity: str = "",
    tags: str = "",
    page: int = 1,
    size: int = 0,
    view_mode: str = "summary",
    summary_pattern: str = "",
    created_after: str = "",
    created_before: str = "",
    updated_after: str = "",
    updated_before: str = ""
):
    """获取项目信息或查询条目列表/详情."""
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    for _, param_val in [
        ("created_after", created_after),
        ("created_before", created_before),
        ("updated_after", updated_after),
        ("updated_before", updated_before),
    ]:
        if param_val and not validate_date(param_val):
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(f"无效的日期格式: {param_val} (要求 YYYY-MM-DD)").model_dump())

    size = resolve_default_size(size, view_mode)
    # 当不需要具体分组数据时，使用精简模式
    include_items = bool(group_name)
    result = await _get_project_service().get_project(project_id, include_items=include_items)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())

    data = result["data"]

    if group_name:
        all_configs = await _get_project_service().item_validator.get_all_configs(project_id)
        is_valid, error_msg = ItemValidator.validate_group_name(group_name, all_configs)
        if not is_valid:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

        items = data.get(group_name, [])

        if item_id:
            item = None
            for it in items:
                if it.get("id") == item_id:
                    item = it.copy()
                    break
            if not item:
                raise HTTPException(status_code=404, detail=ApiResponse.error_response(f"在分组 '{group_name}' 中找不到条目 '{item_id}'").model_dump())
            item_content = await _get_storage().get_item_content(project_id, group_name, item_id)
            if item_content is not None:
                item["content"] = item_content
            return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "item": item}, message="获取条目详情成功")

        filtered_items = items
        tag_list = parse_tags(tags) if tags else []

        all_configs = await _get_project_service().item_validator.get_all_configs(project_id)
        group_config = UnifiedGroupConfig.from_dict(all_configs.get(group_name, {}))
        if group_config.enable_status and group_config.status_values:
            if status:
                filtered_items = [f for f in filtered_items if f.get("status") == status]
            if severity:
                filtered_items = [f for f in filtered_items if f.get("severity") == severity]

        if tag_list:
            filtered_items = [f for f in filtered_items if any(tag in f.get("tags", []) for tag in tag_list)]

        if summary_regex or created_after or created_before or updated_after or updated_before:
            new_filtered = []
            for item in filtered_items:
                if summary_regex and not summary_regex.search(item.get("summary", "")):
                    continue
                created = (item.get("created_at") or "")[:10]
                if created_after and created < created_after:
                    continue
                if created_before and created > created_before:
                    continue
                updated = (item.get("updated_at") or "")[:10]
                if updated_after and (not updated or updated < updated_after):
                    continue
                if updated_before and (not updated or updated > updated_before):
                    continue
                new_filtered.append(item)
            filtered_items = new_filtered

        pr, err = paginate(filtered_items, page, size)
        if err:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response(err).model_dump())
        assert pr is not None
        paginated_items, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

        if view_mode == "summary":
            filtered_items_for_response = apply_view_mode(paginated_items, "summary", ["id", "summary", "tags"])
        else:
            filtered_items_for_response = [{k: v for k, v in item.items() if k != 'content'} for item in paginated_items]

        response_data = {
            "project_id": project_id,
            "project_name": data['info']['name'],
            "group_name": group_name,
            "total": len(items),
            "filtered_total": filtered_total,
            "items": filtered_items_for_response
        }
        if pagination_meta:
            response_data.update(pagination_meta)
        if status or severity or tags or summary_pattern or created_after or created_before or updated_after or updated_before:
            response_data["filters"] = {
                "status": status, "severity": severity, "tags": tags,
                "summary_pattern": summary_pattern,
                "created_after": created_after, "created_before": created_before,
                "updated_after": updated_after, "updated_before": updated_before,
            }
        return ApiResponse(success=True, data=response_data, message=f"共 {filtered_total} 个条目")

    return ApiResponse(success=True, data={
        "project_id": project_id,
        "info": data['info'],
        "groups": {
            "features": {"count": len(data.get("features", []))},
            "notes": {"count": len(data.get("notes", []))},
            "fixes": {"count": len(data.get("fixes", []))},
            "standards": {"count": len(data.get("standards", []))}
        }
    }, message="获取项目信息成功")


@router.post("/projects/{project_id}/items", response_model=ItemOperationResponse)
async def project_add(
    project_id: str,
    group: str,
    content: str = Body(""),
    summary: str = Body(""),
    status: str = Body(None),
    severity: str = Body("medium"),
    related: str = Body(""),
    tags: str = Body("")
):
    """添加项目条目."""
    tag_list = parse_tags(tags)

    v = await _get_project_service().validate_add_item(project_id, group, content, summary, status, severity, related, tag_list)
    if not v["success"]:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(v["error"]).model_dump())

    related_dict = v["related_dict"]

    result = await _get_project_service().add_item(
        project_id=project_id, group=group, content=content, summary=summary,
        status=status, severity=severity, related=related_dict, tags=tag_list
    )

    if result["success"]:
        return ApiResponse(success=True, data=result["data"], message=f"条目 '{result['data']['item_id']}' 已添加")

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        # 直接返回冲突信息，不使用 ApiResponse.error_response 包装
        conflict_detail = {
            "error": error,
            "message": result.get("message", "分组已被其他操作修改，请稍后重试"),
            "retryable": True
        }
        raise HTTPException(status_code=409, detail=conflict_detail)
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.put("/projects/{project_id}/items/{item_id}", response_model=ItemOperationResponse)
async def project_update(
    project_id: str,
    item_id: str,
    group: str,
    content: str = Body(None),
    summary: str = Body(None),
    status: str = Body(None),
    severity: str = Body(None),
    related: str = Body(None),
    tags: str = Body(None),
    version: Optional[int] = Body(None)
):
    """更新项目条目."""
    v = await _get_project_service().validate_update_item(project_id, group, item_id, content, summary, status, severity, related, parse_tags(tags) if tags else None)
    if not v["success"]:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(v["error"]).model_dump())

    related_dict = v.get("related_dict")

    result = await _get_project_service().update_item(
        project_id=project_id, group=group, item_id=item_id,
        content=content, summary=summary, status=status,
        severity=severity, related=related_dict,
        tags=parse_tags(tags) if tags else None,
        expected_version=version
    )

    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "group": group, "item_id": item_id, "item": result["data"]["item"], "version": result["data"].get("version")}, message=f"条目 '{item_id}' 已更新")

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        # 直接返回冲突信息，不使用 ApiResponse.error_response 包装
        # 这样测试可以直接访问 detail["current_version"]
        conflict_detail = {
            "error": error,
            "message": result.get("message", "数据已被其他操作修改，请刷新后重试"),
            "current_version": result.get("current_version"),
            "expected_version": result.get("expected_version"),
            "retryable": True,
            "current_item": result.get("current_item") or result.get("old_item")
        }
        raise HTTPException(status_code=409, detail=conflict_detail)

    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.delete("/projects/{project_id}/items/{item_id}", response_model=ItemOperationResponse)
async def project_delete(project_id: str, group: str, item_id: str):
    """删除项目条目."""
    all_configs = await _get_project_service().item_validator.get_all_configs(project_id)
    is_valid, error_msg = ItemValidator.validate_group_name(group, all_configs)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())
    if not item_id:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response("item_id 参数不能为空").model_dump())

    result = await _get_project_service().delete_item(project_id=project_id, group=group, item_id=item_id)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "group": group, "item_id": item_id, "deleted": True}, message=f"条目 '{item_id}' 已删除")

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        # 直接返回冲突信息，不使用 ApiResponse.error_response 包装
        conflict_detail = {
            "error": error,
            "message": result.get("message", "分组已被其他操作修改，请稍后重试"),
            "retryable": True
        }
        raise HTTPException(status_code=409, detail=conflict_detail)
    raise HTTPException(status_code=400, detail=ApiResponse.error_response(result.get("error") or "Unknown error").model_dump())


@router.post("/projects/{project_id}/items/{item_id}/tags", response_model=ItemOperationResponse)
async def manage_item_tags(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
):
    """管理条目标签."""
    all_configs = await _get_project_service().item_validator.get_all_configs(project_id)
    is_valid, error_msg = ItemValidator.validate_group_name(group_name, all_configs)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(error_msg or "Unknown error").model_dump())

    if operation == "set" or operation == "设置":
        if not tags:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response("operation='set' 时 tags 参数不能为空").model_dump())
        tag_list = [t.strip() for t in tags.split(",")]
        result = await _get_project_service().update_item(project_id, group_name, item_id, tags=tag_list)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "set", "tags": result.get('tags', tag_list)})

    elif operation == "add" or operation == "添加":
        if not tag:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response("operation='add' 时 tag 参数不能为空").model_dump())
        result = await _get_tag_service().add_item_tag(project_id, group_name, item_id, tag)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "add", "tag": tag, "tags": result.get("tags", [])})

    elif operation == "remove" or operation == "移除":
        if not tag:
            raise HTTPException(status_code=400, detail=ApiResponse.error_response("operation='remove' 时 tag 参数不能为空").model_dump())
        result = await _get_tag_service().remove_item_tag(project_id, group_name, item_id, tag)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "remove", "tag": tag, "tags": result.get("tags", [])})

    else:
        raise HTTPException(status_code=400, detail=ApiResponse.error_response(f"无效的操作类型: {operation} (支持: set/add/remove)").model_dump())
