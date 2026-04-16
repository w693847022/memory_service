"""MCP 标签管理工具模块.

提供标签管理相关的 MCP 工具函数。只做转发，不处理任何业务逻辑。
"""

from typing import Optional

from ._shared import _get_client, _tool_response


# ==================== 参数说明 ====================
"""
【参数获取方式和允许值说明】

1. project_id (项目ID)
   - 获取方式: 通过 project_list() 查询所有项目，从返回结果中的 "id" 字段获取
   - 格式: UUID 字符串 (如: "550e8400-e29b-41d4-a716-446655440000")

2. tag_name (标签名称)
   - 格式: 英文，无空格 (如: "api", "feature", "enhancement")
   - 建议: 使用有意义的名称，便于理解和搜索
   - 限制: 不能包含特殊字符

3. summary (标签语义摘要)
   - 格式: 10-50字的描述
   - 作用: 说明标签的用途和含义

4. aliases (别名列表)
   - 格式: 逗号分隔 (如: "API,接口,http")
   - 作用: 提供别名方便搜索

5. force (强制删除)
   - 允许值: "true", "false"
   - 默认: "false"
   - 说明: "true" 时即使标签正在使用也会强制删除

6. old_tag / new_tag (合并标签)
   - old_tag: 旧标签名称（将被删除）
   - new_tag: 新标签名称（合并目标）
   - 作用: 将所有使用 old_tag 的条目改为使用 new_tag
"""


def tag_register(
    project_id: str,
    tag_name: str,
    summary: str,
    aliases: str = ""
) -> str:
    """注册项目标签.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串
        tag_name: 标签名称 (必填)
            - 格式: 英文，无空格 (如: "api", "feature")
            - 建议: 使用有意义的名称
        summary: 标签语义摘要 (必填)
            - 格式: 10-50字的描述
            - 作用: 说明标签的用途和含义
        aliases: 别名列表 (可选)
            - 格式: 逗号分隔
            - 示例: "API,接口,http"
            - 默认: 空

    Returns:
        JSON 格式的注册结果
    """
    client = _get_client()
    result = client.tag_register(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary,
        aliases=aliases
    )
    return _tool_response(result)


def tag_update(
    project_id: str,
    tag_name: str,
    summary: Optional[str] = None
) -> str:
    """更新已注册标签的语义信息.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串
        tag_name: 标签名称 (必填)
            - 格式: 已注册的标签名称
            - 获取方式: project_tags_info(project_id) 查询
        summary: 新的摘要 (可选)
            - 格式: 10-50字的描述
            - 传入 None 表示不更新

    Returns:
        JSON 格式的更新结果
    """
    client = _get_client()
    result = client.tag_update(
        project_id=project_id,
        tag_name=tag_name,
        summary=summary
    )
    return _tool_response(result)


def tag_delete(
    project_id: str,
    tag_name: str,
    force: str = "false"
) -> str:
    """删除标签注册.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串
        tag_name: 标签名称 (必填)
            - 格式: 已注册的标签名称
            - 获取方式: project_tags_info(project_id) 查询
        force: 是否强制删除 (可选)
            - 允许值: "true", "false"
            - 默认: "false"
            - 说明: "true" 时即使标签正在使用也会强制删除

    Returns:
        JSON 格式的删除结果
    """
    client = _get_client()
    result = client.tag_delete(
        project_id=project_id,
        tag_name=tag_name,
        force=force
    )
    return _tool_response(result)


def tag_merge(
    project_id: str,
    old_tag: str,
    new_tag: str
) -> str:
    """合并标签：将所有 old_tag 的引用迁移到 new_tag.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
            - 格式: UUID 字符串
        old_tag: 旧标签名称 (必填)
            - 格式: 已注册的标签名称
            - 说明: 合并后此标签将被删除
        new_tag: 新标签名称 (必填)
            - 格式: 已注册的标签名称
            - 说明: 合并目标，所有 old_tag 的引用将迁移到此标签

    Returns:
        JSON 格式的合并结果
    """
    client = _get_client()
    result = client.tag_merge(
        project_id=project_id,
        old_tag=old_tag,
        new_tag=new_tag
    )
    return _tool_response(result)
