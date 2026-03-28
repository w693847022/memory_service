"""辅助函数和装饰器模块."""

import os
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple


def detect_client() -> str:
    """检测客户端类型.

    Returns:
        客户端标识: claude-code, cursor, 或 unknown
    """
    if os.environ.get("CLAUDE_CODE", "").lower() == "true":
        return "claude-code"
    elif os.environ.get("CURSOR", "").lower() == "true":
        return "cursor"
    return "unknown"


def get_caller_ip() -> str:
    """获取调用者IP地址.

    Returns:
        IP地址或"local"/"unknown"
    """
    # stdio 模式通常是本地调用
    # SSE 模式需要从请求中获取，这里简化处理
    return "local"


def track_calls(func):
    """装饰器：追踪MCP工具调用."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular dependency
        from features.instances import call_stats

        client = detect_client()
        ip = get_caller_ip()
        tool_name = func.__name__

        # 记录调用
        call_stats.record_call(
            tool_name=tool_name,
            client=client,
            ip=ip,
        )

        return func(*args, **kwargs)
    return wrapper


@dataclass
class PaginationResult:
    items: List[Any]
    pagination_meta: Dict[str, Any]
    filtered_total: int


def resolve_default_size(size, view_mode):
    """summary模式默认20条，detail模式默认全部."""
    size_int = int(size) if size not in (None, "", "0") else 0
    return 20 if size_int == 0 and view_mode == "summary" else (size or 0)


def paginate(items, page=1, size=0) -> Tuple[Optional[PaginationResult], Optional[str]]:
    """通用分页. 返回 (PaginationResult, None) 或 (None, error)."""
    try:
        page_int, size_int = int(page) if page else 1, int(size) if size else 0
    except (ValueError, TypeError):
        return None, "分页参数必须为有效的整数"
    filtered_total = len(items)
    if size_int <= 0:
        return PaginationResult(items, {}, filtered_total), None
    if page_int < 1:
        return None, f"无效的页码: {page_int}"
    if size_int < 0:
        return None, f"无效的每页条数: {size_int}"
    tp = (filtered_total + size_int - 1) // size_int if filtered_total > 0 else 0
    meta = {"page": page_int, "size": size_int, "total_pages": tp,
            "has_next": page_int < tp, "has_prev": page_int > 1}
    return PaginationResult(items[(page_int - 1) * size_int:page_int * size_int], meta, filtered_total), None
