"""辅助函数和装饰器模块."""

import os
from functools import wraps


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
