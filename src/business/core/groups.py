"""组配置和检测函数模块."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
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
    """组配置（内部使用，兼容旧代码）."""
    content: FieldConfig
    summary: FieldConfig
    status_values: List[str] = field(default_factory=list)
    severity_values: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)

    def to_unified_dict(self) -> Dict[str, Any]:
        """转换为统一配置字典（用于 JSON 存储）."""
        return {
            "content_max_bytes": self.content.max_tokens * 3,
            "summary_max_bytes": self.summary.max_tokens * 3,
            "allow_related": bool(self.status_values),
            "allowed_related_to": [],
            "enable_status": bool(self.status_values),
            "enable_severity": bool(self.severity_values),
            "status_values": self.status_values,
            "severity_values": self.severity_values,
            "required_fields": self.required_fields,
        }

    @classmethod
    def from_unified_dict(cls, data: Dict[str, Any]) -> "GroupConfig":
        """从统一配置字典创建 GroupConfig."""
        content_max = data.get("content_max_bytes", 240) // 3
        summary_max = data.get("summary_max_bytes", 90) // 3
        return cls(
            content=FieldConfig(max_tokens=content_max),
            summary=FieldConfig(max_tokens=summary_max),
            status_values=data.get("status_values", []),
            severity_values=data.get("severity_values", []),
            required_fields=data.get("required_fields", ["content", "summary"]),
        )


@dataclass
class UnifiedGroupConfig:
    """统一组配置（内置组和自定义组通用）."""
    content_max_bytes: int = 240
    summary_max_bytes: int = 90
    allow_related: bool = False
    allowed_related_to: List[str] = field(default_factory=list)
    enable_status: bool = True
    enable_severity: bool = False
    status_values: List[str] = field(default_factory=list)
    severity_values: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    is_builtin: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典以便 JSON 序列化."""
        return {
            "content_max_bytes": self.content_max_bytes,
            "summary_max_bytes": self.summary_max_bytes,
            "allow_related": self.allow_related,
            "allowed_related_to": self.allowed_related_to,
            "enable_status": self.enable_status,
            "enable_severity": self.enable_severity,
            "status_values": self.status_values,
            "severity_values": self.severity_values,
            "required_fields": self.required_fields,
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedGroupConfig":
        """从字典创建数据类."""
        if isinstance(data, cls):
            return data
        return cls(
            content_max_bytes=data.get("content_max_bytes", 240),
            summary_max_bytes=data.get("summary_max_bytes", 90),
            allow_related=data.get("allow_related", False),
            allowed_related_to=data.get("allowed_related_to", []),
            enable_status=data.get("enable_status", True),
            enable_severity=data.get("enable_severity", False),
            status_values=data.get("status_values", []),
            severity_values=data.get("severity_values", []),
            required_fields=data.get("required_fields", ["content", "summary"]),
            is_builtin=data.get("is_builtin", False),
        )


# 保留 CustomGroupConfig 作为 UnifiedGroupConfig 的别名，兼容旧代码
CustomGroupConfig = UnifiedGroupConfig


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


# 默认内置组配置（用于初始化 JSON 存储）
DEFAULT_GROUP_CONFIGS: Dict[str, Dict[str, Any]] = {
    "features": {
        "content_max_bytes": 4000,
        "summary_max_bytes": 90,
        "allow_related": True,
        "allowed_related_to": ["notes"],
        "enable_status": True,
        "enable_severity": False,
        "status_values": ["pending", "in_progress", "completed"],
        "severity_values": [],
        "required_fields": ["content", "summary", "status"],
        "is_builtin": True,
    },
    "fixes": {
        "content_max_bytes": 4000,
        "summary_max_bytes": 90,
        "allow_related": True,
        "allowed_related_to": ["features", "notes"],
        "enable_status": True,
        "enable_severity": True,
        "status_values": ["pending", "in_progress", "completed"],
        "severity_values": ["critical", "high", "medium", "low"],
        "required_fields": ["content", "summary", "status", "severity"],
        "is_builtin": True,
    },
    "notes": {
        "content_max_bytes": 4000,
        "summary_max_bytes": 90,
        "allow_related": False,
        "allowed_related_to": [],
        "enable_status": False,
        "enable_severity": False,
        "status_values": [],
        "severity_values": [],
        "required_fields": ["content", "summary"],
        "is_builtin": True,
    },
    "standards": {
        "content_max_bytes": 4000,
        "summary_max_bytes": 90,
        "allow_related": True,
        "allowed_related_to": ["notes"],
        "enable_status": False,
        "enable_severity": False,
        "status_values": [],
        "severity_values": [],
        "required_fields": ["content", "summary"],
        "is_builtin": True,
    },
}

# 使用独立文件存储 content 的默认组
CONTENT_SEPARATE_GROUPS = {"features", "fixes", "notes", "standards"}

# 默认关联规则
DEFAULT_RELATED_RULES: Dict[str, List[str]] = {
    "features": ["notes"],
    "fixes": ["features", "notes"],
    "standards": ["notes"],
    "notes": [],
}


# ==================== 公共检测函数 ====================

def is_reserved_field(field_name: str) -> bool:
    """检测字段名是否为系统保留字段."""
    return field_name in RESERVED_FIELDS


def validate_group_name(group_name: str, all_groups: Optional[Dict[str, UnifiedGroupConfig]] = None) -> tuple[bool, Optional[str]]:
    """验证组名是否合法.

    Args:
        group_name: 组名称
        all_groups: 所有组配置字典（内置+自定义，可选）

    Returns:
        (是否有效, 错误信息)
    """
    if is_reserved_field(group_name):
        return False, f"组名 '{group_name}' 与系统配置字段冲突"

    # 检查是否是内置组
    if group_name in DEFAULT_GROUP_CONFIGS:
        return True, None

    # 检查是否是自定义组
    if all_groups and group_name in all_groups:
        return True, None

    valid_groups = ", ".join(GroupType.values())
    if all_groups:
        valid_groups += ", " + ", ".join(all_groups.keys())
    return False, f"无效的分组类型: {group_name} (支持: {valid_groups})"


def get_group_config(group_name: str, all_groups: Optional[Dict[str, UnifiedGroupConfig]] = None) -> Optional[UnifiedGroupConfig]:
    """获取组配置.

    Args:
        group_name: 组名称
        all_groups: 所有组配置字典（内置+自定义，可选）

    Returns:
        组配置对象，不存在返回 None
    """
    # 先从 all_groups 查找（可能包含覆盖的内置组配置）
    if all_groups and group_name in all_groups:
        return all_groups[group_name]
    # 再从默认内置组配置查找
    if group_name in DEFAULT_GROUP_CONFIGS:
        return UnifiedGroupConfig.from_dict(DEFAULT_GROUP_CONFIGS[group_name])
    return None


def get_all_groups(all_groups: Optional[Dict[str, UnifiedGroupConfig]] = None) -> List[str]:
    """获取所有可用组名称（内置 + 自定义）.

    Args:
        all_groups: 所有组配置字典（可选）

    Returns:
        所有组名称列表
    """
    groups = GroupType.values()
    if all_groups:
        groups = groups + list(all_groups.keys())
    return groups


def validate_status(status: str, group_name: str, config: Optional[UnifiedGroupConfig] = None) -> tuple[bool, Optional[str]]:
    """验证状态值是否合法.

    Args:
        status: 状态值
        group_name: 组名称
        config: 组配置（可选）

    Returns:
        (是否有效, 错误信息)
    """
    if config is None:
        config = get_group_config(group_name)

    if config is not None:
        if not config.enable_status:
            return True, None
        # 如果没有定义 status_values，使用默认值
        status_values = config.status_values if config.status_values else ["pending", "in_progress", "completed"]
        if status in status_values:
            return True, None
        valid_values = ", ".join(status_values)
        return False, f"无效的 status 值: {status} (有效值: {valid_values})"

    return True, None


def validate_severity(severity: str, config: Optional[UnifiedGroupConfig] = None) -> tuple[bool, Optional[str]]:
    """验证严重程度值是否合法.

    Args:
        severity: 严重程度值
        config: 组配置（可选）

    Returns:
        (是否有效, 错误信息)
    """
    if config is None:
        config = get_group_config("fixes")

    if config is not None:
        if not config.enable_severity:
            return True, None
        # 如果没有定义 severity_values，使用默认值
        severity_values = config.severity_values if config.severity_values else ["critical", "high", "medium", "low"]
        if severity in severity_values:
            return True, None
        return False, f"无效的 severity 值: {severity} (有效值: {', '.join(severity_values)})"

    if severity in ["critical", "high", "medium", "low"]:
        return True, None
    return False, f"无效的 severity 值: {severity} (有效值: critical/high/medium/low)"


def validate_content_length(content: str, group_name: str, config: Optional[UnifiedGroupConfig] = None, min_tokens: Optional[int] = None, min_bytes: Optional[int] = None) -> tuple[bool, Optional[str], Optional[int]]:
    """验证内容长度（字节验证）.

    Args:
        content: 内容
        group_name: 组名称
        config: 组配置（可选）
        min_tokens: 最小 token 数（可选，仅用于兼容旧接口，会转换为字节）
        min_bytes: 最小字节数（可选，默认1字节）

    Returns:
        (是否有效, 错误信息, 字节长度)
    """
    content_bytes = len(content.encode('utf-8'))

    effective_min_bytes = 1
    if min_bytes is not None:
        effective_min_bytes = min_bytes
    elif min_tokens is not None:
        effective_min_bytes = min_tokens * 3

    if config is None:
        config = get_group_config(group_name)

    if config is not None:
        max_bytes = config.content_max_bytes

        if content_bytes < effective_min_bytes:
            return False, f"内容过短：至少需要 {effective_min_bytes} 字节", content_bytes

        if content_bytes > max_bytes:
            msg = f"内容过长：{content_bytes} 字节，最大允许 {max_bytes} 字节"
            return False, msg, content_bytes
        return True, None, content_bytes

    return True, None, content_bytes


def validate_summary_length(summary: str, group_name: str, config: Optional[UnifiedGroupConfig] = None, min_tokens: Optional[int] = None, min_bytes: Optional[int] = None) -> tuple[bool, Optional[str], Optional[int]]:
    """验证摘要长度（字节验证）.

    Args:
        summary: 摘要
        group_name: 组名称
        config: 组配置（可选）
        min_tokens: 最小 token 数（可选，仅用于兼容旧接口，会转换为字节）
        min_bytes: 最小字节数（可选，默认1字节）

    Returns:
        (是否有效, 错误信息, 字节长度)
    """
    summary_bytes = len(summary.encode('utf-8'))

    effective_min_bytes = 1
    if min_bytes is not None:
        effective_min_bytes = min_bytes
    elif min_tokens is not None:
        effective_min_bytes = min_tokens * 3

    if config is None:
        config = get_group_config(group_name)

    if config is not None:
        max_bytes = config.summary_max_bytes

        if summary_bytes < effective_min_bytes:
            return False, f"摘要过短：至少需要 {effective_min_bytes} 字节", summary_bytes

        if summary_bytes > max_bytes:
            msg = f"摘要过长：{summary_bytes} 字节，最大允许 {max_bytes} 字节"
            return False, msg, summary_bytes
        return True, None, summary_bytes

    return True, None, summary_bytes


def is_group_with_status(group_name: str, config: Optional[UnifiedGroupConfig] = None) -> bool:
    """检查组是否支持状态字段."""
    if config is None:
        config = get_group_config(group_name)
    if config is not None:
        return config.enable_status and len(config.status_values) > 0
    return False


def is_group_with_severity(group_name: str, config: Optional[UnifiedGroupConfig] = None) -> bool:
    """检查组是否支持 severity 字段."""
    if config is None:
        config = get_group_config(group_name)
    if config is not None:
        return config.enable_severity and len(config.severity_values) > 0
    return False


def all_group_names() -> List[str]:
    """返回所有内置组名称列表."""
    return GroupType.values()


# 默认标签列表
DEFAULT_TAGS = [
    "implementation", "enhancement", "bug", "docs",
    "refactor", "test", "ops", "security"
]


from typing import Tuple


def validate_related(
    related: Optional[str] | Optional[Dict[str, List[str]]],
    group_name: str,
    config: Optional[UnifiedGroupConfig] = None,
    default_rules: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, str, Optional[Dict[str, List[str]]]]:
    """解析并验证 related 参数.

    Args:
        related: JSON 字符串格式或字典格式的关联数据
        group_name: 分组名称
        config: 组配置（可选）
        default_rules: 默认关联规则（可选）

    Returns:
        (是否有效, 错误信息, 解析后的字典)
        None 表示不更新，{} 表示删除关联，非空字典表示设置关联
    """
    if related is None:
        return True, "", None

    if related == "":
        return True, "", None

    allowed_related_to = None

    if config is None:
        config = get_group_config(group_name)

    if config is not None:
        if config.allow_related:
            allowed_related_to = config.allowed_related_to
        else:
            return False, f"分组 '{group_name}' 不支持关联功能", None

    if allowed_related_to is None:
        return True, "", None

    if isinstance(related, dict):
        related_dict = related
    else:
        try:
            related_dict = json.loads(related)
        except json.JSONDecodeError:
            return False, "related 参数 JSON 格式无效", None

    for rel_group in related_dict.keys():
        if rel_group not in allowed_related_to:
            return False, f"分组 '{group_name}' 只能关联 {', '.join(allowed_related_to)}，不能关联 '{rel_group}'", None

    return True, "", related_dict
