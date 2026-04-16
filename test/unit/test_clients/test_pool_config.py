"""ConnectionPoolConfig 单元测试."""

import os
import pytest
import httpx
from clients.pool_config import ConnectionPoolConfig


class TestConnectionPoolConfig:
    """ConnectionPoolConfig 测试类."""

    def test_from_env_default_values(self, monkeypatch):
        """测试从环境变量加载默认值."""
        # 确保环境变量未设置
        for key in ["BUSINESS_API_MAX_CONNECTIONS",
                    "BUSINESS_API_MAX_KEEPALIVE_CONNECTIONS",
                    "BUSINESS_API_KEEPALIVE_EXPIRY",
                    "BUSINESS_API_HTTP2"]:
            monkeypatch.delenv(key, raising=False)

        config = ConnectionPoolConfig.from_env()

        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 5.0
        assert config.http2 is False
        assert config.timeout == 30.0

    def test_from_env_custom_values(self, monkeypatch):
        """测试从环境变量加载自定义值."""
        monkeypatch.setenv("BUSINESS_API_MAX_CONNECTIONS", "50")
        monkeypatch.setenv("BUSINESS_API_MAX_KEEPALIVE_CONNECTIONS", "10")
        monkeypatch.setenv("BUSINESS_API_KEEPALIVE_EXPIRY", "3.0")
        monkeypatch.setenv("BUSINESS_API_HTTP2", "true")

        config = ConnectionPoolConfig.from_env(timeout=60.0)

        assert config.max_connections == 50
        assert config.max_keepalive_connections == 10
        assert config.keepalive_expiry == 3.0
        assert config.http2 is True
        assert config.timeout == 60.0

    def test_from_env_http2_false_variants(self, monkeypatch):
        """测试 HTTP/2 环境变量的各种 false 变体."""
        for value in ["false", "False", "FALSE", "no", "No", "0"]:
            monkeypatch.setenv("BUSINESS_API_HTTP2", value)
            config = ConnectionPoolConfig.from_env()
            assert config.http2 is False, f"Expected False for value: {value}"

    def test_from_env_http2_true_variants(self, monkeypatch):
        """测试 HTTP/2 环境变量的各种 true 变体."""
        for value in ["true", "True", "TRUE", "yes", "Yes", "1"]:
            monkeypatch.setenv("BUSINESS_API_HTTP2", value)
            config = ConnectionPoolConfig.from_env()
            assert config.http2 is True, f"Expected True for value: {value}"

    def test_to_limits(self):
        """测试转换为 httpx.Limits 对象."""
        config = ConnectionPoolConfig(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=5.0,
            http2=True,
            timeout=30.0
        )

        limits = config.to_limits()

        assert isinstance(limits, httpx.Limits)
        assert limits.max_connections == 100
        assert limits.max_keepalive_connections == 20
        assert limits.keepalive_expiry == 5.0

    def test_to_limits_edge_cases(self):
        """测试边界值转换."""
        # 最小值
        config = ConnectionPoolConfig(
            max_connections=1,
            max_keepalive_connections=0,
            keepalive_expiry=0.1,
            http2=False,
            timeout=1.0
        )
        limits = config.to_limits()
        assert limits.max_connections == 1
        assert limits.max_keepalive_connections == 0
        assert limits.keepalive_expiry == 0.1

        # 最大值
        config = ConnectionPoolConfig(
            max_connections=1000,
            max_keepalive_connections=500,
            keepalive_expiry=300.0,
            http2=True,
            timeout=300.0
        )
        limits = config.to_limits()
        assert limits.max_connections == 1000
        assert limits.max_keepalive_connections == 500
        assert limits.keepalive_expiry == 300.0

    def test_timeout_parameter(self):
        """测试 timeout 参数传递."""
        # 默认 timeout
        config1 = ConnectionPoolConfig.from_env()
        assert config1.timeout == 30.0

        # 自定义 timeout
        config2 = ConnectionPoolConfig.from_env(timeout=120.0)
        assert config2.timeout == 120.0
