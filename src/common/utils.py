"""通用工具函数模块 - 不包含任何业务逻辑依赖."""

import re
from typing import Any, Dict, List, Optional, Tuple, Pattern

from src.models.config import PaginationResult


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
        return PaginationResult(items=items, pagination_meta={}, filtered_total=filtered_total), None
    if page_int < 1:
        return None, f"无效的页码: {page_int}"
    if size_int < 0:
        return None, f"无效的每页条数: {size_int}"
    tp = (filtered_total + size_int - 1) // size_int if filtered_total > 0 else 0
    meta = {"page": page_int, "size": size_int, "total_pages": tp,
            "has_next": page_int < tp, "has_prev": page_int > 1}
    return PaginationResult(items=items[(page_int - 1) * size_int:page_int * size_int], pagination_meta=meta, filtered_total=filtered_total), None


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


def parse_tags(tags_str: str) -> list:
    """解析标签字符串为列表."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def validate_date(date_str: str) -> bool:
    """验证日期字符串格式 (YYYY-MM-DD)."""
    if not date_str:
        return True
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def filter_tags_by_regex(tags_list: list, summary_regex=None, tag_name_regex=None) -> list:
    """正则过滤标签列表."""
    filtered = []
    for tag_item in tags_list:
        if summary_regex and not summary_regex.search(tag_item.get("summary", "")):
            continue
        if tag_name_regex and not tag_name_regex.search(tag_item.get("tag", "")):
            continue
        filtered.append(tag_item)
    return filtered
