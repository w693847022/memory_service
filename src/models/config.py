"""配置模型 - 统一管理所有配置."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml
from pydantic import BaseModel, Field

# ==================== 服务配置 ====================


class ServiceConfig(BaseModel):
    """单个服务配置基类."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


class McpConfig(ServiceConfig):
    """MCP服务配置."""

    transport: str = "stdio"  # stdio, sse, streamable-http


class FastApiConfig(ServiceConfig):
    """FastAPI服务配置."""

    pass


class BusinessConfig(ServiceConfig):
    """Business服务配置."""

    pass


# ==================== 缓存配置 ====================


class CacheL1Config(BaseModel):
    """L1缓存配置（热点缓存）."""

    ttl: int = 60
    maxsize: int = 20


class CacheL2Config(BaseModel):
    """L2缓存配置（常规缓存）."""

    ttl: int = 600
    maxsize: int = 100


class CacheL3Config(BaseModel):
    """L3缓存配置（列表缓存LRU）."""

    maxsize: int = 1000


class CacheConfig(BaseModel):
    """缓存配置."""

    l1: CacheL1Config = Field(default_factory=CacheL1Config)
    l2: CacheL2Config = Field(default_factory=CacheL2Config)
    l3: CacheL3Config = Field(default_factory=CacheL3Config)
    hot_threshold: int = 10
    promotion_enabled: bool = True

    # Backward compatibility properties
    @property
    def l1_maxsize(self) -> int:
        return self.l1.maxsize

    @property
    def l1_ttl(self) -> int:
        return self.l1.ttl

    @property
    def l2_maxsize(self) -> int:
        return self.l2.maxsize

    @property
    def l2_ttl(self) -> int:
        return self.l2.ttl

    @property
    def l3_maxsize(self) -> int:
        return self.l3.maxsize


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


# ==================== HTTP连接池配置 ====================


class HttpPoolConfig(BaseModel):
    """HTTP客户端连接池配置."""

    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    http2: bool = False
    timeout: float = 30.0

    @classmethod
    def from_env(cls, timeout: float = 30.0) -> "HttpPoolConfig":
        """从环境变量加载配置."""
        return cls(
            max_connections=int(os.environ.get("BUSINESS_API_MAX_CONNECTIONS", "100")),
            max_keepalive_connections=int(
                os.environ.get("BUSINESS_API_MAX_KEEPALIVE_CONNECTIONS", "20")
            ),
            keepalive_expiry=float(os.environ.get("BUSINESS_API_KEEPALIVE_EXPIRY", "5.0")),
            http2=os.environ.get("BUSINESS_API_HTTP2", "false").lower() in ("true", "yes", "1"),
            timeout=timeout,
        )

    def to_limits(self) -> "httpx.Limits":
        """转换为 httpx.Limits 对象."""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry,
        )


# Backward compatibility alias
ConnectionPoolConfig = HttpPoolConfig


# ==================== 组默认配置 ====================


class UnifiedGroupConfigData(BaseModel):
    """组配置数据模型（用于YAML解析）."""

    content_max_bytes: int = 4000
    summary_max_bytes: int = 90
    allow_related: bool = False
    allowed_related_to: List[str] = Field(default_factory=list)
    enable_status: bool = True
    enable_severity: bool = False
    status_values: List[str] = Field(default_factory=list)
    severity_values: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    max_tags: int = 2


class GroupsConfigData(BaseModel):
    """组配置集合（用于YAML解析）."""

    features: UnifiedGroupConfigData = Field(default_factory=UnifiedGroupConfigData)
    fixes: UnifiedGroupConfigData = Field(default_factory=UnifiedGroupConfigData)
    notes: UnifiedGroupConfigData = Field(default_factory=UnifiedGroupConfigData)
    standards: UnifiedGroupConfigData = Field(default_factory=UnifiedGroupConfigData)


# ==================== 全局设置 ====================


class Settings(BaseModel):
    """全局设置（统一配置模型）."""

    mcp: McpConfig = Field(default_factory=McpConfig)
    fastapi: FastApiConfig = Field(default_factory=FastApiConfig)
    business: BusinessConfig = Field(default_factory=BusinessConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    http: HttpPoolConfig = Field(default_factory=HttpPoolConfig)
    groups: GroupsConfigData = Field(default_factory=GroupsConfigData)
    initial_tags: List[str] = Field(default_factory=list)
    default_related_rules: Dict[str, List[str]] = Field(default_factory=dict)


# ==================== 配置加载器 ====================

# Docker环境默认路径
_DOCKER_CONFIG_PATH = Path("/app/config/service.yaml")
# 本地开发默认路径
_LOCAL_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "service.yaml"


class SettingsLoader:
    """配置加载器（单例模式）.

    优先级:
    1. 环境变量 CONFIG_PATH 指定的文件
    2. /app/config/service.yaml (Docker默认)
    3. ./config/service.yaml (本地开发默认)
    """

    _instance: Optional[Settings] = None

    @classmethod
    def get_config_path(cls) -> Path:
        """获取配置文件路径."""
        if env_path := os.environ.get("CONFIG_PATH"):
            return Path(env_path)
        if os.path.exists(_DOCKER_CONFIG_PATH):
            return _DOCKER_CONFIG_PATH
        return _LOCAL_CONFIG_PATH

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> Settings:
        """加载配置."""
        if cls._instance is not None:
            return cls._instance

        path = config_path or cls.get_config_path()

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        cls._instance = Settings(**data)
        return cls._instance

    @classmethod
    def reload(cls, config_path: Optional[Path] = None) -> Settings:
        """重新加载配置."""
        cls._instance = None
        return cls.load(config_path)

    @classmethod
    def get_settings(cls) -> Settings:
        """获取已加载的配置."""
        return cls.load()


def get_settings() -> Settings:
    """获取配置的便捷函数."""
    return SettingsLoader.get_settings()


# ==================== 分页模型 ====================


class PaginationResult(BaseModel):
    """分页结果."""

    items: List[Any] = Field(..., description="分页后的数据列表")
    pagination_meta: Dict[str, Any] = Field(..., description="分页元数据")
    filtered_total: int = Field(..., description="过滤后的总数")
