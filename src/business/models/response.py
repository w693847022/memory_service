"""统一的 API 响应格式类 - 代理到 common 模块."""

# 为了保持向后兼容，从 common 导入
from common.response import ApiResponse

__all__ = ["ApiResponse"]
