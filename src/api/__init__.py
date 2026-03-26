"""API Module - MCP 工具接口."""

from .tools import (
    # Project Management Tools
    project_register,
    project_rename,
    project_list,
    project_groups_list,
    project_tags_info,
    # CRUD Tools
    project_add,
    project_update,
    project_delete,
    project_item_tag_manage,
    # Tag Management Tools
    tag_register,
    tag_update,
    tag_delete,
    tag_merge,
    # Query Tools
    project_get,
    project_stats,
    # Statistics Tools
    stats_summary,
    stats_cleanup,
)

__all__ = [
    "project_register",
    "project_rename",
    "project_list",
    "project_groups_list",
    "project_tags_info",
    "project_add",
    "project_update",
    "project_delete",
    "project_item_tag_manage",
    "tag_register",
    "tag_update",
    "tag_delete",
    "tag_merge",
    "project_get",
    "project_stats",
    "stats_summary",
    "stats_cleanup",
]
