"""
Configuration models for ai_memory_mcp.

This module contains Pydantic models for configuration-related data structures,
including group configurations, cache settings, connection pool settings, and pagination results.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

from pydantic import BaseModel, Field


# ==================== 组配置模型 ====================


class FieldConfig(BaseModel):
    """字段配置."""

    max_tokens: int = Field(..., description="最大 token 数")
    required: bool = Field(default=False, description="是否必填")


class GroupConfig(BaseModel):
    """组配置（内部使用，兼容旧代码）."""

    content: FieldConfig = Field(..., description="内容字段配置")
    summary: FieldConfig = Field(..., description="摘要字段配置")
    status_values: List[str] = Field(default_factory=list, description="允许的状态值列表")
    severity_values: List[str] = Field(default_factory=list, description="允许的严重程度值列表")
    required_fields: List[str] = Field(default_factory=list, description="必填字段列表")

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


# 保留 CustomGroupConfig 作为 UnifiedGroupConfig 的别名，兼容旧代码
CustomGroupConfig = UnifiedGroupConfig


# ==================== 缓存配置模型 ====================


class CacheConfig(BaseModel):
    """缓存配置."""

    # L1: 热点缓存
    l1_ttl: int = Field(default=60, description="L1 缓存 TTL（秒）")
    l1_maxsize: int = Field(default=20, description="L1 缓存最大条目数")

    # L2: 常规缓存
    l2_ttl: int = Field(default=600, description="L2 缓存 TTL（秒）")
    l2_maxsize: int = Field(default=100, description="L2 缓存最大条目数")

    # L3: 列表缓存 (LRU)
    l3_maxsize: int = Field(default=1000, description="L3 缓存最大条目数")

    # 热点识别
    hot_threshold: int = Field(default=10, description="升级为热点的访问次数阈值")
    promotion_enabled: bool = Field(default=True, description="是否启用自动升级")


class CacheStats(BaseModel):
    """缓存统计."""

    l1_hits: int = Field(default=0, description="L1 缓存命中次数")
    l1_misses: int = Field(default=0, description="L1 缓存未命中次数")
    l2_hits: int = Field(default=0, description="L2 缓存命中次数")
    l2_misses: int = Field(default=0, description="L2 缓存未命中次数")
    l3_hits: int = Field(default=0, description="L3 缓存命中次数")
    l3_misses: int = Field(default=0, description="L3 缓存未命中次数")
    promotions: int = Field(default=0, description="L2→L1 升级次数")
    total_access: int = Field(default=0, description="总访问次数")

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率."""
        total_hits = self.l1_hits + self.l2_hits + self.l3_hits
        total = total_hits + self.l1_misses + self.l2_misses + self.l3_misses
        return total_hits / total if total > 0 else 0.0


# ==================== 连接池配置模型 ====================


class ConnectionPoolConfig(BaseModel):
    """HTTP 客户端连接池配置.

    通过环境变量配置连接池参数，支持 HTTP/2 可选启用。
    """

    max_connections: int = Field(..., description="最大连接数")
    max_keepalive_connections: int = Field(..., description="最大保持连接数")
    keepalive_expiry: float = Field(..., description="保持连接过期时间（秒）")
    http2: bool = Field(..., description="是否启用 HTTP/2")
    timeout: float = Field(..., description="请求超时时间（秒）")

    @classmethod
    def from_env(cls, timeout: float = 30.0) -> "ConnectionPoolConfig":
        """从环境变量加载配置.

        Args:
            timeout: 请求超时时间（秒），默认 30.0

        Returns:
            ConnectionPoolConfig 配置对象
        """
        return cls(
            max_connections=int(
                os.environ.get("BUSINESS_API_MAX_CONNECTIONS", "100")
            ),
            max_keepalive_connections=int(
                os.environ.get("BUSINESS_API_MAX_KEEPALIVE_CONNECTIONS", "20")
            ),
            keepalive_expiry=float(
                os.environ.get("BUSINESS_API_KEEPALIVE_EXPIRY", "5.0")
            ),
            http2=os.environ.get("BUSINESS_API_HTTP2", "false").lower()
            in ("true", "yes", "1"),
            timeout=timeout,
        )

    def to_limits(self) -> httpx.Limits:
        """转换为 httpx.Limits 对象.

        Returns:
            httpx.Limits 对象
        """
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry,
        )


# ==================== 分页模型 ====================


class PaginationResult(BaseModel):
    """分页结果."""

    items: List[Any] = Field(..., description="分页后的数据列表")
    pagination_meta: Dict[str, Any] = Field(..., description="分页元数据")
    filtered_total: int = Field(..., description="过滤后的总数")
