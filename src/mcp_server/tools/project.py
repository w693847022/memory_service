"""MCP 项目管理工具模块.

提供项目管理相关的 MCP 工具函数。只做转发，不处理任何业务逻辑。
"""

from typing import Optional, Union, Dict, List

from ._shared import _get_client, _tool_response


# ==================== 参数说明 ====================
"""
【参数获取方式和允许值说明】

1. project_id (项目ID)
   - 获取方式: 通过 project_list() 查询所有项目，从返回结果中的 "id" 字段获取
   - 格式: UUID 字符串 (如: "550e8400-e29b-41d4-a716-446655440000")
   - 注意: project_id 是项目注册时自动生成的唯一标识

2. group_name (分组名称)
   - 内置分组: features, fixes, notes, standards
   - 自定义分组: 通过 create_custom_group() 创建的分组名称
   - 获取方式: 通过 project_groups_list(project_id) 查询项目的所有分组

3. item_id (条目ID)
   - 格式: {group}_{timestamp}_{sequence} (如: "feat_20260403_2", "fix_20260323_11")
   - 获取方式: 通过 project_get(project_id, group_name) 查询分组列表，从返回结果的 "id" 字段获取

4. status (状态)
   - features/fixes 分组支持: pending, in_progress, completed
   - 其他分组: 不支持状态字段
   - 默认值: pending

5. severity (严重程度)
   - 仅 fixes 分组支持: critical, high, medium, low
   - 其他分组: 不支持严重程度字段
   - 默认值: medium

6. tags (标签)
   - 格式: 逗号分隔的字符串 (如: "feature,api,enhancement")
   - 建议先通过 tag_register() 注册标签，以便添加语义说明
   - 获取已注册标签: 通过 project_tags_info(project_id) 查询

7. related (关联条目)
   - 格式: JSON 字符串或字典 {"group_name": ["item_id1", "item_id2"]}
   - 示例: {"features": ["feat_20260403_2"], "notes": ["note_20260323_5"]}
   - 限制: features→notes, fixes→features+notes, standards→notes
   - 获取: project_get(project_id, group_name) 查询获取 item_id

8. view_mode (视图模式)
   - 允许值: summary (精简视图), detail (完整视图)
   - 默认值: summary

9. operation (标签操作类型)
   - 允许值: set (设置), add (添加), remove (移除)

10. mode (删除/归档模式)
    - 允许值: archive (归档), delete (永久删除)
    - 默认值: archive

11. 日期格式
    - created_after, created_before, updated_after, updated_before
    - 格式: YYYY-MM-DD (如: "2026-04-01")

12. 分页参数
    - page: 页码，从 1 开始
    - size: 每页条数，0 表示使用默认值
"""


def project_register(name: str, path: str = "", summary: str = "", tags: str = "") -> str:
    """注册一个新项目.

    Args:
        name: 项目名称 (必填)
            - 获取方式: 用户输入或从项目路径自动提取
            - 限制: 不能与现有项目同名
        path: 项目路径 (可选)
            - 格式: 绝对路径或相对路径 (如: "/home/user/myproject")
            - 默认: 空
        summary: 项目摘要 (可选)
            - 建议: 简短描述项目用途，10-50字
            - 默认: 空
        tags: 项目标签 (可选)
            - 格式: 逗号分隔 (如: "web,api,service")
            - 默认: 空

    Returns:
        JSON 格式的注册结果，包含新生成的 project_id
    """
    client = _get_client()
    result = client.register_project(name=name, path=path, summary=summary, tags=tags)
    return _tool_response(result)


def project_rename(project_id: str, new_name: str) -> str:
    """重命名项目（修改 name 字段并重命名目录）.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串
        new_name: 新的项目名称 (必填)
            - 获取方式: 用户输入
            - 限制: 不能与其他项目同名

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
        view_mode: 视图模式 (可选)
            - 允许值: "summary"(精简), "detail"(完整)
            - 默认: "summary"
        page: 页码 (可选)
            - 范围: 从 1 开始
            - 默认: 1
        size: 每页条数 (可选)
            - 0 表示使用默认值
            - 默认: 0
        name_pattern: 项目名称正则过滤 (可选)
            - 格式: 正则表达式 (如: "test.*" 匹配所有以 test 开头的项目)
            - 默认: 空 (不过滤)
        include_archived: 是否包含归档项目 (可选)
            - 允许值: True, False
            - 默认: False

    Returns:
        JSON 格式的项目列表，包含项目的 id、name、path 等信息
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
    """列出项目的所有分组（内置组 + 自定义组）及其配置.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串

    Returns:
        JSON 格式的分组列表，每个分组包含：
        - name: 分组名称
        - count: 该分组下的条目数量
        - is_builtin: 是否为内置分组
        - content_max_bytes: 内容最大字节数
        - summary_max_bytes: 摘要最大字节数
        - allow_related: 是否允许关联其他分组
        - allowed_related_to: 允许关联的分组列表
        - enable_status: 是否启用状态字段
        - enable_severity: 是否启用严重程度字段
        - status_values: 支持的状态值列表
        - severity_values: 支持的严重程度值列表
        - required_fields: 必填字段列表
    """
    client = _get_client()
    # list_groups 现在返回完整配置 + settings
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
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group_name: 分组名称 (可选)
            - 允许值: features, fixes, notes, standards 或自定义分组名
            - 获取方式: project_groups_list(project_id) 返回结果
            - 默认: 空 (查询所有分组的标签)
        tag_name: 标签名称 (可选)
            - 为空则返回所有标签
            - 指定则返回单个标签的详细信息
            - 默认: 空
        unregistered_only: 仅返回未注册标签 (可选)
            - 允许值: True, False
            - 默认: False
        page: 页码 (可选)
            - 范围: 从 1 开始
            - 默认: 1
        size: 每页条数 (可选)
            - 0 表示使用默认值
            - 默认: 0
        view_mode: 视图模式 (可选)
            - 允许值: "summary"(精简), "detail"(完整)
            - 默认: "summary"
        summary_pattern: 摘要正则过滤 (可选)
            - 格式: 正则表达式
            - 默认: 空
        tag_name_pattern: 标签名正则过滤 (可选)
            - 格式: 正则表达式
            - 默认: 空

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
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group: 分组类型 (必填)
            - 内置: features, fixes, notes, standards
            - 自定义: 通过 create_custom_group() 创建的分组名
            - 获取方式: project_groups_list(project_id) 返回的 groups 列表
        content: 补充描述 (必填)
            - 格式: Markdown 格式文本
            - 限制: 通过 project_groups_list(project_id) 获取对应分组的 content_max_bytes
            - 默认: 空
        summary: 摘要 (必填)
            - 格式: 简短描述
            - 限制: 通过 project_groups_list(project_id) 获取对应分组的 summary_max_bytes
        status: 状态 (条件必填)
            - 是否必填: 通过 project_groups_list(project_id) 获取对应分组的 enable_status 和 required_fields
            - 可选值: 通过 project_groups_list(project_id) 获取对应分组的 status_values
            - 示例: features/fixes 分组支持 pending, in_progress, completed
        severity: 严重程度 (条件必填)
            - 是否必填: 通过 project_groups_list(project_id) 获取对应分组的 enable_severity 和 required_fields
            - 可选值: 通过 project_groups_list(project_id) 获取对应分组的 severity_values
            - 示例: fixes 分组支持 critical, high, medium, low
        related: 关联条目 (可选)
            - 格式: JSON 字符串，示例: '{"features": ["feat_20260403_2"]}'
            - 是否允许: 通过 project_groups_list(project_id) 获取对应分组的 allow_related
            - 可关联组: 通过 project_groups_list(project_id) 获取对应分组的 allowed_related_to
        tags: 标签列表 (可选)
            - 格式: 逗号分隔 (如: "feature,api,enhancement")
            - 默认: 空

    Returns:
        JSON 格式的操作结果，包含新生成的 item_id
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
    tags: Optional[str] = None,
    version: Optional[int] = None
) -> str:
    """更新项目条目（统一接口）.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group: 分组类型 (必填)
            - 允许值: 通过 project_groups_list(project_id) 获取所有可用分组
        item_id: 条目ID (必填)
            - 格式: {group}_{timestamp}_{sequence} (如: "feat_20260403_2")
            - 获取方式: project_get(project_id, group_name) 返回结果中的 "id" 字段
        content: 内容更新 (可选)
            - 传入 None 表示不更新，传入空字符串 "" 表示清空
            - 长度限制: 通过 project_groups_list(project_id) 获取对应分组的 content_max_bytes
        summary: 摘要更新 (可选)
            - 传入 None 表示不更新
            - 长度限制: 通过 project_groups_list(project_id) 获取对应分组的 summary_max_bytes
        status: 状态更新 (可选)
            - 传入 None 表示不更新
            - 可选值: 通过 project_groups_list(project_id) 获取对应分组的 status_values
            - 注意: 只有 enable_status=true 的分组才支持此字段
        severity: 严重程度更新 (可选)
            - 传入 None 表示不更新
            - 可选值: 通过 project_groups_list(project_id) 获取对应分组的 severity_values
            - 注意: 只有 enable_severity=true 的分组才支持此字段
        related: 关联条目更新 (可选)
            - 格式: JSON 字符串或字典，示例: {"notes": ["note_20260323_5"]} 或 '{"notes": ["note_20260323_5"]}'
            - None=不更新, {}=清空关联
            - 可关联组: 通过 project_groups_list(project_id) 获取对应分组的 allowed_related_to
            - 注意: 只有 allow_related=true 的分组才支持此字段
        tags: 标签更新 (可选)
            - 格式: 逗号分隔的字符串
            - 传入 None 表示不更新，传入空字符串 "" 表示清空标签
        version: 版本号 (可选)
            - 用途: 乐观锁并发控制
            - 获取方式: project_get() 返回结果中的 "version" 字段
            - 传入 None 表示不进行版本检查

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
        tags=tags,
        version=version
    )
    return _tool_response(result)


def project_delete(
    project_id: str,
    group: str,
    item_id: str
) -> str:
    """删除项目条目（统一接口）.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group: 分组类型 (必填)
            - 允许值: features, fixes, notes, standards 或自定义分组名
        item_id: 条目ID (必填)
            - 格式: {group}_{timestamp}_{sequence}
            - 获取方式: project_get(project_id, group_name) 返回结果中的 "id" 字段

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
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        mode: 操作模式 (可选)
            - 允许值: "archive"(归档), "delete"(永久删除)
            - 默认: "archive"
            - 注意: "delete" 操作不可逆

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
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group_name: 分组名称 (必填)
            - 允许值: features, fixes, notes, standards 或自定义分组名
        item_id: 条目ID (必填)
            - 格式: {group}_{timestamp}_{sequence}
            - 获取方式: project_get(project_id, group_name) 返回结果中的 "id" 字段
        operation: 操作类型 (必填)
            - 允许值: "set"(设置), "add"(添加), "remove"(移除)
            - set: 替换所有标签
            - add: 添加单个标签
            - remove: 移除单个标签
        tag: 单个标签 (可选)
            - operation="add" 或 "remove" 时使用
            - 默认: 空
        tags: 标签列表 (可选)
            - 格式: 逗号分隔 (如: "feature,api,enhancement")
            - operation="set" 时使用
            - 默认: 空

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
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group_name: 分组名称 (可选)
            - 允许值: features, fixes, notes, standards 或自定义分组名
            - 不传: 返回整个项目信息
            - 传入: 返回该分组的条目列表或详情
        item_id: 条目ID (可选)
            - 格式: {group}_{timestamp}_{sequence}
            - 查询单个条目详情时指定
            - 默认: 空
        status: 状态过滤 (可选)
            - 允许值: pending, in_progress, completed
            - 默认: 空 (不过滤)
        severity: 严重程度过滤 (可选)
            - 允许值: critical, high, medium, low
            - 默认: 空 (不过滤)
        tags: 标签过滤 (可选)
            - 格式: 逗号分隔 (如: "feature,api")
            - 默认: 空 (不过滤)
        page: 页码 (可选)
            - 范围: 从 1 开始
            - 默认: 1
        size: 每页条数 (可选)
            - 0 表示使用默认值
            - 默认: 0
        view_mode: 视图模式 (可选)
            - 允许值: "summary"(精简), "detail"(完整)
            - 默认: "summary"
        summary_pattern: 摘要正则过滤 (可选)
            - 格式: 正则表达式
            - 默认: 空
        created_after: 创建时间起始 (可选)
            - 格式: YYYY-MM-DD (如: "2026-04-01")
            - 默认: 空
        created_before: 创建时间截止 (可选)
            - 格式: YYYY-MM-DD
            - 默认: 空
        updated_after: 修改时间起始 (可选)
            - 格式: YYYY-MM-DD
            - 默认: 空
        updated_before: 修改时间截止 (可选)
            - 格式: YYYY-MM-DD
            - 默认: 空

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
