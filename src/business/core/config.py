"""配置和初始化模块 - 代理到 common 模块."""

# 为了保持向后兼容，从 common 导入
from common.config import parse_args

__all__ = ["parse_args"]
