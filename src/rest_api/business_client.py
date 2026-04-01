"""Business 服务客户端 - REST API 层调用 business 层的接口.

此模块提供 REST API 层直接调用 business 层服务的接口，
不通过 MCP 协议，直接使用 business 层服务。
"""

import os
from typing import Optional, Dict, List, Union

# 设置存储目录
storage_dir = os.environ.get("MCP_STORAGE_DIR", os.path.join(os.path.expanduser("~"), ".project_memory_ai"))

# 导入存储层
from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService
from business.stats_service import StatsService

# 导入辅助函数
from business.core.groups import (
    validate_group_name,
    is_group_with_status,
    UnifiedGroupConfig,
)
from business.models.response import ApiResponse
from business.core.utils import paginate, resolve_default_size, validate_view_mode, validate_regex_pattern, apply_view_mode

# 初始化 business 层服务
_storage = Storage(storage_dir=storage_dir)
_project_service = ProjectService(_storage)
_tag_service = TagService(_storage)
_stats_service = StatsService(_storage)


# ===================
# Helper Functions
# ===================

def _parse_tags(tags_str: str) -> list:
    """解析标签字符串为列表."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def _validate_date(date_str: str) -> bool:
    """验证日期字符串格式 (YYYY-MM-DD)."""
    if not date_str:
        return True
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _tool_response(result, success_data=None, success_message=None):
    """构建工具响应."""
    if result.get("success"):
        msg = success_message or result.get("message", "操作成功")
        return ApiResponse(success=True, data=success_data, message=msg).to_json()
    return ApiResponse(success=False, error=result.get("error", "未知错误")).to_json()


def _error_response(error):
    """构建错误响应."""
    return ApiResponse(success=False, error=error).to_json()


def _filter_tags_by_regex(tags_list: list, summary_regex=None, tag_name_regex=None) -> list:
    """正则过滤标签列表."""
    filtered = []
    for tag_item in tags_list:
        if summary_regex and not summary_regex.search(tag_item.get("summary", "")):
            continue
        if tag_name_regex and not tag_name_regex.search(tag_item.get("tag", "")):
            continue
        filtered.append(tag_item)
    return filtered


# ===================
# 项目管理 API 实现
# ===================

def api_project_list(
    view_mode: str = "summary",
    page: int = 1,
    size: int = 0,
    name_pattern: str = "",
    include_archived: bool = False
) -> Dict:
    """列出所有项目."""
    # 验证 view_mode 参数
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        return {"success": False, "error": error_msg}

    # 验证 name_pattern 正则有效性
    name_regex, error_msg = validate_regex_pattern(name_pattern, "name_pattern")
    if error_msg:
        return {"success": False, "error": error_msg}

    # 根据 view_mode 设置 size 默认值
    size = resolve_default_size(size, view_mode)

    result = _project_service.list_projects(include_archived=include_archived)

    if not result["success"]:
        return result

    projects = result["projects"]
    total = result["total"]

    # name_pattern 过滤
    if name_regex:
        projects = [p for p in projects if name_regex.search(p.get("name", ""))]

    # 分页处理
    pr, err = paginate(projects, page, size)
    if err:
        return {"success": False, "error": err}
    assert pr is not None
    projects, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

    # view_mode 字段过滤
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

    return {"success": True, "data": response_data}


def api_register_project(name: str, path: str = "", summary: str = "", tags: str = "") -> Dict:
    """注册新项目."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = _project_service.register_project(name, path, summary, tag_list)
    if result["success"]:
        data = {k: v for k, v in result.items() if k not in ("success", "error", "message")}
        return {"success": True, "data": data if data else None}
    return result


def api_get_project(project_id: str) -> Dict:
    """获取项目详情."""
    return _project_service.get_project(project_id)


def api_rename_project(project_id: str, new_name: str) -> Dict:
    """重命名项目."""
    return _project_service.project_rename(project_id, new_name)


def api_remove_project(project_id: str, mode: str = "archive") -> Dict:
    """删除或归档项目."""
    return _project_service.remove_project(project_id, mode)


def api_list_groups(project_id: str) -> Dict:
    """列出项目的所有分组."""
    return _project_service.list_groups(project_id)


def api_project_tags_info(
    project_id: str,
    group_name: str = "",
    tag_name: str = "",
    unregistered_only: bool = False,
    page: int = 1,
    size: int = 0,
    view_mode: str = "summary",
    summary_pattern: str = "",
    tag_name_pattern: str = ""
) -> Dict:
    """查询标签信息."""
    # 统一参数验证
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        return {"success": False, "error": error_msg}

    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        return {"success": False, "error": error_msg}

    tag_name_regex, error_msg = validate_regex_pattern(tag_name_pattern, "tag_name_pattern")
    if error_msg:
        return {"success": False, "error": error_msg}

    size = resolve_default_size(size, view_mode)

    # 根据不同模式获取原始列表
    items_list = None
    total_count = 0
    data_key = "tags"
    total_key = "total_tags"
    summary_fields = ["tag", "summary"]
    extra_fields = {}
    msg_suffix = "已注册标签"

    if not group_name:
        result = _tag_service.list_all_registered_tags(project_id)
        if not result.get("success"):
            return result
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
    elif tag_name:
        result = _tag_service.query_by_tag(project_id, group_name, tag_name)
        if not result.get("success"):
            return result
        items_list = result.get("items", [])
        total_count = result.get("total", 0)
        data_key = "items"
        total_key = "total"
        summary_fields = ["id", "summary", "tags"]
        extra_fields = {"group_name": group_name, "tag_name": tag_name, "tag_info": result.get("tag_info")}
        msg_suffix = "条目"
    elif unregistered_only:
        result = _tag_service.list_unregistered_tags(project_id, group_name)
        return {"success": True, "data": {"project_id": project_id, "group_name": group_name, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])}, "message": f"共 {result.get('total_tags', 0)} 个未注册标签"}
    else:
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            return {"success": False, "error": error_msg}
        result = _tag_service.list_group_tags(project_id, group_name)
        if not result.get("success"):
            return result
        items_list = result.get("tags", [])
        total_count = result.get("total_tags", 0)
        extra_fields = {"group_name": group_name}
        msg_suffix = "标签"

    # 统一的正则过滤
    if summary_regex or tag_name_regex:
        items_list = _filter_tags_by_regex(items_list, summary_regex, tag_name_regex)

    # 统一分页
    pr, err = paginate(items_list, page, size)
    if err:
        return {"success": False, "error": err}
    assert pr is not None

    # 统一 view_mode 字段过滤
    filtered_items = apply_view_mode(pr.items, view_mode, summary_fields)

    # 统一响应组装
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

    return {"success": True, "data": response_data}


def api_project_get(
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
) -> Dict:
    """获取项目信息或查询条目列表/详情."""
    # 验证 view_mode 参数
    is_valid, error_msg = validate_view_mode(view_mode)
    if not is_valid:
        return {"success": False, "error": error_msg}

    # 验证 summary_pattern 正则有效性
    summary_regex, error_msg = validate_regex_pattern(summary_pattern, "summary_pattern")
    if error_msg:
        return {"success": False, "error": error_msg}

    # 验证时间范围参数格式
    for _, param_val in [
        ("created_after", created_after),
        ("created_before", created_before),
        ("updated_after", updated_after),
        ("updated_before", updated_before),
    ]:
        if param_val and not _validate_date(param_val):
            return {"success": False, "error": f"无效的日期格式: {param_val} (要求 YYYY-MM-DD)"}

    # 根据 view_mode 设置 size 默认值
    size = resolve_default_size(size, view_mode)

    result = _project_service.get_project(project_id)

    if not result["success"]:
        return result

    data = result["data"]

    # 如果指定了 group_name
    if group_name:
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            return {"success": False, "error": error_msg}

        items = data.get(group_name, [])

        # 如果指定了 item_id，返回单个条目详情
        if item_id:
            item = None
            for it in items:
                if it.get("id") == item_id:
                    item = it.copy()
                    break

            if not item:
                return {"success": False, "error": f"在分组 '{group_name}' 中找不到条目 '{item_id}'"}

            # 对于 notes 分组，从 .md 文件加载 content
            if group_name == "notes":
                note_content = _storage._load_note_content(project_id, item_id)
                if note_content is not None:
                    item["content"] = note_content

            return {"success": True, "data": {"project_id": project_id, "group_name": group_name, "item_id": item_id, "item": item}}

        # 如果只指定了 group_name 但没有 item_id，返回该分组列表
        filtered_items = items

        # 解析 tags 参数
        tag_list = _parse_tags(tags) if tags else []

        # 应用过滤条件
        if is_group_with_status(group_name):
            if status:
                filtered_items = [f for f in filtered_items if f.get("status") == status]
            if severity:
                filtered_items = [f for f in filtered_items if f.get("severity") == severity]

        # tags 过滤：OR 逻辑
        if tag_list:
            filtered_items = [f for f in filtered_items if any(tag in f.get("tags", []) for tag in tag_list)]

        # summary 正则过滤 + 时间范围过滤
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

        # 分页处理
        pr, err = paginate(filtered_items, page, size)
        if err:
            return {"success": False, "error": err}
        assert pr is not None
        paginated_items, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

        # 列表模式根据 view_mode 决定返回字段
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
                "status": status,
                "severity": severity,
                "tags": tags,
                "summary_pattern": summary_pattern,
                "created_after": created_after,
                "created_before": created_before,
                "updated_after": updated_after,
                "updated_before": updated_before,
            }

        return {"success": True, "data": response_data}

    # 默认行为：返回精简的项目概览
    return {
        "success": True,
        "data": {
            "project_id": project_id,
            "info": data['info'],
            "groups": {
                "features": {"count": len(data["features"])},
                "notes": {"count": len(data["notes"])},
                "fixes": {"count": len(data.get("fixes", []))},
                "standards": {"count": len(data.get("standards", []))}
            }
        }
    }


def api_project_add(
    project_id: str,
    group: str,
    content: str = "",
    summary: str = "",
    status: Optional[str] = None,
    severity: str = "medium",
    related: Union[str, Dict[str, List[str]], None] = "",
    tags: str = ""
) -> Dict:
    """添加项目条目."""
    tag_list = _parse_tags(tags)

    # 加载组配置
    group_configs = _storage.get_group_configs(project_id)
    all_groups_raw = group_configs.get("groups", {})
    all_groups = {
        name: UnifiedGroupConfig.from_dict(cfg) if isinstance(cfg, dict) else cfg
        for name, cfg in all_groups_raw.items()
    }
    default_rules = group_configs.get("group_settings", {}).get("default_related_rules", {})

    v = _project_service.validate_add_item(group, content, summary, status, severity, related, tag_list, all_groups, default_rules)
    if not v["success"]:
        return {"success": False, "error": v["error"]}

    related_dict = v["related_dict"]

    result = _project_service.add_item(
        project_id=project_id,
        group=group,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related_dict,
        tags=tag_list
    )

    if result["success"]:
        data = {
            "project_id": project_id,
            "group": group,
            "item_id": result["item_id"],
            "item": {
                "id": result["item_id"],
                "summary": summary,
                "content": content,
                "tags": tag_list,
            }
        }
        if status:
            data["item"]["status"] = status
        if severity and severity != "medium":
            data["item"]["severity"] = severity
        if related_dict:
            data["item"]["related"] = related_dict
        return {"success": True, "data": data}
    return result


def api_project_update(
    project_id: str,
    group: str,
    item_id: str,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    related: Optional[Union[str, Dict[str, List[str]]]] = None,
    tags: Optional[str] = None
) -> Dict:
    """更新项目条目."""
    # 加载组配置
    group_configs = _storage.get_group_configs(project_id)
    all_groups_raw = group_configs.get("groups", {})
    all_groups = {
        name: UnifiedGroupConfig.from_dict(cfg) if isinstance(cfg, dict) else cfg
        for name, cfg in all_groups_raw.items()
    }
    default_rules = group_configs.get("group_settings", {}).get("default_related_rules", {})

    v = _project_service.validate_update_item(group, item_id, content, summary, related, all_groups, default_rules)
    if not v["success"]:
        return {"success": False, "error": v["error"]}

    related_dict = v.get("related_dict")

    result = _project_service.update_item(
        project_id=project_id,
        group=group,
        item_id=item_id,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related_dict,
        tags=_parse_tags(tags) if tags else None
    )

    if result["success"]:
        return {"success": True, "data": {"project_id": project_id, "group": group, "item_id": item_id, "item": result["item"]}}
    return result


def api_project_delete(project_id: str, group: str, item_id: str) -> Dict:
    """删除项目条目."""
    is_valid, error_msg = validate_group_name(group)
    if not is_valid:
        return {"success": False, "error": error_msg}

    if not item_id:
        return {"success": False, "error": "item_id 参数不能为空"}

    return _project_service.delete_item(project_id=project_id, group=group, item_id=item_id)


def api_manage_item_tags(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
) -> Dict:
    """管理条目标签."""
    is_valid, error_msg = validate_group_name(group_name)
    if not is_valid:
        return {"success": False, "error": error_msg}

    if operation == "set" or operation == "设置":
        if not tags:
            return {"success": False, "error": "operation='set' 时 tags 参数不能为空"}
        tag_list = [t.strip() for t in tags.split(",")]

        result = _project_service.update_item(project_id, group_name, item_id, tags=tag_list)
        return result

    elif operation == "add" or operation == "添加":
        if not tag:
            return {"success": False, "error": "operation='add' 时 tag 参数不能为空"}
        return _tag_service.add_item_tag(project_id, group_name, item_id, tag)

    elif operation == "remove" or operation == "移除":
        if not tag:
            return {"success": False, "error": "operation='remove' 时 tag 参数不能为空"}
        return _tag_service.remove_item_tag(project_id, group_name, item_id, tag)

    else:
        return {"success": False, "error": f"无效的操作类型: {operation} (支持: set/add/remove)"}


# ===================
# 标签管理 API 实现
# ===================

def api_tag_register(project_id: str, tag_name: str, summary: str, aliases: str = "") -> Dict:
    """注册项目标签."""
    alias_list = [a.strip() for a in aliases.split(",")] if aliases else []
    return _tag_service.register_tag(project_id=project_id, tag_name=tag_name, summary=summary, aliases=alias_list)


def api_tag_update(project_id: str, tag_name: str, summary: str) -> Dict:
    """更新标签."""
    return _tag_service.update_tag(project_id=project_id, tag_name=tag_name, summary=summary if summary else None)


def api_tag_delete(project_id: str, tag_name: str, force: str = "false") -> Dict:
    """删除标签."""
    force_flag = force.lower() == "true"
    return _tag_service.delete_tag(project_id=project_id, tag_name=tag_name, force=force_flag)


def api_tag_merge(project_id: str, old_tag: str, new_tag: str) -> Dict:
    """合并标签."""
    return _tag_service.merge_tags(project_id=project_id, old_tag=old_tag, new_tag=new_tag)


# ===================
# 统计 API 实现
# ===================

def api_project_stats() -> Dict:
    """获取全局统计信息."""
    # 计算项目级统计信息
    _storage.refresh_projects_cache()
    total_projects = len(_storage.list_all_projects())

    all_tags = []
    feature_stats = {"pending": 0, "in_progress": 0, "completed": 0}
    total_features = 0
    total_notes = 0
    feature_tag_counts = {}
    note_tag_counts = {}

    for project_id in _storage.list_all_projects().keys():
        project_data = _storage.get_project_data(project_id)
        if project_data is None:
            continue

        all_tags.extend(project_data["info"].get("tags", []))
        total_features += len(project_data.get("features", []))
        for feature in project_data.get("features", []):
            status = feature.get("status", "pending")
            if status in feature_stats:
                feature_stats[status] += 1
            for tag in feature.get("tags", []):
                feature_tag_counts[tag] = feature_tag_counts.get(tag, 0) + 1

        total_notes += len(project_data.get("notes", []))
        for note in project_data.get("notes", []):
            for tag in note.get("tags", []):
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

    return {"success": True, "data": stats}


def api_stats_summary(
    type: str = "",
    tool_name: str = "",
    project_id: str = "",
    date: str = ""
) -> Dict:
    """获取统计摘要."""
    if type == "tool" or type == "工具":
        if tool_name:
            result = _stats_service.get_tool_stats(tool_name)
            if not result["success"]:
                return result
            return {"success": True, "data": {
                "type": "tool",
                "tool_name": tool_name,
                "total": result['total'],
                "first_called": result.get('first_called'),
                "last_called": result.get('last_called'),
                "by_project": result.get("by_project", {}),
                "by_client": result.get("by_client", {}),
                "by_ip": result.get("by_ip", {})
            }}
        else:
            result = _stats_service.get_tool_stats()
            if not result["success"]:
                return result
            return {"success": True, "data": {"type": "tool", "tools": result["tools"]}}

    elif type == "project" or type == "项目":
        if not project_id:
            return {"success": False, "error": "project_id 参数不能为空"}
        result = _stats_service.get_project_stats(project_id)
        if not result["success"]:
            return result
        return {"success": True, "data": {
            "type": "project",
            "project_id": project_id,
            "total_calls": result['total_calls'],
            "tools_called": result["tools_called"]
        }}

    elif type == "client" or type == "客户端":
        result = _stats_service.get_client_stats()
        if not result["success"]:
            return result
        return {"success": True, "data": {"type": "client", "clients": result["clients"]}}

    elif type == "ip" or type == "IP":
        result = _stats_service.get_ip_stats()
        if not result["success"]:
            return result
        return {"success": True, "data": {"type": "ip", "ips": result["ips"]}}

    elif type == "daily" or type == "每日":
        if date:
            result = _stats_service.get_daily_stats(date)
            if not result["success"]:
                return result
            return {"success": True, "data": {
                "type": "daily",
                "date": date,
                "total_calls": result['total_calls'],
                "tools": result["tools"]
            }}
        else:
            result = _stats_service.get_daily_stats()
            if not result["success"]:
                return result
            return {"success": True, "data": {
                "type": "daily",
                "recent_days": result["recent_days"],
                "stats": result["stats"]
            }}

    elif type == "full" or type == "完整":
        result = _stats_service.get_full_summary()
        if not result["success"]:
            return result
        return {"success": True, "data": {
            "type": "full",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "ip_stats": result["ip_stats"],
            "daily_stats": result["daily_stats"]
        }}

    else:
        result = _stats_service.get_full_summary()
        if not result["success"]:
            return result
        return {"success": True, "data": {
            "type": "summary",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "daily_stats": result["daily_stats"]
        }}


def api_stats_cleanup(retention_days: int = 30) -> Dict:
    """清理过期统计数据."""
    return _stats_service.cleanup_stats(retention_days)


# ===================
# 分组管理 API 实现
# ===================

def api_create_custom_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = 240,
    summary_max_bytes: int = 90,
    allow_related: bool = False,
    allowed_related_to: str = "",
    enable_status: bool = True,
    enable_severity: bool = False
) -> Dict:
    """创建自定义组."""
    # 使用 _storage 直接操作
    group_configs = _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name in groups:
        return {"success": False, "error": f"自定义组 '{group_name}' 已存在"}

    # 构建组配置
    from business.core.groups import UnifiedGroupConfig, GroupType
    new_group = UnifiedGroupConfig(
        group_type=GroupType.CUSTOM,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=[g.strip() for g in allowed_related_to.split(",") if g.strip()] if allowed_related_to else [],
        enable_status=enable_status,
        enable_severity=enable_severity,
    )

    groups[group_name] = new_group.to_dict()
    group_configs["groups"] = groups

    if _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"自定义组 '{group_name}' 创建成功"}

    return {"success": False, "error": "保存配置失败"}


def api_update_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = None,
    summary_max_bytes: int = None,
    allow_related: bool = None,
    allowed_related_to: str = None,
    enable_status: bool = None,
    enable_severity: bool = None
) -> Dict:
    """更新组配置."""
    group_configs = _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name not in groups:
        return {"success": False, "error": f"组 '{group_name}' 不存在"}

    # 获取现有配置
    from business.core.groups import UnifiedGroupConfig
    existing = groups[group_name]
    if isinstance(existing, dict):
        config = UnifiedGroupConfig.from_dict(existing)
    else:
        config = existing

    # 更新字段
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

    if _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"组 '{group_name}' 更新成功"}

    return {"success": False, "error": "保存配置失败"}


def api_delete_custom_group(project_id: str, group_name: str) -> Dict:
    """删除自定义组."""
    group_configs = _storage.get_group_configs(project_id)
    groups = group_configs.get("groups", {})

    if group_name not in groups:
        return {"success": False, "error": f"自定义组 '{group_name}' 不存在"}

    # 检查是否是内置组
    from business.core.groups import all_group_names
    if group_name in all_group_names():
        return {"success": False, "error": "不能删除内置组"}

    del groups[group_name]
    group_configs["groups"] = groups

    if _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": f"自定义组 '{group_name}' 已删除"}

    return {"success": False, "error": "保存配置失败"}


def api_get_group_settings(project_id: str) -> Dict:
    """获取组设置."""
    group_configs = _storage.get_group_configs(project_id)
    settings = group_configs.get("group_settings", {})
    return {"success": True, "data": settings, "settings": settings}


def api_update_group_settings(project_id: str, default_related_rules: Dict = None) -> Dict:
    """更新组设置."""
    group_configs = _storage.get_group_configs(project_id)

    if default_related_rules is not None:
        if "group_settings" not in group_configs:
            group_configs["group_settings"] = {}
        group_configs["group_settings"]["default_related_rules"] = default_related_rules

    if _storage.save_group_configs(project_id, group_configs):
        return {"success": True, "message": "组设置更新成功"}

    return {"success": False, "error": "保存配置失败"}