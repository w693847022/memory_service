"""辅助函数和装饰器模块."""

import os
import re
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


def validate_view_mode(view_mode: str) -> Tuple[bool, Optional[str]]:
    """验证 view_mode 参数.

    Args:
        view_mode: 视图模式字符串

    Returns:
        (True, None) 或 (False, error_message)
    """
    if view_mode in ("summary", "detail"):
        return True, None
    return False, f"无效的 view_mode: {view_mode} (支持: summary/detail)"


def validate_regex_pattern(pattern: str, param_name: str = "pattern") -> Tuple[Optional[re.Pattern], Optional[str]]:
    """验证正则表达式并返回编译后的对象.

    Args:
        pattern: 正则表达式字符串
        param_name: 参数名称，用于错误信息

    Returns:
        (compiled_regex, None) 或 (None, error_message)
        pattern 为空时返回 (None, None)
    """
    if not pattern:
        return None, None
    try:
        return re.compile(pattern), None
    except re.error as e:
        return None, f"无效的{param_name}正则表达式: {pattern} ({e})"


def apply_view_mode(items: list, view_mode: str, summary_fields: list) -> list:
    """根据 view_mode 过滤返回字段.

    Args:
        items: 原始数据列表
        view_mode: "summary" 或 "detail"
        summary_fields: summary 模式下保留的字段列表

    Returns:
        过滤后的数据列表
    """
    if view_mode == "summary":
        return [{k: item.get(k) for k in summary_fields} for item in items]
    return items
