"""阻挡位常量定义.

定义操作级别、全局常量、文件级别映射。
"""

from enum import IntEnum
from typing import Dict


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


# 全局阻挡位 key，用于 L1 级别操作
GLOBAL_BARRIER_KEY = "__global__"


# 文件级别映射：定义每个文件需要的最低操作级别
# 如果操作级别低于文件的级别要求，则不允许修改该文件
# 文件级别 = 该文件的主要操作者级别
#
# 支持两种格式：
# 1. 精确匹配：如 "_index.json"
# 2. 模式匹配：使用 {var} 作为通配符，如 "{group}/{item_id}.json"
#    匹配时忽略实际值，只检查结构是否符合模式
FILE_LEVELS: Dict[str, OperationLevel] = {
    # L1: 全局文件
    "_index.json": OperationLevel.L1,

    # L2: 项目元数据文件
    "_project.json": OperationLevel.L2,

    # L3: 管理元数据文件（标签定义、组定义）
    "_tags.json": OperationLevel.L3,  # tag_register/delete/merge 都修改此文件
    "_groups.json": OperationLevel.L3,

    # L4: 列表目录
    "features/": OperationLevel.L4,
    "fixes/": OperationLevel.L4,
    "notes/": OperationLevel.L4,
    "{group}/": OperationLevel.L4,  # 任意组目录

    # L5: 单条目文件（拆分存储后）
    "fixes/{item_id}.json": OperationLevel.L5,
    "{group}/{item_id}.json": OperationLevel.L5,  # 任意组的条目文件
}


# 排空策略：定义每个级别需要排空的目标级别
# 每个级别排空自身等级以下的所有等级
# 格式: {级别: [需要排空的级别列表]}
DRAIN_STRATEGY = {
    OperationLevel.L1: [OperationLevel.L2, OperationLevel.L3, OperationLevel.L4, OperationLevel.L5],
    OperationLevel.L2: [OperationLevel.L3, OperationLevel.L4, OperationLevel.L5],  # L2 排空 L3+L4+L5
    OperationLevel.L3: [OperationLevel.L4, OperationLevel.L5],  # L3 排空 L4+L5
    OperationLevel.L4: [OperationLevel.L5],
    OperationLevel.L5: [],  # L5 不需要排空任何级别
}
