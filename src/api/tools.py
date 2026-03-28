"""MCP 工具实现模块.

这些函数将在 server.py 中注册为 MCP 工具。
"""

import re
from datetime import datetime
from typing import Optional, Dict, List, Union

# 从 features.instances 导入全局实例
from features.instances import memory, call_stats
from core.groups import (
    validate_group_name,
    is_group_with_status,
)
from models.response import ApiResponse
from core.utils import paginate, resolve_default_size


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
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _tool_response(result, success_data=None, success_message=None):
    if result.get("success"):
        msg = success_message or result.get("message", "操作成功")
        return ApiResponse(success=True, data=success_data, message=msg).to_json()
    return ApiResponse(success=False, error=result.get("error", "未知错误")).to_json()


def _error_response(error):
    return ApiResponse(success=False, error=error).to_json()


# ===================
# Project Memory Tools
# ===================

def project_register(name: str, path: str = "", summary: str = "", tags: str = "") -> str:
    """注册一个新项目.
    Args:
        name: 项目名称
        path: 项目路径（可选）
        summary: 项目摘要（可选）
        tags: 项目标签，逗号分隔（可选）
    Returns:
        JSON 格式的注册结果
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = memory.register_project(name, path, summary, tag_list)
    if result["success"]:
        data = {k: v for k, v in result.items() if k not in ("success", "error", "message")}
        return _tool_response(result, data if data else None)
    return _tool_response(result)


def project_rename(project_id: str, new_name: str) -> str:
    """重命名项目（修改 name 字段并重命名目录）.

    Args:
        project_id: 项目 UUID
        new_name: 新的项目名称

    Returns:
        JSON 格式的操作结果
    """
    result = memory.project_rename(project_id, new_name)
    data = {"old_name": result.get("old_name"), "new_name": result.get("new_name")} if result.get("success") else None
    return _tool_response(result, data)


def project_list(
    view_mode: str = "summary",
    page: int = 1,
    size: int = 0,
    name_pattern: str = "",
    include_archived: bool = False
) -> str:
    """列出所有项目.

    Args:
        view_mode: 视图模式 (可选): "summary"(精简，默认) 或 "detail"(完整)
            - summary: 只返回 id, name, summary, tags，size 默认 20
            - detail: 返回所有字段（含 created_at），size 默认 0（全部）
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 根据 view_mode 决定默认值
        name_pattern: 项目名称正则过滤 (可选): 正则表达式匹配项目名称，默认不过滤
        include_archived: 是否包含归档项目 (可选): 默认 false，传入 true 时显示归档项目

    Returns:
        JSON 格式的项目列表

    使用示例:
        # 列出所有项目（精简模式，默认前20条）
        project_list()

        # 列出所有项目（完整模式）
        project_list(view_mode="detail")

        # 包含归档项目
        project_list(include_archived=true)

        # 按名称过滤（支持正则）
        project_list(name_pattern="test")

        # 分页查询
        project_list(page=2, size=5)

        # 组合使用
        project_list(view_mode="detail", name_pattern="^api", page=1, size=10)
    """
    # 验证 view_mode 参数
    if view_mode not in ("summary", "detail"):
        return _error_response(f"无效的 view_mode: {view_mode} (支持: summary/detail)")

    # 验证 name_pattern 正则有效性
    name_regex = None
    if name_pattern:
        try:
            name_regex = re.compile(name_pattern)
        except re.error as e:
            return _error_response(f"无效的正则表达式: {name_pattern} ({e})")

    # 根据 view_mode 设置 size 默认值
    size = resolve_default_size(size, view_mode)

    result = memory.list_projects(include_archived=include_archived)

    if not result["success"]:
        return _tool_response(result)

    projects = result["projects"]
    total = result["total"]

    # name_pattern 过滤
    if name_regex:
        projects = [p for p in projects if name_regex.search(p.get("name", ""))]

    # 分页处理
    pr, err = paginate(projects, page, size)
    if err:
        return _error_response(err)
    assert pr is not None
    projects, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

    # view_mode 字段过滤
    if view_mode == "summary":
        filtered_projects = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "summary": p.get("summary"),
                "tags": p.get("tags", []),
                "status": p.get("status", "active")
            }
            for p in projects
        ]
    else:
        filtered_projects = projects

    response_data = {
        "total": total,
        "filtered_total": filtered_total,
        "projects": filtered_projects
    }

    if pagination_meta:
        response_data.update(pagination_meta)

    if name_pattern:
        response_data["filters"] = {"name_pattern": name_pattern}

    return _tool_response({"success": True}, response_data, f"共 {filtered_total} 个项目")


def project_groups_list(project_id: str) -> str:
    """列出项目的所有分组（功能、笔记、规范）.

    Args:
        project_id: 项目ID

    Returns:
        JSON 格式的分组列表及统计信息
    """
    result = memory.list_groups(project_id)

    if not result["success"]:
        return _tool_response(result)

    data = {
        "project_id": project_id,
        "groups": result["groups"]
    }
    return _tool_response(result, data, "获取分组成功")


def project_tags_info(
    project_id: str,
    group_name: str = "",
    tag_name: str = "",
    unregistered_only: bool = False
) -> str:
    """查询标签信息（统一接口）.

    Args:
        project_id: 项目ID
        group_name: 分组名称 ("features"|"notes"|"fixes"|"standards")，为空则返回所有已注册标签
        tag_name: 标签名称 (为空则返回所有标签)
        unregistered_only: 仅返回未注册标签

    Returns:
        JSON 格式的标签信息
    """
    # 不指定 group_name 时，列出所有已注册标签
    if not group_name:
        result = memory.list_all_registered_tags(project_id)
        data = {"project_id": project_id, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])} if result.get("success") else None
        return _tool_response(result, data, f"共 {result.get('total_tags', 0)} 个已注册标签")

    is_valid, error_msg = validate_group_name(group_name)
    if not is_valid:
        return _error_response(error_msg)

    # 查询特定标签
    if tag_name:
        result = memory.query_by_tag(project_id, group_name, tag_name)
        data = {"project_id": project_id, "group_name": group_name, "tag_name": tag_name, "total": result.get("total", 0), "items": result.get("items", [])} if result.get("success") else None
        return _tool_response(result, data, f"共 {result.get('total', 0)} 个条目")

    # 仅返回未注册标签
    elif unregistered_only:
        result = memory.list_unregistered_tags(project_id, group_name)
        data = {"project_id": project_id, "group_name": group_name, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])} if result.get("success") else None
        return _tool_response(result, data, f"共 {result.get('total_tags', 0)} 个未注册标签")

    # 返回所有标签
    else:
        result = memory.list_group_tags(project_id, group_name)
        data = {"project_id": project_id, "group_name": group_name, "total_tags": result.get("total_tags", 0), "tags": result.get("tags", [])} if result.get("success") else None
        return _tool_response(result, data, f"共 {result.get('total_tags', 0)} 个标签")


def project_add(
    project_id: str,
    group: str,
    content: str = "",
    summary: str = "",
    status: Optional[str] = None,  # 哨兵值，用于检测是否显式传入
    severity: str = "medium",
    related: Union[str, Dict[str, List[str]], None] = "",
    tags: str = ""
) -> str:
    """添加项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"（支持中文："功能"/"修复"/"笔记"/"规范"）
        content: 补充描述
            - features: 功能详细内容
            - fixes: 修复详细内容
            - notes: 笔记详细内容
            - standards: 规范详细内容
        summary: 摘要（所有分组必填，标准摘要描述）
        status: 状态（仅 features/fixes 使用，必填，有效值: pending/in_progress/completed）
        severity: 严重程度（仅 fixes 使用，默认 "medium"）
        related: 关联条目，支持JSON字符串或字典格式，如 '{"features": ["feat_001"], "notes": ["note_001"]}' 或 {"features": ["feat_001"]}（仅 features/fixes 使用）
        tags: 标签列表，逗号分隔

    Returns:
        JSON 格式的操作结果
    """
    tag_list = _parse_tags(tags)

    v = memory.validate_add_item(group, content, summary, status, related, tag_list)
    if not v["success"]:
        return _error_response(v["error"])

    related_dict = v["related_dict"]

    # 统一调用 add_item
    result = memory.add_item(
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
        # 可选字段
        if status:
            data["item"]["status"] = status
        if severity and severity != "medium":
            data["item"]["severity"] = severity
        if related_dict:
            data["item"]["related"] = related_dict
        return _tool_response(result, data)
    return _tool_response(result)


def project_update(
    project_id: str,
    group: str,
    item_id: str,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    related: Optional[Union[str, Dict[str, List[str]]]] = None,
    tags: Optional[str] = None
) -> str:
    """更新项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"
        item_id: 条目ID
        content: 内容更新（可选）
        summary: 摘要更新（可选）
        status: 状态更新（可选）
        severity: 严重程度更新（仅 fixes）
        related: 关联条目更新,支持JSON字符串或字典格式,如 '{"features": ["feat_001"]}' 或 {"features": ["feat_001"]}（仅 features/fixes）
        tags: 标签更新（可选）

    Returns:
        JSON 格式的操作结果
    """
    v = memory.validate_update_item(group, item_id, content, summary, related)
    if not v["success"]:
        return _error_response(v["error"])

    related_dict = v["related_dict"]

    # 统一调用 update_item
    result = memory.update_item(
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
        data = {
            "project_id": project_id,
            "group": group,
            "item_id": item_id,
            "item": result["item"]
        }
        return _tool_response(result, data)
    return _tool_response(result)


def project_delete(
    project_id: str,
    group: str,
    item_id: str
) -> str:
    """删除项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"
        item_id: 条目ID

    Returns:
        JSON 格式的操作结果
    """
    # 验证 group 有效性
    is_valid, error_msg = validate_group_name(group)
    if not is_valid:
        return _error_response(error_msg)

    # 验证必需参数
    if not item_id:
        return _error_response("item_id 参数不能为空")

    # 统一调用 delete_item
    result = memory.delete_item(project_id=project_id, group=group, item_id=item_id)
    data = {"project_id": project_id, "group": group, "item_id": item_id, "deleted": True} if result.get("success") else None
    return _tool_response(result, data)


def project_remove(
    project_id: str,
    mode: str = "archive"
) -> str:
    """归档或永久删除项目（统一接口）.

    Args:
        project_id: 项目ID
        mode: 操作模式 - "archive"(归档，默认) 或 "delete"(永久删除)

    Returns:
        JSON 格式的操作结果

    使用示例:
        # 归档项目（默认）
        project_remove(project_id="xxx")

        # 永久删除项目
        project_remove(project_id="xxx", mode="delete")
    """
    result = memory.remove_project(project_id=project_id, mode=mode)
    if result.get("success"):
        data = {"project_id": project_id, "mode": mode}
        return _tool_response(result, data, result.get("message", "操作成功"))
    return _tool_response(result)


def project_item_tag_manage(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
) -> str:
    """管理条目标签（统一接口）.

    Args:
        project_id: 项目ID
        group_name: 分组名称 ("features"|"notes"|"fixes"|"standards")
        item_id: 条目ID
        operation: 操作类型 - "set"|"add"|"remove"
        tag: 单个标签 (operation="add"|"remove"时)
        tags: 标签列表逗号分隔 (operation="set"时)

    Returns:
        JSON 格式的操作结果
    """
    is_valid, error_msg = validate_group_name(group_name)
    if not is_valid:
        return _error_response(error_msg)

    if operation == "set" or operation == "设置":
        if not tags:
            return _error_response("operation='set' 时 tags 参数不能为空")
        tag_list = [t.strip() for t in tags.split(",")]

        result = memory.update_item(project_id, group_name, item_id, tags=tag_list)
        data = {"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "set", "tags": result.get('tags', tag_list)} if result.get("success") else None
        return _tool_response(result, data)

    elif operation == "add" or operation == "添加":
        if not tag:
            return _error_response("operation='add' 时 tag 参数不能为空")
        result = memory.add_item_tag(project_id, group_name, item_id, tag)
        data = {"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "add", "tag": tag, "tags": result.get("tags", [])} if result.get("success") else None
        return _tool_response(result, data)

    elif operation == "remove" or operation == "移除":
        if not tag:
            return _error_response("operation='remove' 时 tag 参数不能为空")
        result = memory.remove_item_tag(project_id, group_name, item_id, tag)
        data = {"project_id": project_id, "group_name": group_name, "item_id": item_id, "operation": "remove", "tag": tag, "tags": result.get("tags", [])} if result.get("success") else None
        return _tool_response(result, data)

    else:
        return _error_response(f"无效的操作类型: {operation} (支持: set/add/remove)")


def tag_register(
    project_id: str,
    tag_name: str,
    summary: str,
    aliases: str = ""
) -> str:
    """注册项目标签.

    标签必须先注册才能使用。注册时需要提供语义描述（建议10-50字）。

    Args:
        project_id: 项目ID
        tag_name: 标签名称（英文，无空格）
        summary: 标签语义摘要（10-50字）
        aliases: 别名列表，逗号分隔（可选）

    Returns:
        JSON 格式的注册结果
    """
    alias_list = [a.strip() for a in aliases.split(",")] if aliases else []

    result = memory.register_tag(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary,
        aliases=alias_list
    )

    data = {"project_id": project_id, "tag_name": tag_name, "tag_info": result.get("tag_info", {})} if result.get("success") else None
    return _tool_response(result, data)


def tag_update(
    project_id: str,
    tag_name: str,
    summary: Optional[str] = ""
) -> str:
    """更新已注册标签的语义信息.

    Args:
        project_id: 项目ID
        tag_name: 标签名称
        summary: 新的摘要（可选）

    Returns:
        JSON 格式的更新结果
    """
    summary_param = summary if summary else None

    result = memory.update_tag(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary_param
    )

    data = {"project_id": project_id, "tag_name": tag_name, "updated": True} if result.get("success") else None
    return _tool_response(result, data)


def tag_delete(
    project_id: str,
    tag_name: str,
    force: str = "false"
) -> str:
    """删除标签注册.

    Args:
        project_id: 项目ID
        tag_name: 标签名称
        force: 是否强制删除（"true"/"false"，即使标签正在使用）

    Returns:
        JSON 格式的删除结果
    """
    force_flag = force.lower() == "true"

    result = memory.delete_tag(
        project_id=project_id,
        tag_name=tag_name,
        force=force_flag
    )

    data = {"project_id": project_id, "tag_name": tag_name, "force": force_flag, "deleted": True} if result.get("success") else None
    return _tool_response(result, data)


def tag_merge(
    project_id: str,
    old_tag: str,
    new_tag: str
) -> str:
    """合并标签：将所有 old_tag 的引用迁移到 new_tag.

    Args:
        project_id: 项目ID
        old_tag: 旧标签名称（将被删除）
        new_tag: 新标签名称（合并目标）

    Returns:
        JSON 格式的合并结果
    """
    result = memory.merge_tags(
        project_id=project_id,
        old_tag=old_tag,
        new_tag=new_tag
    )

    data = {"project_id": project_id, "old_tag": old_tag, "new_tag": new_tag, "merged": True} if result.get("success") else None
    return _tool_response(result, data)


def project_get(
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
) -> str:
    """获取项目信息或查询条目列表/详情.

    查询模式:
        1. 整个项目信息 - 不传 group_name
        2. 分组列表模式 - 传 group_name，不传 item_id (根据 view_mode 决定返回字段)
        3. 条目详情模式 - 传 group_name + item_id (含完整 content)

    Args:
        project_id: 项目ID
        group_name: 分组名称 (可选): "features"|"notes"|"fixes"|"standards"
        item_id: 条目ID (可选): 查询单个条目时指定
        status: 状态过滤 (可选): 对 group_name="features" 或 "fixes" 有效，过滤状态 (pending/in_progress/completed)
        severity: 严重程度过滤 (可选): 仅对 group_name="fixes" 有效，过滤严重程度 (critical/high/medium/low)
        tags: 标签过滤 (可选): 逗号分隔的标签字符串，OR 逻辑匹配（至少包含一个标签即可），如 "api,enhancement"
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 根据 view_mode 决定默认值
        view_mode: 视图模式 (可选): "summary"(精简，默认) 或 "detail"(完整)
            - summary: 只返回 id, summary, tags，size 默认 20
            - detail: 返回所有字段（不含 content），size 默认 0（全部）
        summary_pattern: 摘要正则过滤 (可选): 正则表达式匹配摘要，默认不过滤
        created_after: 创建时间起始 (可选): YYYY-MM-DD，包含边界，默认不过滤
        created_before: 创建时间截止 (可选): YYYY-MM-DD，包含边界，默认不过滤
        updated_after: 修改时间起始 (可选): YYYY-MM-DD，包含边界，默认不过滤
        updated_before: 修改时间截止 (可选): YYYY-MM-DD，包含边界，默认不过滤

    Returns:
        JSON 格式的项目信息、条目列表或单个条目详情

    使用示例:
        # 获取整个项目信息
        project_get(project_id="my_project")

        # 查询功能列表（精简模式，默认前20条）
        project_get(project_id="my_project", group_name="features")

        # 查询功能列表（完整模式）
        project_get(project_id="my_project", group_name="features", view_mode="detail")

        # 查询功能列表（带状态过滤）
        project_get(project_id="my_project", group_name="features", status="pending")

        # 查询修复列表（带过滤）
        project_get(project_id="my_project", group_name="fixes", status="pending", severity="high")

        # 查询功能列表（带标签过滤，OR 逻辑）
        project_get(project_id="my_project", group_name="features", tags="api,enhancement")

        # 查询功能列表（组合过滤）
        project_get(project_id="my_project", group_name="features", status="pending", tags="api")

        # 查询功能列表（分页）
        project_get(project_id="my_project", group_name="features", page=1, size=10)

        # 查询功能列表（过滤 + 分页）
        project_get(project_id="my_project", group_name="features", status="pending", page=1, size=10)

        # 查询功能列表（带摘要正则过滤）
        project_get(project_id="my_project", group_name="features", summary_pattern="API")

        # 查询功能列表（带时间范围过滤）
        project_get(project_id="my_project", group_name="features", created_after="2026-03-01", created_before="2026-03-31")

        # 查询单个条目详情
        project_get(project_id="my_project", group_name="features", item_id="feat_20260318_001")
    """
    # 验证 view_mode 参数
    if view_mode not in ("summary", "detail"):
        return _error_response(f"无效的 view_mode: {view_mode} (支持: summary/detail)")

    # 验证 summary_pattern 正则有效性
    summary_regex = None
    if summary_pattern:
        try:
            summary_regex = re.compile(summary_pattern)
        except re.error as e:
            return _error_response(f"无效的summary正则表达式: {summary_pattern} ({e})")

    # 验证时间范围参数格式 (YYYY-MM-DD)
    for _, param_val in [
        ("created_after", created_after),
        ("created_before", created_before),
        ("updated_after", updated_after),
        ("updated_before", updated_before),
    ]:
        if param_val and not _validate_date(param_val):
            return _error_response(f"无效的日期格式: {param_val} (要求 YYYY-MM-DD)")

    # 根据 view_mode 设置 size 默认值
    size = resolve_default_size(size, view_mode)

    result = memory.get_project(project_id)

    if not result["success"]:
        return _tool_response(result)

    data = result["data"]

    # 如果指定了 group_name
    if group_name:
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            return _error_response(error_msg)

        items = data.get(group_name, [])

        # 如果指定了 item_id，返回单个条目详情
        if item_id:
            item = None
            for it in items:
                if it.get("id") == item_id:
                    item = it.copy()  # 复制以避免修改原始数据
                    break

            if not item:
                return _error_response(f"在分组 '{group_name}' 中找不到条目 '{item_id}'")

            # 对于 notes 分组，从 .md 文件加载 content
            if group_name == "notes":
                note_content = memory._load_note_content(project_id, item_id)
                if note_content is not None:
                    item["content"] = note_content

            response_data = {
                "project_id": project_id,
                "group_name": group_name,
                "item_id": item_id,
                "item": item
            }
            return _tool_response({"success": True}, response_data, "获取条目详情成功")

        # 如果只指定了 group_name 但没有 item_id，返回该分组列表
        # 列表模式不返回 content 字段以减少数据量，使用 item_id 查询详情可获取完整 content
        filtered_items = items

        # 解析 tags 参数
        tag_list = _parse_tags(tags) if tags else []

        # 应用过滤条件
        if is_group_with_status(group_name):
            if status:
                filtered_items = [f for f in filtered_items if f.get("status") == status]
            if severity:
                filtered_items = [f for f in filtered_items if f.get("severity") == severity]

        # tags 过滤：OR 逻辑，适用于所有分组
        if tag_list:
            filtered_items = [f for f in filtered_items if any(tag in f.get("tags", []) for tag in tag_list)]

        # summary 正则过滤 + 时间范围过滤（单次遍历优化）
        if summary_regex or created_after or created_before or updated_after or updated_before:
            new_filtered = []
            for item in filtered_items:
                # summary 正则
                if summary_regex and not summary_regex.search(item.get("summary", "")):
                    continue
                # 创建时间范围
                created = (item.get("created_at") or "")[:10]
                if created_after and created < created_after:
                    continue
                if created_before and created > created_before:
                    continue
                # 修改时间范围
                updated = (item.get("updated_at") or "")[:10]
                if updated_after and (not updated or updated < updated_after):
                    continue
                if updated_before and (not updated or updated > updated_before):
                    continue
                new_filtered.append(item)
            filtered_items = new_filtered

        # 分页处理：先过滤，后分页
        pr, err = paginate(filtered_items, page, size)
        if err:
            return _error_response(err)
        assert pr is not None
        paginated_items, pagination_meta, filtered_total = pr.items, pr.pagination_meta, pr.filtered_total

        # 列表模式根据 view_mode 决定返回字段
        if view_mode == "summary":
            # 精简模式：只返回 id, summary, tags
            filtered_items_for_response = [
                {
                    "id": item.get("id"),
                    "summary": item.get("summary"),
                    "tags": item.get("tags", [])
                }
                for item in paginated_items
            ]
        else:
            # 完整模式：返回所有字段（除 content）
            filtered_items_for_response = [{k: v for k, v in item.items() if k != 'content'} for item in paginated_items]

        response_data = {
            "project_id": project_id,
            "project_name": data['info']['name'],
            "group_name": group_name,
            "total": len(items),
            "filtered_total": filtered_total,
            "items": filtered_items_for_response
        }

        # 添加分页元信息（仅在启用分页时）
        if pagination_meta:
            response_data.update(pagination_meta)

        # 添加过滤器信息（如果有过滤条件）
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

        return _tool_response({"success": True}, response_data, f"共 {filtered_total} 个条目")

    # 默认行为：返回精简的项目概览（仅统计信息，不返回各分组摘要列表）
    response_data = {
        "project_id": project_id,
        "info": data['info'],
        "groups": {
            "features": {"count": len(data["features"])},
            "notes": {"count": len(data["notes"])},
            "fixes": {"count": len(data.get("fixes", []))},
            "standards": {"count": len(data.get("standards", []))}
        }
    }
    return _tool_response({"success": True}, response_data, "获取项目信息成功")


def project_stats() -> str:
    """获取全局统计信息.

    Returns:
        JSON 格式的统计数据
    """
    result = memory.get_stats()

    if not result["success"]:
        return _tool_response(result)

    stats = result["stats"]
    data = {
        "total_projects": stats['total_projects'],
        "total_features": stats['total_features'],
        "total_notes": stats['total_notes'],
        "feature_status": stats["feature_status"],
        "top_project_tags": stats["top_project_tags"],
        "top_feature_tags": stats["top_feature_tags"],
        "top_note_tags": stats["top_note_tags"]
    }
    return _tool_response(result, data, "获取统计成功")



def stats_summary(
    type: str = "",
    tool_name: str = "",
    project_id: str = "",
    date: str = ""
) -> str:
    """获取统计摘要（统一接口）.

    Args:
        type: 统计类型 - "tool"|"project"|"client"|"ip"|"daily"|"full"|""(所有)
        tool_name: 工具名称 (type="tool"时)
        project_id: 项目ID (type="project"时)
        date: 日期 YYYY-MM-DD (type="daily"时)

    Returns:
        JSON 格式的统计摘要
    """
    if type == "tool" or type == "工具":
        if tool_name:
            result = call_stats.get_tool_stats(tool_name)
            if not result["success"]:
                return _tool_response(result)

            data = {
                "type": "tool",
                "tool_name": tool_name,
                "total": result['total'],
                "first_called": result.get('first_called'),
                "last_called": result.get('last_called'),
                "by_project": result.get("by_project", {}),
                "by_client": result.get("by_client", {}),
                "by_ip": result.get("by_ip", {})
            }
            return _tool_response(result, data, f"工具 '{tool_name}' 调用统计")
        else:
            result = call_stats.get_tool_stats()
            if not result["success"]:
                return _tool_response(result)

            data = {
                "type": "tool",
                "tools": result["tools"]
            }
            return _tool_response(result, data, "所有工具调用统计")

    elif type == "project" or type == "项目":
        if not project_id:
            return _error_response("project_id 参数不能为空")
        result = call_stats.get_project_stats(project_id)

        if not result["success"]:
            return _tool_response(result)

        data = {
            "type": "project",
            "project_id": project_id,
            "total_calls": result['total_calls'],
            "tools_called": result["tools_called"]
        }
        return _tool_response(result, data, f"项目 '{project_id}' 调用统计")

    elif type == "client" or type == "客户端":
        result = call_stats.get_client_stats()

        if not result["success"]:
            return _tool_response(result, None, "获取客户端统计失败")

        data = {
            "type": "client",
            "clients": result["clients"]
        }
        return _tool_response(result, data, "客户端调用统计")

    elif type == "ip" or type == "IP":
        result = call_stats.get_ip_stats()

        if not result["success"]:
            return _tool_response(result, None, "获取IP统计失败")

        data = {
            "type": "ip",
            "ips": result["ips"]
        }
        return _tool_response(result, data, "IP地址调用统计")

    elif type == "daily" or type == "每日":
        if date:
            result = call_stats.get_daily_stats(date)
            if not result["success"]:
                return _tool_response(result)

            data = {
                "type": "daily",
                "date": date,
                "total_calls": result['total_calls'],
                "tools": result["tools"]
            }
            return _tool_response(result, data, f"日期 '{date}' 统计")
        else:
            result = call_stats.get_daily_stats()
            if not result["success"]:
                return _tool_response(result, None, "获取每日统计失败")

            data = {
                "type": "daily",
                "recent_days": result["recent_days"],
                "stats": result["stats"]
            }
            return _tool_response(result, data, "最近7天统计")

    elif type == "full" or type == "完整":
        result = call_stats.get_full_summary()

        if not result["success"]:
            return _tool_response(result, None, "获取完整统计失败")

        data = {
            "type": "full",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "ip_stats": result["ip_stats"],
            "daily_stats": result["daily_stats"]
        }
        return _tool_response(result, data, "完整统计")

    else:
        # 默认返回所有统计摘要
        result = call_stats.get_full_summary()
        if not result["success"]:
            return _tool_response(result, None, "获取完整统计失败")

        data = {
            "type": "summary",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "daily_stats": result["daily_stats"]
        }
        return _tool_response(result, data, "统计摘要")


def stats_cleanup(retention_days: int = 30) -> str:
    """手动清理过期统计数据.

    清理超过指定天数的统计数据，包括每日统计、工具调用统计、项目统计等。
    这可以帮助减少存储空间使用和提升性能。

    Args:
        retention_days: 保留天数（默认30天），超过此天数的数据将被清理

    Returns:
        JSON 格式的清理结果摘要
    """
    result = call_stats.cleanup_stats(retention_days)

    if not result["success"]:
        return _tool_response(result)

    cleanup_result = result["cleanup_result"]
    before = result["before"]
    after = result["after"]

    data = {
        "retention_days": retention_days,
        "cutoff_date": cleanup_result['cutoff_date'],
        "cleanup_details": {
            "daily_stats_removed": cleanup_result['daily_stats_removed'],
            "tools_removed": cleanup_result['tools_removed'],
            "projects_cleaned": cleanup_result['projects_cleaned'],
            "clients_cleaned": cleanup_result['clients_cleaned'],
            "ips_cleaned": cleanup_result['ips_cleaned']
        },
        "storage_before": before,
        "storage_after": after
    }
    return _tool_response(result, data, "统计数据清理完成")



