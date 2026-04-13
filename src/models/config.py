"""
Configuration models for ai_memory_mcp.

This module contains Pydantic models for configuration-related data structures,
including cache settings, connection pool settings, and pagination results.
"""

import os
from typing import Any, Dict, List

import httpx

from pydantic import BaseModel, Field


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
