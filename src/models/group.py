"""组配置模型.

包含组配置模型、默认配置和常量。
所有组相关的模型定义集中在此文件。
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ==================== 常量 ====================

# 系统保留字段（不能用作自定义组名）
RESERVED_FIELDS = ["id", "info", "tag_registry"]

# 使用独立文件存储 content 的默认组
CONTENT_SEPARATE_GROUPS = {"features", "fixes", "notes", "standards"}

# 默认内置组配置（用于项目注册初始化，写入 _groups.json 后不再使用）
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

# 默认关联规则
DEFAULT_RELATED_RULES: Dict[str, List[str]] = {
    "features": ["notes"],
    "fixes": ["features", "notes"],
    "standards": ["notes"],
    "notes": [],
}

# 默认标签列表
DEFAULT_TAGS = [
    "implementation", "enhancement", "bug", "docs",
    "refactor", "test", "ops", "security",
]


# ==================== 模型 ====================


class UnifiedGroupConfig(BaseModel):
    """统一组配置（内置组和自定义组通用）."""

    content_max_bytes: int = Field(default=240, description="内容最大字节数")
    summary_max_bytes: int = Field(default=90, description="摘要最大字节数")
    allow_related: bool = Field(default=False, description="是否允许关联")
    allowed_related_to: List[str] = Field(default_factory=list, description="允许关联的组列表")
    enable_status: bool = Field(default=True, description="是否启用状态")
    enable_severity: bool = Field(default=False, description="是否启用严重程度")
    status_values: List[str] = Field(default_factory=list, description="状态值列表")
    severity_values: List[str] = Field(default_factory=list, description="严重程度值列表")
    required_fields: List[str] = Field(default_factory=list, description="必填字段列表")
    is_builtin: bool = Field(default=False, description="是否为内置组")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典以便 JSON 序列化."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedGroupConfig":
        """从字典创建配置."""
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


class GroupSettings(BaseModel):
    """全局组设置."""

    default_related_rules: Dict[str, List[str]] = Field(
        default_factory=dict, description="默认关联规则"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {"default_related_rules": self.default_related_rules}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupSettings":
        return cls(default_related_rules=data.get("default_related_rules", {}))
