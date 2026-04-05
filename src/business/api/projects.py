"""Business API - Projects 路由."""

from fastapi import APIRouter, HTTPException, Body
from typing import Optional

from business.core.groups import (
    validate_group_name,
    is_group_with_status,
    UnifiedGroupConfig,
    CONTENT_SEPARATE_GROUPS,
)
from business.core.utils import paginate, resolve_default_size, validate_view_mode, validate_regex_pattern, apply_view_mode, parse_tags, validate_date, filter_tags_by_regex
from business.models.response import ApiResponse

# 全局服务实例（由 main.py 导入时注入）
_storage = None
_project_service = None
_tag_service = None


def init_services(storage, project_service, tag_service):
    """初始化服务实例."""
    global _storage, _project_service, _tag_service
    _storage = storage
    _project_service = project_service
    _tag_service = tag_service


router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects")
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
        raise HTTPException(status_code=400, detail=error_msg)

    name_regex, error_msg = validate_regex_pattern(name_pattern, "name_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    size = resolve_default_size(size, view_mode)
    result = await _project_service.list_projects(include_archived=include_archived)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    projects = result["projects"]
    total = result["total"]

    if name_regex:
        projects = [p for p in projects if name_regex.search(p.get("name", ""))]

    pr, err = paginate(projects, page, size)
    if err:
        raise HTTPException(status_code=400, detail=err)
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

    return ApiResponse(success=True, data=response_data).to_dict()


@router.post("/projects")
async def register_project(
    name: str,
    path: str = "",
    summary: str = "",
    tags: str = ""
):
    """注册新项目."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = await _project_service.register_project(name, path, summary, tag_list)
    if result["success"]:
        data = {k: v for k, v in result.items() if k not in ("success", "error", "message")}
        return ApiResponse(success=True, data=data, message="项目注册成功").to_dict()

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": error,
                "message": result.get("message", "项目已被其他操作修改，请刷新后重试"),
                "retryable": True
            }
        )
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """获取项目详情."""
    result = await _project_service.get_project(project_id)
    if result["success"]:
        return ApiResponse(success=True, data=result.get("data")).to_dict()
    raise HTTPException(status_code=404, detail=result.get("error"))


@router.put("/projects/{project_id}/rename")
async def rename_project(project_id: str, new_name: str):
    """重命名项目."""
    result = await _project_service.project_rename(project_id, new_name)
    if result["success"]:
        return ApiResponse(success=True, data=result, message="项目重命名成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/projects/{project_id}")
async def remove_project(project_id: str, mode: str = "archive"):
    """删除或归档项目."""
    result = await _project_service.remove_project(project_id, mode)
    if result["success"]:
        action = "归档" if mode == "archive" else "删除"
        return ApiResponse(success=True, message=f"项目{action}成功").to_dict()
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/projects/{project_id}/groups")
async def list_groups(project_id: str):
    """列出项目的所有分组."""
    result = await _project_service.list_groups(project_id)
    if result["success"]:
        return ApiResponse(success=True, data={"groups": result.get("groups")}).to_dict()
    raise HTTPException(status_code=404, detail=result.get("error"))


@router.get("/projects/{project_id}/tags")
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
        raise HTTPException(status_code=400, detail=error_msg)

    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    tag_name_regex, error_msg = validate_regex_pattern(tag_name_pattern, "tag_name_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    size = resolve_default_size(size, view_mode)

    items_list = None
    total_count = 0
    data_key = "tags"
    total_key = "total_tags"
    summary_fields = ["tag", "summary"]
    extra_fields = {}
    msg_suffix = "已注册标签"

    if not group_name:
        result = await _tag_service.list_all_registered_tags(project_id)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
    elif tag_name:
        result = await _tag_service.query_by_tag(project_id, group_name, tag_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        items_list = result.get("items", [])
        total_count = result.get("total", 0)
        data_key = "items"
        total_key = "total"
        summary_fields = ["id", "summary", "tags"]
        extra_fields = {"group_name": group_name, "tag_name": tag_name, "tag_info": result.get("tag_info")}
        msg_suffix = "条目"
    elif unregistered_only:
        result = await _tag_service.list_unregistered_tags(project_id, group_name)
        data = {"project_id": project_id, "group_name": group_name, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])}
        return ApiResponse(success=True, data=data, message=f"共 {result.get('total_tags', 0)} 个未注册标签").to_dict()
    else:
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        result = await _tag_service.list_group_tags(project_id, group_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
        extra_fields = {"group_name": group_name}
        msg_suffix = "标签"

    if summary_regex or tag_name_regex:
        items_list = filter_tags_by_regex(items_list, summary_regex, tag_name_regex)

    pr, err = paginate(items_list, page, size)
    if err:
        raise HTTPException(status_code=400, detail=err)
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

    return ApiResponse(success=True, data=response_data, message=f"共 {pr.filtered_total} 个{msg_suffix}").to_dict()


@router.get("/projects/{project_id}/items")
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
        raise HTTPException(status_code=400, detail=error_msg)

    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    for _, param_val in [
        ("created_after", created_after),
        ("created_before", created_before),
        ("updated_after", updated_after),
        ("updated_before", updated_before),
    ]:
        if param_val and not validate_date(param_val):
            raise HTTPException(status_code=400, detail=f"无效的日期格式: {param_val} (要求 YYYY-MM-DD)")

    size = resolve_default_size(size, view_mode)
    result = await _project_service.get_project(project_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))

    data = result["data"]

    if group_name:
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        items = data.get(group_name, [])

        if item_id:
            item = None
            for it in items:
                if it.get("id") == item_id:
                    item = it.copy()
                    break
            if not item:
                raise HTTPException(status_code=404, detail=f"在分组 '{group_name}' 中找不到条目 '{item_id}'")
            if group_name in CONTENT_SEPARATE_GROUPS:
                item_content = await _storage.get_item_content(project_id, group_name, item_id)
                if item_content is not None:
                    item["content"] = item_content
            return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "item": item}, message="获取条目详情成功").to_dict()

        filtered_items = items
        tag_list = parse_tags(tags) if tags else []

        if is_group_with_status(group_name):
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
            raise HTTPException(status_code=400, detail=err)
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
        return ApiResponse(success=True, data=response_data, message=f"共 {filtered_total} 个条目").to_dict()

    return ApiResponse(success=True, data={
        "project_id": project_id,
        "info": data['info'],
        "groups": {
            "features": {"count": len(data["features"])},
            "notes": {"count": len(data["notes"])},
            "fixes": {"count": len(data.get("fixes", []))},
            "standards": {"count": len(data.get("standards", []))}
        }
    }, message="获取项目信息成功").to_dict()


@router.post("/projects/{project_id}/items")
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
    group_configs = await _storage.get_group_configs(project_id)
    all_groups_raw = group_configs.get("groups", {})
    all_groups = {
        name: UnifiedGroupConfig.from_dict(cfg) if isinstance(cfg, dict) else cfg
        for name, cfg in all_groups_raw.items()
    }
    default_rules = group_configs.get("group_settings", {}).get("default_related_rules", {})

    v = _project_service.validate_add_item(group, content, summary, status, severity, related, tag_list, all_groups, default_rules)
    if not v["success"]:
        raise HTTPException(status_code=400, detail=v["error"])

    related_dict = v["related_dict"]

    result = await _project_service.add_item(
        project_id=project_id, group=group, content=content, summary=summary,
        status=status, severity=severity, related=related_dict, tags=tag_list
    )

    if result["success"]:
        data = {
            "project_id": project_id, "group": group, "item_id": result["item_id"],
            "item": {"id": result["item_id"], "summary": summary, "content": content, "tags": tag_list}
        }
        if status:
            data["item"]["status"] = status
        if severity and severity != "medium":
            data["item"]["severity"] = severity
        if related_dict:
            data["item"]["related"] = related_dict
        return ApiResponse(success=True, data=data, message=f"条目 '{result['item_id']}' 已添加").to_dict()

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": error,
                "message": result.get("message", "分组已被其他操作修改，请稍后重试"),
                "retryable": True
            }
        )
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.put("/projects/{project_id}/items/{item_id}")
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
    group_configs = await _storage.get_group_configs(project_id)
    all_groups_raw = group_configs.get("groups", {})
    all_groups = {
        name: UnifiedGroupConfig.from_dict(cfg) if isinstance(cfg, dict) else cfg
        for name, cfg in all_groups_raw.items()
    }
    default_rules = group_configs.get("group_settings", {}).get("default_related_rules", {})

    v = _project_service.validate_update_item(group, item_id, content, summary, related, all_groups, default_rules)
    if not v["success"]:
        raise HTTPException(status_code=400, detail=v["error"])

    related_dict = v.get("related_dict")

    result = await _project_service.update_item(
        project_id=project_id, group=group, item_id=item_id,
        content=content, summary=summary, status=status,
        severity=severity, related=related_dict,
        tags=parse_tags(tags) if tags else None,
        expected_version=version
    )

    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "group": group, "item_id": item_id, "item": result["item"], "version": result.get("version")}, message=f"条目 '{item_id}' 已更新").to_dict()

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": error,
                "message": result.get("message", "数据已被其他操作修改，请刷新后重试"),
                "current_version": result.get("current_version"),
                "expected_version": result.get("expected_version"),
                "retryable": True,
                "current_item": result.get("current_item") or result.get("old_item")
            }
        )

    raise HTTPException(status_code=400, detail=result.get("error"))


@router.delete("/projects/{project_id}/items/{item_id}")
async def project_delete(project_id: str, group: str, item_id: str):
    """删除项目条目."""
    is_valid, error_msg = validate_group_name(group)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id 参数不能为空")

    result = await _project_service.delete_item(project_id=project_id, group=group, item_id=item_id)
    if result["success"]:
        return ApiResponse(success=True, data={"project_id": project_id, "group": group, "item_id": item_id, "deleted": True}, message=f"条目 '{item_id}' 已删除").to_dict()

    # 处理并发冲突
    error = result.get("error")
    if error in ("version_conflict", "concurrent_update"):
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": error,
                "message": result.get("message", "分组已被其他操作修改，请稍后重试"),
                "retryable": True
            }
        )
    raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/projects/{project_id}/items/{item_id}/tags")
async def manage_item_tags(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
):
    """管理条目标签."""
    is_valid, error_msg = validate_group_name(group_name)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    if operation == "set" or operation == "设置":
        if not tags:
            raise HTTPException(status_code=400, detail="operation='set' 时 tags 参数不能为空")
        tag_list = [t.strip() for t in tags.split(",")]
        result = await _project_service.update_item(project_id, group_name, item_id, tags=tag_list)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "set", "tags": result.get('tags', tag_list)}).to_dict()

    elif operation == "add" or operation == "添加":
        if not tag:
            raise HTTPException(status_code=400, detail="operation='add' 时 tag 参数不能为空")
        result = await _tag_service.add_item_tag(project_id, group_name, item_id, tag)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "add", "tag": tag, "tags": result.get("tags", [])}).to_dict()

    elif operation == "remove" or operation == "移除":
        if not tag:
            raise HTTPException(status_code=400, detail="operation='remove' 时 tag 参数不能为空")
        result = await _tag_service.remove_item_tag(project_id, group_name, item_id, tag)
        return ApiResponse(success=True, data={"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "remove", "tag": tag, "tags": result.get("tags", [])}).to_dict()

    else:
        raise HTTPException(status_code=400, detail=f"无效的操作类型: {operation} (支持: set/add/remove)")
