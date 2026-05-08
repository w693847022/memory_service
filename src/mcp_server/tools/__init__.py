"""MCP 工具模块.

统一导出所有 MCP 工具函数。
"""

from ._shared import (
    _get_client,
    _parse_tags,
    _tool_response,
    _error_response,
)

from .project import (
    project_register,
    project_rename,
    project_update_info,
    project_list,
    project_groups_list,
    project_tags_info,
    project_add,
    project_update,
    project_delete,
    project_archive,
    project_item_tag_manage,
    project_get,
)

from .group import (
    create_custom_group,
)

from .tag import (
    tag_register,
    tag_update,
    tag_delete,
    tag_merge,
)

__all__ = [
    # Shared
    "_get_client",
    "_parse_tags",
    "_tool_response",
    "_error_response",
    # Project
    "project_register",
    "project_rename",
    "project_update_info",
    "project_list",
    "project_groups_list",
    "project_tags_info",
    "project_add",
    "project_update",
    "project_delete",
    "project_archive",
    "project_item_tag_manage",
    "project_get",
    # Group
    "create_custom_group",
    # Tag
    "tag_register",
    "tag_update",
    "tag_delete",
    "tag_merge",
]
