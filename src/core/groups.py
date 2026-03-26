"""组配置和检测函数模块."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


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


# 分组配置表
GROUP_CONFIGS: Dict[str, GroupConfig] = {
    "features": GroupConfig(
        content=FieldConfig(max_tokens=80),
        summary=FieldConfig(max_tokens=30),
        status_values=["pending", "in_progress", "completed"],
        required_fields=["content", "summary", "status"],
    ),
    "fixes": GroupConfig(
        content=FieldConfig(max_tokens=80),
        summary=FieldConfig(max_tokens=30),
        status_values=["pending", "in_progress", "completed"],
        severity_values=["critical", "high", "medium", "low"],
        required_fields=["content", "summary", "status", "severity"],
    ),
    "notes": GroupConfig(
        content=FieldConfig(max_tokens=1000),
        summary=FieldConfig(max_tokens=50),
        required_fields=["content", "summary"],
    ),
    "standards": GroupConfig(
        content=FieldConfig(max_tokens=80),
        summary=FieldConfig(max_tokens=30),
        required_fields=["content", "summary"],
    ),
}


# ==================== 公共检测函数 ====================

def validate_group_name(group_name: str) -> tuple[bool, Optional[str]]:
    """验证组名是否合法.

    Args:
        group_name: 组名称

    Returns:
        (是否有效, 错误信息)
    """
    if group_name in GROUP_CONFIGS:
        return True, None
    valid_groups = ", ".join(GroupType.values())
    return False, f"无效的分组类型: {group_name} (支持: {valid_groups})"


def get_group_config(group_name: str) -> Optional[GroupConfig]:
    """获取组配置.

    Args:
        group_name: 组名称

    Returns:
        组配置对象，不存在返回 None
    """
    return GROUP_CONFIGS.get(group_name)


def validate_status(status: str, group_name: str) -> tuple[bool, Optional[str]]:
    """验证状态值是否合法.

    Args:
        status: 状态值
        group_name: 组名称

    Returns:
        (是否有效, 错误信息)
    """
    config = get_group_config(group_name)
    if config is None:
        return True, None  # 组名无效会在其他函数中检测

    if not config.status_values:
        return True, None  # 该组不支持 status

    if status in config.status_values:
        return True, None
    valid_values = ", ".join(config.status_values)
    return False, f"无效的 status 值: {status} (有效值: {valid_values})"


def validate_severity(severity: str) -> tuple[bool, Optional[str]]:
    """验证严重程度值是否合法.

    Args:
        severity: 严重程度值

    Returns:
        (是否有效, 错误信息)
    """
    fixes_config = get_group_config("fixes")
    if fixes_config and severity in fixes_config.severity_values:
        return True, None
    if severity in ["critical", "high", "medium", "low"]:
        return True, None
    return False, f"无效的 severity 值: {severity} (有效值: critical/high/medium/low)"


def validate_content_length(content: str, group_name: str, min_tokens: Optional[int] = 1) -> tuple[bool, Optional[str], Optional[int]]:
    """验证内容长度.

    Args:
        content: 内容
        group_name: 组名称
        min_tokens: 最小 token 数（可选）

    Returns:
        (是否有效, 错误信息, 预估token数)
    """
    config = get_group_config(group_name)
    if config is None:
        return True, None, None

    max_tokens = config.content.max_tokens
    estimated_tokens = len(content) / 3  # 简化的 token 估算

    if min_tokens is not None and estimated_tokens < min_tokens:
        return False, f"内容过短：预估 {int(estimated_tokens)} tokens，最小允许 {min_tokens} tokens（约 {min_tokens * 3} 字符）", int(estimated_tokens)

    if estimated_tokens > max_tokens:
        msg = f"内容过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens"
        if group_name in ("features", "fixes"):
            msg += "。如果无法简化，建议建立 note 与之关联"
        return False, msg, int(estimated_tokens)
    return True, None, int(estimated_tokens)


def validate_summary_length(summary: str, group_name: str, min_tokens: Optional[int] = 1) -> tuple[bool, Optional[str], Optional[int]]:
    """验证摘要长度.

    Args:
        summary: 摘要
        group_name: 组名称
        min_tokens: 最小 token 数（可选）

    Returns:
        (是否有效, 错误信息, 预估token数)
    """
    config = get_group_config(group_name)
    if config is None:
        return True, None, None

    max_tokens = config.summary.max_tokens
    estimated_tokens = len(summary) / 3

    if min_tokens is not None and estimated_tokens < min_tokens:
        return False, f"摘要过短：预估 {int(estimated_tokens)} tokens，最小允许 {min_tokens} tokens（约 {min_tokens * 3} 字符）", int(estimated_tokens)

    if estimated_tokens > max_tokens:
        msg = f"摘要过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens"
        if group_name in ("features", "fixes"):
            msg += "。如果无法简化，建议建立 note 与之关联"
        return False, msg, int(estimated_tokens)
    return True, None, int(estimated_tokens)


def is_group_with_status(group_name: str) -> bool:
    """检查组是否支持状态字段."""
    config = get_group_config(group_name)
    return config is not None and len(config.status_values) > 0


def is_group_with_severity(group_name: str) -> bool:
    """检查组是否支持 severity 字段."""
    config = get_group_config(group_name)
    return config is not None and len(config.severity_values) > 0


def all_group_names() -> List[str]:
    """返回所有组名称列表."""
    return GroupType.values()
