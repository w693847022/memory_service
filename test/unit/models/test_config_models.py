"""Unit tests for config models."""

import pytest
import os
from pathlib import Path
import importlib.util

# Load config module directly to avoid __init__.py import errors
_config_path = Path(__file__).parent.parent.parent.parent / "src" / "models" / "config.py"
_spec = importlib.util.spec_from_file_location("config", _config_path)
if _spec and _spec.loader:
    config = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(config)

    ServiceConfig = config.ServiceConfig
    McpConfig = config.McpConfig
    CacheConfig = config.CacheConfig
    HttpPoolConfig = config.HttpPoolConfig
    UnifiedGroupConfigData = config.UnifiedGroupConfigData
    GroupsConfigData = config.GroupsConfigData
    Settings = config.Settings
    SettingsLoader = config.SettingsLoader
    PaginationResult = config.PaginationResult
    get_settings = config.get_settings


class TestServiceConfig:
    """Test ServiceConfig model."""

    def test_default_values(self):
        config = ServiceConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.log_level == "INFO"

    def test_custom_values(self):
        config = ServiceConfig(host="localhost", port=9000, log_level="DEBUG")
        assert config.host == "localhost"
        assert config.port == 9000
        assert config.log_level == "DEBUG"


class TestMcpConfig:
    """Test McpConfig model."""

    def test_has_transport_field(self):
        config = McpConfig()
        assert config.transport == "stdio"

    def test_custom_transport(self):
        config = McpConfig(transport="sse", port=9000)
        assert config.transport == "sse"
        assert config.port == 9000


class TestCacheConfig:
    """Test CacheConfig model."""

    def test_default_values(self):
        config = CacheConfig()
        assert config.l1.ttl == 60
        assert config.l1.maxsize == 20
        assert config.l2.ttl == 600
        assert config.l2.maxsize == 100
        assert config.l3.maxsize == 1000
        assert config.hot_threshold == 10
        assert config.promotion_enabled is True


class TestHttpPoolConfig:
    """Test HttpPoolConfig model."""

    def test_default_values(self):
        config = HttpPoolConfig()
        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.http2 is False
        assert config.timeout == 30.0

    def test_from_env(self):
        os.environ["BUSINESS_API_MAX_CONNECTIONS"] = "200"
        config = HttpPoolConfig.from_env()
        assert config.max_connections == 200
        del os.environ["BUSINESS_API_MAX_CONNECTIONS"]


class TestUnifiedGroupConfigData:
    """Test UnifiedGroupConfigData model."""

    def test_default_values(self):
        config = UnifiedGroupConfigData()
        assert config.content_max_bytes == 4000
        assert config.summary_max_bytes == 90
        assert config.allow_related is False
        assert config.max_tags == 2
        assert config.description == ""


class TestSettings:
    """Test Settings model."""

    def test_default_values(self):
        settings = Settings()
        assert settings.mcp.transport == "stdio"
        assert settings.fastapi.port == 8000  # FastApiConfig inherits from ServiceConfig with port=8000
        assert settings.business.port == 8000
        assert settings.cache.l1.ttl == 60
        assert settings.groups.features.content_max_bytes == 4000
        assert settings.initial_tags == []
        assert settings.default_related_rules == {}

    def test_custom_initial_tags(self):
        settings = Settings(initial_tags=["custom-tag", "ops"])
        assert settings.initial_tags == ["custom-tag", "ops"]

    def test_custom_default_related_rules(self):
        rules = {"features": ["notes"], "fixes": ["features"]}
        settings = Settings(default_related_rules=rules)
        assert settings.default_related_rules == rules


class TestSettingsLoader:
    """Test SettingsLoader."""

    def test_singleton_pattern(self):
        SettingsLoader._instance = None  # Reset
        settings1 = SettingsLoader.load()
        settings2 = SettingsLoader.get_settings()
        assert settings1 is settings2

    def test_reload(self):
        SettingsLoader._instance = None  # Reset
        settings1 = SettingsLoader.load()
        settings2 = SettingsLoader.reload()
        assert settings1 is not settings2

    def test_fallback_when_no_config(self):
        SettingsLoader._instance = None  # Reset
        settings = SettingsLoader.load(Path("/nonexistent/path.yaml"))
        # Should use defaults
        assert settings.mcp.port == 8000

    def test_load_initial_tags_and_related_rules_from_yaml(self, tmp_path):
        yaml_content = """
groups:
  features:
    content_max_bytes: 1000
    summary_max_bytes: 50
    allow_related: true
    allowed_related_to:
      - "notes"
    enable_status: true
    enable_severity: false
    status_values:
      - "pending"
      - "completed"
    severity_values: []
    required_fields:
      - "content"
      - "summary"
      - "status"
    max_tags: 2
  fixes:
    content_max_bytes: 1000
    summary_max_bytes: 50
    allow_related: true
    allowed_related_to:
      - "features"
    enable_status: true
    enable_severity: true
    status_values:
      - "pending"
      - "completed"
    severity_values:
      - "high"
      - "low"
    required_fields:
      - "content"
      - "summary"
      - "status"
      - "severity"
    max_tags: 2
  notes:
    content_max_bytes: 500
    summary_max_bytes: 50
    allow_related: false
    allowed_related_to: []
    enable_status: false
    enable_severity: false
    status_values: []
    severity_values: []
    required_fields:
      - "content"
      - "summary"
    max_tags: 5
  standards:
    content_max_bytes: 1000
    summary_max_bytes: 50
    allow_related: true
    allowed_related_to:
      - "notes"
    enable_status: false
    enable_severity: false
    status_values: []
    severity_values: []
    required_fields:
      - "content"
      - "summary"
    max_tags: 2
initial_tags:
  - "custom-tag"
  - "ops"
default_related_rules:
  features:
    - "notes"
  fixes:
    - "features"
"""
        yaml_path = tmp_path / "test_service.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        SettingsLoader._instance = None  # Reset
        settings = SettingsLoader.reload(yaml_path)

        assert settings.initial_tags == ["custom-tag", "ops"]
        assert settings.default_related_rules == {
            "features": ["notes"],
            "fixes": ["features"],
        }
        SettingsLoader._instance = None  # Reset


class TestPaginationResult:
    """Test PaginationResult model."""

    def test_valid_pagination(self):
        result = PaginationResult(
            items=[1, 2, 3],
            pagination_meta={"page": 1, "size": 10},
            filtered_total=100
        )
        assert len(result.items) == 3
        assert result.filtered_total == 100
