"""MCP 项目管理工具模块.

提供项目管理相关的 MCP 工具函数。只做转发，不处理任何业务逻辑。
"""

from typing import Optional, Union, Dict, List

from ._shared import _get_client, _tool_response


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
    client = _get_client()
    result = client.register_project(name=name, path=path, summary=summary, tags=tags)
    return _tool_response(result)


def project_rename(project_id: str, new_name: str) -> str:
    """重命名项目（修改 name 字段并重命名目录）.

    Args:
        project_id: 项目 UUID
        new_name: 新的项目名称

    Returns:
        JSON 格式的操作结果
    """
    client = _get_client()
    result = client.rename_project(project_id, new_name)
    return _tool_response(result)


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
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 根据 view_mode 决定默认值
        name_pattern: 项目名称正则过滤 (可选): 正则表达式匹配项目名称，默认不过滤
        include_archived: 是否包含归档项目 (可选): 默认 false，传入 true 时显示归档项目

    Returns:
        JSON 格式的项目列表
    """
    client = _get_client()
    result = client.project_list(
        view_mode=view_mode,
        page=page,
        size=size,
        name_pattern=name_pattern,
        include_archived=include_archived
    )
    return _tool_response(result)


def project_groups_list(project_id: str) -> str:
    """列出项目的所有分组（内置组 + 自定义组）.

    Args:
        project_id: 项目ID

    Returns:
        JSON 格式的分组列表及统计信息
    """
    client = _get_client()
    result = client.list_groups(project_id)
    return _tool_response(result)


def project_tags_info(
    project_id: str,
    group_name: str = "",
    tag_name: str = "",
    unregistered_only: bool = False,
    page: int = 1,
    size: int = 0,
    view_mode: str = "summary",
    summary_pattern: str = "",
    tag_name_pattern: str = ""
) -> str:
    """查询标签信息（统一接口）.

    Args:
        project_id: 项目ID
        group_name: 分组名称 (可选)
        tag_name: 标签名称 (为空则返回所有标签)
        unregistered_only: 仅返回未注册标签
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 根据 view_mode 决定默认值
        view_mode: 视图模式 (可选): "summary"(精简，默认) 或 "detail"(完整)
        summary_pattern: 摘要正则过滤 (可选)
        tag_name_pattern: 标签名正则过滤 (可选)

    Returns:
        JSON 格式的标签信息
    """
    client = _get_client()
    result = client.project_tags_info(
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
    return _tool_response(result)


def project_add(
    project_id: str,
    group: str,
    content: str = "",
    summary: str = "",
    status: Optional[str] = None,
    severity: str = "medium",
    related: str = "",
    tags: str = ""
) -> str:
    """添加项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型
        content: 补充描述
        summary: 摘要（所有分组必填）
        status: 状态（仅 features/fixes 使用）
        severity: 严重程度（仅 fixes 使用，默认 "medium"）
        related: 关联条目
        tags: 标签列表，逗号分隔

    Returns:
        JSON 格式的操作结果
    """
    client = _get_client()
    result = client.project_add(
        project_id=project_id,
        group=group,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related,
        tags=tags
    )
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
        group: 分组类型
        item_id: 条目ID
        content: 内容更新（可选）
        summary: 摘要更新（可选）
        status: 状态更新（可选）
        severity: 严重程度更新（仅 fixes）
        related: 关联条目更新（可选）
        tags: 标签更新（可选）

    Returns:
        JSON 格式的操作结果
    """
    import json
    # 如果 related 是字典，转换为 JSON 字符串
    related_str = json.dumps(related) if isinstance(related, dict) else related

    client = _get_client()
    result = client.project_update(
        project_id=project_id,
        group=group,
        item_id=item_id,
        content=content,
        summary=summary,
        status=status,
        severity=severity,
        related=related_str,
        tags=tags
    )
    return _tool_response(result)


def project_delete(
    project_id: str,
    group: str,
    item_id: str
) -> str:
    """删除项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型
        item_id: 条目ID

    Returns:
        JSON 格式的操作结果
    """
    client = _get_client()
    result = client.project_delete(project_id=project_id, group=group, item_id=item_id)
    return _tool_response(result)


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
    """
    client = _get_client()
    result = client.remove_project(project_id=project_id, mode=mode)
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
        group_name: 分组名称
        item_id: 条目ID
        operation: 操作类型 - "set"|"add"|"remove"
        tag: 单个标签 (operation="add"|"remove"时)
        tags: 标签列表逗号分隔 (operation="set"时)

    Returns:
        JSON 格式的操作结果
    """
    client = _get_client()
    result = client.manage_item_tags(
        project_id=project_id,
        group_name=group_name,
        item_id=item_id,
        operation=operation,
        tag=tag,
        tags=tags
    )
    return _tool_response(result)


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
        group_name: 分组名称 (可选)
        item_id: 条目ID (可选): 查询单个条目时指定
        status: 状态过滤 (可选)
        severity: 严重程度过滤 (可选)
        tags: 标签过滤 (可选)
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 根据 view_mode 决定默认值
        view_mode: 视图模式 (可选): "summary"(精简，默认) 或 "detail"(完整)
        summary_pattern: 摘要正则过滤 (可选)
        created_after: 创建时间起始 (可选): YYYY-MM-DD
        created_before: 创建时间截止 (可选): YYYY-MM-DD
        updated_after: 修改时间起始 (可选): YYYY-MM-DD
        updated_before: 修改时间截止 (可选): YYYY-MM-DD

    Returns:
        JSON 格式的项目信息、条目列表或单个条目详情
    """
    client = _get_client()
    result = client.project_get(
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
    return _tool_response(result)
