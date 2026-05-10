"""MCP 工具共享函数模块.

提供工具函数、共用导入和响应构建函数。
"""

from typing import Optional

# 导入 HTTP 客户端
from clients.business_client import get_business_client, BusinessApiClient

# 获取全局 HTTP 客户端
_business_client: Optional[BusinessApiClient] = None


def _get_client() -> BusinessApiClient:
    """获取或创建 business API 客户端."""
    global _business_client
    if _business_client is None:
        _business_client = get_business_client()
    return _business_client


# ===================
# Helper Functions
# ===================

def _parse_tags(tags_str: str) -> list:
    """解析标签字符串为列表."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def _tool_response(result, success_data=None, success_message=None):
    """构建工具响应.

    由于 business_client 已返回 ApiResponse 对象，直接返回其 JSON 格式。
    """
    # ApiResponse 对象使用 model_dump_json() 方法（Pydantic 提供）
    if hasattr(result, 'model_dump_json'):
        return result.model_dump_json()
    # 如果是 dict，已经是 to_dict() 的结果
    elif isinstance(result, dict):
        import json
        return json.dumps(result)
    else:
        return str(result)


def _error_response(error):
    """构建错误响应."""
    from src.models import ApiResponse
    return ApiResponse(success=False, error=error).model_dump_json()


# ===================
# MCP Access Control
# ===================

# mcp_access 值常量
MCP_ACCESS_WRITABLE = "writable"   # MCP可读可写
MCP_ACCESS_READABLE = "readable"  # MCP只读
MCP_ACCESS_DISABLED = "disabled"  # MCP不可访问


def _check_mcp_access(project_id: str, group_name: str, operation: str) -> Optional[str]:
    """检查MCP客户端对指定分组的访问权限.

    Args:
        project_id: 项目ID
        group_name: 分组名称
        operation: 操作类型 "read" 或 "write"

    Returns:
        None 表示允许访问，字符串表示拒绝访问的错误消息
    """
    client = _get_client()
    result = client.list_groups(project_id)

    # 解析 ApiResponse
    if hasattr(result, 'success') and result.success:
        data = result.data if hasattr(result, 'data') else {}
        groups = data.get("groups", []) if isinstance(data, dict) else []
        for group in groups:
            if group.get("name") == group_name:
                mcp_access = group.get("mcp_access", MCP_ACCESS_WRITABLE)
                if mcp_access == MCP_ACCESS_DISABLED:
                    return f"分组 '{group_name}' 已禁止MCP访问"
                if mcp_access == MCP_ACCESS_READABLE and operation == "write":
                    return f"分组 '{group_name}' 对MCP客户端为只读，无法执行写操作"
                return None
        return f"未找到分组 '{group_name}'"

    error = getattr(result, 'error', '未知错误')
    return f"获取分组信息失败: {error}"
