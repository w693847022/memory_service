"""
Enumeration models for ai_memory_mcp.

This module contains all enumeration types used throughout the application,
including group types, cache levels, operation levels, and barrier levels.
"""

from enum import Enum, IntEnum
from typing import Dict, List, Optional


# ==================== 组类型枚举 ====================


class GroupType(str, Enum):
    """组类型枚举."""

    FEATURES = "features"
    FIXES = "fixes"
    NOTES = "notes"
    STANDARDS = "standards"

    @classmethod
    def values(cls) -> List[str]:
        """返回所有组类型值."""
        return [g.value for g in cls]

    @classmethod
    def from_string(cls, s: str) -> Optional["GroupType"]:
        """从字符串获取枚举值，忽略大小写和空格."""
        s_lower = s.lower().strip()
        for g in cls:
            if g.value == s_lower:
                return g
        return None


# ==================== 缓存层级枚举 ====================


class CacheLevel(str, Enum):
    """缓存层级."""

    L1_HOT = "l1_hot"  # 热点数据
    L2_WARM = "l2_warm"  # 常规数据
    L3_LIST = "l3_list"  # 列表数据


# ==================== 操作级别枚举 ====================


class OperationLevel(IntEnum):
    """操作级别枚举.

    级别越高，锁粒度越细：
    - L1: 服务级，全局锁
    - L2: 项目范围级，项目级锁
    - L3: 标签/组定义级，项目级锁
    - L4: 条目列表级，项目+组级锁
    - L5: 条目ID级，项目+条目ID级锁
    """

    L1 = 1  # 跨项目/项目列表（全局）
    L2 = 2  # 项目元数据/跨组修改
    L3 = 3  # 单管理设置/管理元数据
    L4 = 4  # 组内列表/多条目
    L5 = 5  # 单条目


# ==================== 阻挡等级枚举 ====================


class BarrierLevel(IntEnum):
    """阻挡等级枚举."""

    B1 = 1  # 服务级
    B2 = 2  # 项目范围级
    B3 = 3  # 标签/组定义级
    B4 = 4  # 条目列表级
    B5 = 5  # 条目ID级


# ==================== 文件级别映射（保留） ====================

# 文件级别映射：定义每个文件需要的最低操作级别
FILE_LEVELS: Dict[str, OperationLevel] = {
    # L1: 全局文件
    "_index.json": OperationLevel.L1,
    # L2: 项目元数据文件
    "_project.json": OperationLevel.L2,
    # L3: 管理元数据文件（标签定义、组定义）
    "_tags.json": OperationLevel.L3,
    "_groups.json": OperationLevel.L3,
    # L4: 列表目录
    "features/": OperationLevel.L4,
    "fixes/": OperationLevel.L4,
    "notes/": OperationLevel.L4,
    "{group}/": OperationLevel.L4,
    # L5: 单条目文件（拆分存储后）
    "fixes/{item_id}.json": OperationLevel.L5,
    "{group}/{item_id}.json": OperationLevel.L5,
}


# 排空策略：定义每个级别需要排空的目标级别
DRAIN_STRATEGY: Dict[OperationLevel, List[OperationLevel]] = {
    OperationLevel.L1: [OperationLevel.L2, OperationLevel.L3, OperationLevel.L4, OperationLevel.L5],
    OperationLevel.L2: [OperationLevel.L3, OperationLevel.L4, OperationLevel.L5],
    OperationLevel.L3: [OperationLevel.L4, OperationLevel.L5],
    OperationLevel.L4: [OperationLevel.L5],
    OperationLevel.L5: [],
}
