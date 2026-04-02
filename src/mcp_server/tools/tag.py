"""MCP 标签管理工具模块.

提供标签管理相关的 MCP 工具函数。只做转发，不处理任何业务逻辑。
"""

from typing import Optional

from ._shared import _get_client, _tool_response


def tag_register(
    project_id: str,
    tag_name: str,
    summary: str,
    aliases: str = ""
) -> str:
    """注册项目标签.

    Args:
        project_id: 项目ID
        tag_name: 标签名称（英文，无空格）
        summary: 标签语义摘要（10-50字）
        aliases: 别名列表，逗号分隔（可选）

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
        project_id: 项目ID
        tag_name: 标签名称
        summary: 新的摘要（可选）

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
        project_id: 项目ID
        tag_name: 标签名称
        force: 是否强制删除（"true"/"false"，即使标签正在使用）

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
        project_id: 项目ID
        old_tag: 旧标签名称（将被删除）
        new_tag: 新标签名称（合并目标）

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
