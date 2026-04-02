"""Business 服务客户端 - REST API 层调用 business 层的接口.

此模块提供 REST API 层通过 HTTP 调用 business_api 服务的接口。
"""

from typing import Optional, Dict, List, Union

# 导入 HTTP 客户端
from clients.business_client import get_business_client, BusinessApiClient
from common.response import ApiResponse

# 获取全局 HTTP 客户端
_business_client: Optional[BusinessApiClient] = None


def _get_client() -> BusinessApiClient:
    """获取或创建 business API 客户端."""
    global _business_client
    if _business_client is None:
        _business_client = get_business_client()
    return _business_client


# ===================
# 项目管理 API 实现
# ===================

def api_project_list(
    view_mode: str = "summary",
    page: int = 1,
    size: int = 0,
    name_pattern: str = "",
    include_archived: bool = False
) -> ApiResponse:
    """列出所有项目."""
    client = _get_client()
    return client.project_list(
        view_mode=view_mode,
        page=page,
        size=size,
        name_pattern=name_pattern,
        include_archived=include_archived
    )


def api_register_project(name: str, path: str = "", summary: str = "", tags: str = "") -> ApiResponse:
    """注册新项目."""
    client = _get_client()
    return client.register_project(name=name, path=path, summary=summary, tags=tags)


def api_get_project(project_id: str) -> ApiResponse:
    """获取项目详情."""
    client = _get_client()
    return client.get_project(project_id)


def api_rename_project(project_id: str, new_name: str) -> ApiResponse:
    """重命名项目."""
    client = _get_client()
    return client.rename_project(project_id, new_name)


def api_remove_project(project_id: str, mode: str = "archive") -> ApiResponse:
    """删除或归档项目."""
    client = _get_client()
    return client.remove_project(project_id=project_id, mode=mode)


def api_list_groups(project_id: str) -> ApiResponse:
    """列出项目的所有分组."""
    client = _get_client()
    return client.list_groups(project_id)


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
) -> ApiResponse:
    """查询标签信息."""
    client = _get_client()
    return client.project_tags_info(
        project_id=project_id,
        group_name=group_name,
        tag_name=tag_name,
        unregistered_only=unregistered_only,
        page=page,
        size=size,
        view_mode=view_mode,
        summary_pattern=summary_pattern,
        tag_name_pattern=tag_name_pattern
    )


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
) -> ApiResponse:
    """获取项目信息或查询条目列表/详情."""
    client = _get_client()
    return client.project_get(
        project_id=project_id,
        group_name=group_name,
        item_id=item_id,
        status=status,
        severity=severity,
        tags=tags,
        page=page,
        size=size,
        view_mode=view_mode,
        summary_pattern=summary_pattern,
        created_after=created_after,
        created_before=created_before,
        updated_after=updated_after,
        updated_before=updated_before
    )


def api_project_add(
    project_id: str,
    group: str,
    content: str = "",
    summary: str = "",
    status: Optional[str] = None,
    severity: str = "medium",
    related: Union[str, Dict[str, List[str]], None] = "",
    tags: str = ""
) -> ApiResponse:
    """添加项目条目."""
    client = _get_client()
    return client.project_add(
        project_id=project_id,
        group=group,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related,
        tags=tags
    )


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
) -> ApiResponse:
    """更新项目条目."""
    client = _get_client()
    return client.project_update(
        project_id=project_id,
        group=group,
        item_id=item_id,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related,
        tags=tags
    )


def api_project_delete(project_id: str, group: str, item_id: str) -> ApiResponse:
    """删除项目条目."""
    client = _get_client()
    return client.project_delete(project_id=project_id, group=group, item_id=item_id)


def api_manage_item_tags(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
) -> ApiResponse:
    """管理条目标签."""
    client = _get_client()
    return client.manage_item_tags(
        project_id=project_id,
        group_name=group_name,
        item_id=item_id,
        operation=operation,
        tag=tag,
        tags=tags
    )


# ===================
# 标签管理 API 实现
# ===================

def api_tag_register(project_id: str, tag_name: str, summary: str, aliases: str = "") -> ApiResponse:
    """注册项目标签."""
    client = _get_client()
    return client.tag_register(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary,
        aliases=aliases
    )


def api_tag_update(project_id: str, tag_name: str, summary: str) -> ApiResponse:
    """更新标签."""
    client = _get_client()
    return client.tag_update(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary
    )


def api_tag_delete(project_id: str, tag_name: str, force: str = "false") -> ApiResponse:
    """删除标签."""
    client = _get_client()
    return client.tag_delete(
        project_id=project_id,
        tag_name=tag_name,
        force=force
    )


def api_tag_merge(project_id: str, old_tag: str, new_tag: str) -> ApiResponse:
    """合并标签."""
    client = _get_client()
    return client.tag_merge(
        project_id=project_id,
        old_tag=old_tag,
        new_tag=new_tag
    )


# ===================
# 统计 API 实现
# ===================

def api_project_stats() -> ApiResponse:
    """获取全局统计信息."""
    client = _get_client()
    return client.project_stats()


def api_stats_summary(
    type: str = "",
    tool_name: str = "",
    project_id: str = "",
    date: str = ""
) -> ApiResponse:
    """获取统计摘要."""
    client = _get_client()
    return client.stats_summary(
        type=type,
        tool_name=tool_name,
        project_id=project_id,
        date=date
    )


def api_stats_cleanup(retention_days: int = 30) -> ApiResponse:
    """清理过期统计数据."""
    client = _get_client()
    return client.stats_cleanup(retention_days=retention_days)


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
) -> ApiResponse:
    """创建自定义组."""
    client = _get_client()
    return client.create_custom_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity
    )


def api_update_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = None,
    summary_max_bytes: int = None,
    allow_related: bool = None,
    allowed_related_to: str = None,
    enable_status: bool = None,
    enable_severity: bool = None
) -> ApiResponse:
    """更新组配置."""
    client = _get_client()
    return client.update_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity
    )


def api_delete_custom_group(project_id: str, group_name: str) -> ApiResponse:
    """删除自定义组."""
    client = _get_client()
    return client.delete_custom_group(project_id=project_id, group_name=group_name)


def api_get_group_settings(project_id: str) -> ApiResponse:
    """获取组设置."""
    client = _get_client()
    return client.get_group_settings(project_id)


def api_update_group_settings(project_id: str, default_related_rules: Dict = None) -> ApiResponse:
    """更新组设置."""
    client = _get_client()
    return client.update_group_settings(
        project_id=project_id,
        default_related_rules=default_related_rules
    )
