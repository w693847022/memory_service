"""MCP 分组管理工具模块.

提供分组管理相关的 MCP 工具函数。只做转发，不处理任何业务逻辑。
"""

from ._shared import _get_client, _tool_response, _error_response


# MCP 层保留的自定义组名前缀
# frontend_ 前缀专用于 Web 前端，仅通过 REST API 创建，MCP 客户端不允许创建。
# 如需创建前端专用分组，请使用 REST API 的 POST /api/projects/{project_id}/groups 接口。
_MCP_RESTRICTED_PREFIXES = ("frontend_",)


def create_custom_group(
    project_id: str,
    group_name: str,
    content_max_bytes: int = 240,
    summary_max_bytes: int = 90,
    allow_related: bool = False,
    allowed_related_to: str = "",
    enable_status: bool = True,
    enable_severity: bool = False,
    max_tags: int = 2,
    description: str = "",
    mcp_access: str = "writable",
    max_items: int = 0,
) -> str:
    """创建自定义组.

    Args:
        project_id: 项目ID (必填)
            - 获取方式: project_list() 返回结果中的 "id" 字段
        group_name: 自定义组名称 (必填)
            - 限制: 不能与现有组同名，不能使用系统保留字段名
            - 注意: 不允许使用 "frontend_" 前缀，该前缀专用于 Web 前端，
              仅可通过 REST API 创建。如需创建前端专用分组，请使用
              REST API 的 POST /api/projects/{project_id}/groups 接口。
        content_max_bytes: 内容最大字节数 (可选)
            - 默认: 240
        summary_max_bytes: 摘要最大字节数 (可选)
            - 默认: 90
        allow_related: 是否允许关联 (可选)
            - 默认: False
        allowed_related_to: 允许关联的目标组列表 (可选)
            - 格式: 逗号分隔
            - 默认: 空
        enable_status: 是否启用状态字段 (可选)
            - 默认: True
        enable_severity: 是否启用严重程度字段 (可选)
            - 默认: False
        max_tags: 单个条目最大标签数量 (可选)
            - 默认: 2
        description: 组描述 (可选)
            - 默认: 空
        mcp_access: MCP访问控制 (可选)
            - 允许值: "writable"(可读写), "readable"(只读), "disabled"(不可访问)
            - 默认: "writable"
        max_items: 最大条目数量 (可选)
            - 0 表示无限制
            - 默认: 0

    Returns:
        JSON 格式的操作结果
    """
    # 检查 MCP 层保留前缀
    for prefix in _MCP_RESTRICTED_PREFIXES:
        if group_name.startswith(prefix):
            return _error_response(
                f"MCP 客户端不允许创建 '{prefix}' 前缀的自定义组，"
                f"该前缀专用于 Web 前端。请通过 REST API 创建。"
            )

    client = _get_client()
    result = client.create_custom_group(
        project_id=project_id,
        group_name=group_name,
        content_max_bytes=content_max_bytes,
        summary_max_bytes=summary_max_bytes,
        allow_related=allow_related,
        allowed_related_to=allowed_related_to,
        enable_status=enable_status,
        enable_severity=enable_severity,
        max_tags=max_tags,
        description=description,
        mcp_access=mcp_access,
        max_items=max_items,
    )
    return _tool_response(result)
