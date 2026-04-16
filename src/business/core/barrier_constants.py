"""阻挡位常量定义.

定义操作级别、全局常量、文件级别映射。
"""

from src.models.enums import OperationLevel, FILE_LEVELS, DRAIN_STRATEGY

# 全局阻挡位 key，用于 L1 级别操作
GLOBAL_BARRIER_KEY = "__global__"
