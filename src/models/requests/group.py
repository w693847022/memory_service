"""分组管理请求模型."""

from typing import Optional, List, Literal

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    """创建自定义组请求."""

    group_name: str = Field(
        ...,
        description="自定义组名称",
    )
    content_max_bytes: int = Field(
        default=240,
        description="content 字段最大字节数",
    )
    summary_max_bytes: int = Field(
        default=90,
        description="summary 字段最大字节数",
    )
    allow_related: bool = Field(
        default=False,
        description="是否允许关联",
    )
    allowed_related_to: str = Field(
        default="",
        description="允许关联的目标组列表（逗号分隔）",
    )
    enable_status: bool = Field(
        default=True,
        description="是否开启 status 字段",
    )
    enable_severity: bool = Field(
        default=False,
        description="是否开启 severity 字段",
    )
    description: str = Field(
        default="",
        description="组描述",
    )
    mcp_access: Literal["writable", "readable", "disabled"] = Field(
        default="writable",
        description="MCP访问控制: writable(可读写)/readable(只读)/disabled(不可访问)",
    )


class GroupUpdateRequest(BaseModel):
    """更新组配置请求."""

    content_max_bytes: Optional[int] = Field(
        default=None,
        description="content 字段最大字节数",
    )
    summary_max_bytes: Optional[int] = Field(
        default=None,
        description="summary 字段最大字节数",
    )
    allow_related: Optional[bool] = Field(
        default=None,
        description="是否允许关联",
    )
    allowed_related_to: Optional[str] = Field(
        default=None,
        description="允许关联的目标组列表（逗号分隔）",
    )
    enable_status: Optional[bool] = Field(
        default=None,
        description="是否开启 status 字段",
    )
    enable_severity: Optional[bool] = Field(
        default=None,
        description="是否开启 severity 字段",
    )
    max_tags: Optional[int] = Field(
        default=None,
        description="单个item最大标签数量",
    )
    status_values: Optional[str] = Field(
        default=None,
        description="状态值列表（逗号分隔）",
    )
    severity_values: Optional[str] = Field(
        default=None,
        description="严重程度值列表（逗号分隔）",
    )
    required_fields: Optional[str] = Field(
        default=None,
        description="必填字段列表（逗号分隔）",
    )
    description: Optional[str] = Field(
        default=None,
        description="组描述",
    )
    mcp_access: Optional[Literal["writable", "readable", "disabled"]] = Field(
        default=None,
        description="MCP访问控制: writable(可读写)/readable(只读)/disabled(不可访问)",
    )


class GroupSettingsUpdateRequest(BaseModel):
    """更新组设置请求."""

    default_related_rules: Optional[str] = Field(
        default=None,
        description="默认关联规则（JSON 字符串）",
    )


class ItemCreateRequest(BaseModel):
    """创建分组条目请求."""

    summary: str = Field(
        ...,
        description="摘要",
    )
    content: str = Field(
        default="",
        description="内容",
    )
    status: str = Field(
        default="",
        description="状态 (仅 features/fixes)",
    )
    severity: str = Field(
        default="medium",
        description="严重程度 (仅 fixes)",
    )
    tags: str = Field(
        default="",
        description="标签（逗号分隔）",
    )
    related: str = Field(
        default="",
        description="关联条目 (JSON 字符串)",
    )


class ItemUpdateRequest(BaseModel):
    """更新分组条目请求."""

    summary: Optional[str] = Field(
        default=None,
        description="摘要",
    )
    content: Optional[str] = Field(
        default=None,
        description="内容",
    )
    status: Optional[str] = Field(
        default=None,
        description="状态",
    )
    severity: Optional[str] = Field(
        default=None,
        description="严重程度",
    )
    tags: Optional[str] = Field(
        default=None,
        description="标签（逗号分隔）",
    )
    related: Optional[str] = Field(
        default=None,
        description="关联条目 (JSON 字符串)",
    )


class ItemTagManageRequest(BaseModel):
    """管理条目标签请求."""

    operation: str = Field(
        ...,
        pattern="^(set|add|remove)$",
        description="操作类型",
    )
    tag: str = Field(
        default="",
        description="单个标签 (add/remove 时使用)",
    )
    tags: str = Field(
        default="",
        description="标签列表（逗号分隔，set 时使用）",
    )
