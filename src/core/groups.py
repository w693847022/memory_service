"""组配置和检测函数模块."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Union
import json


# 系统保留字段（不能用作自定义组名）
# 注意：内置组 features/notes/fixes/standards 不是保留字段，它们是有效的组名
RESERVED_FIELDS = ["id", "info", "tag_registry"]


class GroupType(Enum):
    """组类型枚举."""
    FEATURES = "features"
    FIXES = "fixes"
    NOTES = "notes"
    STANDARDS = "standards"

    @classmethod
    def values(cls) -> List[str]:
        return [g.value for g in cls]

    @classmethod
    def from_string(cls, s: str) -> Optional["GroupType"]:
        """从字符串获取枚举值，忽略大小写和空格."""
        s_lower = s.lower().strip()
        for g in cls:
            if g.value == s_lower:
                return g
        return None


@dataclass
class FieldConfig:
    """字段配置."""
    max_tokens: int
    required: bool = False


@dataclass
class GroupConfig:
    """组配置."""
    content: FieldConfig
    summary: FieldConfig
    status_values: List[str] = field(default_factory=list)
    severity_values: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)


@dataclass
class CustomGroupConfig:
    """自定义组配置（继承默认配置的部分设置）."""
    content_max_bytes: int = 240  # 默认约 80 tokens * 3 字节
    summary_max_bytes: int = 90   # 默认约 30 tokens * 3 字节
    allow_related: bool = False
    allowed_related_to: List[str] = field(default_factory=list)
    enable_status: bool = True    # 默认开启
    enable_severity: bool = False # 默认关闭

    def to_dict(self) -> Dict:
        """转换为字典以便 JSON 序列化."""
        return {
            "content_max_bytes": self.content_max_bytes,
            "summary_max_bytes": self.summary_max_bytes,
            "allow_related": self.allow_related,
            "allowed_related_to": self.allowed_related_to,
            "enable_status": self.enable_status,
            "enable_severity": self.enable_severity,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CustomGroupConfig":
        """从字典创建数据类."""
        return cls(
            content_max_bytes=data.get("content_max_bytes", 240),
            summary_max_bytes=data.get("summary_max_bytes", 90),
            allow_related=data.get("allow_related", False),
            allowed_related_to=data.get("allowed_related_to", []),
            enable_status=data.get("enable_status", True),
            enable_severity=data.get("enable_severity", False),
        )


@dataclass
class GroupSettings:
    """全局组设置."""
    default_related_rules: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "default_related_rules": self.default_related_rules
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GroupSettings":
        return cls(
            default_related_rules=data.get("default_related_rules", {})
        )


# 分组配置表（内置组，向后兼容）
# 注意：content/summary 的 max_tokens 是 token 数量，验证时会转换为字节（约 * 3）
GROUP_CONFIGS: Dict[str, GroupConfig] = {
    "features": GroupConfig(
        content=FieldConfig(max_tokens=80),  # ~240 字节
        summary=FieldConfig(max_tokens=30),   # ~90 字节
        status_values=["pending", "in_progress", "completed"],
        required_fields=["content", "summary", "status"],
    ),
    "fixes": GroupConfig(
        content=FieldConfig(max_tokens=80),   # ~240 字节
        summary=FieldConfig(max_tokens=30),   # ~90 字节
        status_values=["pending", "in_progress", "completed"],
        severity_values=["critical", "high", "medium", "low"],
        required_fields=["content", "summary", "status", "severity"],
    ),
    "notes": GroupConfig(
        content=FieldConfig(max_tokens=1000), # ~3000 字节
        summary=FieldConfig(max_tokens=50),   # ~150 字节
        required_fields=["content", "summary"],
    ),
    "standards": GroupConfig(
        content=FieldConfig(max_tokens=80),   # ~240 字节
        summary=FieldConfig(max_tokens=30),  # ~90 字节
        required_fields=["content", "summary"],
    ),
}

# 默认关联规则
DEFAULT_RELATED_RULES: Dict[str, List[str]] = {
    "features": ["notes"],
    "fixes": ["features", "notes"],
    "standards": ["notes"],
    "notes": [],
}


# ==================== 公共检测函数 ====================

def is_reserved_field(field_name: str) -> bool:
    """检测字段名是否为系统保留字段.

    Args:
        field_name: 字段名称

    Returns:
        是否为保留字段
    """
    return field_name in RESERVED_FIELDS


def validate_group_name(group_name: str, custom_groups: Optional[Dict[str, CustomGroupConfig]] = None) -> tuple[bool, Optional[str]]:
    """验证组名是否合法.

    Args:
        group_name: 组名称
        custom_groups: 自定义组配置字典（可选）

    Returns:
        (是否有效, 错误信息)
    """
    # 检查是否与保留字段冲突
    if is_reserved_field(group_name):
        return False, f"组名 '{group_name}' 与系统配置字段冲突"

    # 检查是否是内置组
    if group_name in GROUP_CONFIGS:
        return True, None

    # 检查是否是自定义组
    if custom_groups and group_name in custom_groups:
        return True, None

    valid_groups = ", ".join(GroupType.values())
    if custom_groups:
        valid_groups += ", " + ", ".join(custom_groups.keys())
    return False, f"无效的分组类型: {group_name} (支持: {valid_groups})"


def get_group_config(group_name: str) -> Optional[GroupConfig]:
    """获取组配置.

    Args:
        group_name: 组名称

    Returns:
        组配置对象，不存在返回 None
    """
    return GROUP_CONFIGS.get(group_name)


def get_all_groups(custom_groups: Optional[Dict[str, CustomGroupConfig]] = None) -> List[str]:
    """获取所有可用组名称（内置 + 自定义）.

    Args:
        custom_groups: 自定义组配置字典（可选）

    Returns:
        所有组名称列表
    """
    groups = GroupType.values()
    if custom_groups:
        groups = groups + list(custom_groups.keys())
    return groups


def validate_status(status: str, group_name: str, custom_config: Optional[CustomGroupConfig] = None) -> tuple[bool, Optional[str]]:
    """验证状态值是否合法.

    Args:
        status: 状态值
        group_name: 组名称
        custom_config: 自定义组配置（可选）

    Returns:
        (是否有效, 错误信息)
    """
    # 内置组
    config = get_group_config(group_name)
    if config is not None:
        if not config.status_values:
            return True, None  # 该组不支持 status
        if status in config.status_values:
            return True, None
        valid_values = ", ".join(config.status_values)
        return False, f"无效的 status 值: {status} (有效值: {valid_values})"

    # 自定义组
    if custom_config is not None:
        if not custom_config.enable_status:
            return True, None  # 自定义组未开启 status
        if status in ["pending", "in_progress", "completed"]:
            return True, None
        return False, f"无效的 status 值: {status} (有效值: pending/in_progress/completed)"

    return True, None  # 组名无效会在其他函数中检测


def validate_severity(severity: str, custom_config: Optional[CustomGroupConfig] = None) -> tuple[bool, Optional[str]]:
    """验证严重程度值是否合法.

    Args:
        severity: 严重程度值
        custom_config: 自定义组配置（可选）

    Returns:
        (是否有效, 错误信息)
    """
    # 自定义组检查
    if custom_config is not None:
        if not custom_config.enable_severity:
            return True, None  # 自定义组未开启 severity
        if severity in ["critical", "high", "medium", "low"]:
            return True, None
        return False, f"无效的 severity 值: {severity} (有效值: critical/high/medium/low)"

    # 内置组（fixes）
    fixes_config = get_group_config("fixes")
    if fixes_config and severity in fixes_config.severity_values:
        return True, None
    if severity in ["critical", "high", "medium", "low"]:
        return True, None
    return False, f"无效的 severity 值: {severity} (有效值: critical/high/medium/low)"


def validate_content_length(content: str, group_name: str, custom_config: Optional[CustomGroupConfig] = None, min_tokens: Optional[int] = None, min_bytes: Optional[int] = None) -> tuple[bool, Optional[str], Optional[int]]:
    """验证内容长度（字节验证）.

    Args:
        content: 内容
        group_name: 组名称
        custom_config: 自定义组配置（可选）
        min_tokens: 最小 token 数（可选，仅用于兼容旧接口，会转换为字节）
        min_bytes: 最小字节数（可选，默认1字节）

    Returns:
        (是否有效, 错误信息, 字节长度)
    """
    content_bytes = len(content.encode('utf-8'))

    # 计算最小字节数
    effective_min_bytes = 1
    if min_bytes is not None:
        effective_min_bytes = min_bytes
    elif min_tokens is not None:
        effective_min_bytes = min_tokens * 3  # token 转字节

    # 内置组
    config = get_group_config(group_name)
    if config is not None:
        max_bytes = config.content.max_tokens * 3  # token 转字节

        if content_bytes < effective_min_bytes:
            return False, f"内容过短：至少需要 {effective_min_bytes} 字节", content_bytes

        if content_bytes > max_bytes:
            msg = f"内容过长：{content_bytes} 字节，最大允许 {max_bytes} 字节"
            if group_name in ("features", "fixes"):
                msg += "。如果无法简化，建议建立 note 与之关联"
            return False, msg, content_bytes
        return True, None, content_bytes

    # 自定义组
    if custom_config is not None:
        max_bytes = custom_config.content_max_bytes

        if content_bytes < effective_min_bytes:
            return False, f"内容过短：至少需要 {effective_min_bytes} 字节", content_bytes

        if content_bytes > max_bytes:
            return False, f"内容过长：{content_bytes} 字节，最大允许 {max_bytes} 字节", content_bytes
        return True, None, content_bytes

    return True, None, content_bytes


def validate_summary_length(summary: str, group_name: str, custom_config: Optional[CustomGroupConfig] = None, min_tokens: Optional[int] = None, min_bytes: Optional[int] = None) -> tuple[bool, Optional[str], Optional[int]]:
    """验证摘要长度（字节验证）.

    Args:
        summary: 摘要
        group_name: 组名称
        custom_config: 自定义组配置（可选）
        min_tokens: 最小 token 数（可选，仅用于兼容旧接口，会转换为字节）
        min_bytes: 最小字节数（可选，默认1字节）

    Returns:
        (是否有效, 错误信息, 字节长度)
    """
    summary_bytes = len(summary.encode('utf-8'))

    # 计算最小字节数
    effective_min_bytes = 1
    if min_bytes is not None:
        effective_min_bytes = min_bytes
    elif min_tokens is not None:
        effective_min_bytes = min_tokens * 3  # token 转字节

    # 内置组
    config = get_group_config(group_name)
    if config is not None:
        max_bytes = config.summary.max_tokens * 3  # token 转字节

        if summary_bytes < effective_min_bytes:
            return False, f"摘要过短：至少需要 {effective_min_bytes} 字节", summary_bytes

        if summary_bytes > max_bytes:
            msg = f"摘要过长：{summary_bytes} 字节，最大允许 {max_bytes} 字节"
            if group_name in ("features", "fixes"):
                msg += "。如果无法简化，建议建立 note 与之关联"
            return False, msg, summary_bytes
        return True, None, summary_bytes

    # 自定义组
    if custom_config is not None:
        max_bytes = custom_config.summary_max_bytes

        if summary_bytes < effective_min_bytes:
            return False, f"摘要过短：至少需要 {effective_min_bytes} 字节", summary_bytes

        if summary_bytes > max_bytes:
            return False, f"摘要过长：{summary_bytes} 字节，最大允许 {max_bytes} 字节", summary_bytes
        return True, None, summary_bytes

    return True, None, summary_bytes


def is_group_with_status(group_name: str, custom_config: Optional[CustomGroupConfig] = None) -> bool:
    """检查组是否支持状态字段."""
    config = get_group_config(group_name)
    if config is not None:
        return len(config.status_values) > 0
    if custom_config is not None:
        return custom_config.enable_status
    return False


def is_group_with_severity(group_name: str, custom_config: Optional[CustomGroupConfig] = None) -> bool:
    """检查组是否支持 severity 字段."""
    config = get_group_config(group_name)
    if config is not None:
        return len(config.severity_values) > 0
    if custom_config is not None:
        return custom_config.enable_severity
    return False


def all_group_names() -> List[str]:
    """返回所有组名称列表."""
    return GroupType.values()


# 默认标签列表
DEFAULT_TAGS = [
    "implementation", "enhancement", "bug", "docs",
    "refactor", "test", "ops", "security"
]


import json
from typing import Tuple


def validate_related(
    related: Optional[str] | Optional[Dict[str, List[str]]],
    group_name: str,
    custom_config: Optional[CustomGroupConfig] = None,
    default_rules: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, str, Optional[Dict[str, List[str]]]]:
    """解析并验证 related 参数.

    Args:
        related: JSON 字符串格式或字典格式的关联数据
        group_name: 分组名称
        custom_config: 自定义组配置（可选）
        default_rules: 默认关联规则（可选）

    Returns:
        (是否有效, 错误信息, 解析后的字典)
        None 表示不更新，{} 表示删除关联，非空字典表示设置关联
    """
    if related is None:
        return True, "", None  # 不更新

    # 空字符串视为不设置关联
    if related == "":
        return True, "", None

    # 获取组的关联规则
    allowed_related_to = None

    # 内置组
    config = get_group_config(group_name)
    if config is not None:
        # 检查是否在默认关联规则中（features/fixes/standards 都在）
        if default_rules and group_name in default_rules:
            allowed_related_to = default_rules[group_name]
        elif config.status_values:  # features/fixes 有 status_values
            allowed_related_to = []
        else:
            return False, f"分组 '{group_name}' 不支持关联功能", None

    # 自定义组
    if custom_config is not None:
        if custom_config.allow_related:
            allowed_related_to = custom_config.allowed_related_to
        else:
            return False, f"分组 '{group_name}' 不支持关联功能", None

    # 如果无法确定关联规则，跳过验证
    if allowed_related_to is None:
        return True, "", None  # 无效分组名直接通过

    # 处理字典类型（MCP 协议自动解析 JSON 时）
    if isinstance(related, dict):
        related_dict = related
    else:
        # JSON 字符串解析
        try:
            related_dict = json.loads(related)
        except json.JSONDecodeError:
            return False, "related 参数 JSON 格式无效", None

    # 验证关联目标是否在允许范围内
    for rel_group, rel_ids in related_dict.items():
        if rel_group not in allowed_related_to:
            return False, f"分组 '{group_name}' 只能关联 {', '.join(allowed_related_to)}，不能关联 '{rel_group}'", None

    return True, "", related_dict
