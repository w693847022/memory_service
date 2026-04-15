"""Unit tests for group default getters with external config fallback."""

import sys
from pathlib import Path
import importlib.util

# Ensure project root is on path so src imports work
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

# We must import config *before* group so that group.py sees the same module object
from src.models.config import SettingsLoader, Settings

# Now load group module
from src.models.group import (
    get_default_tags,
    get_default_related_rules,
    DEFAULT_TAGS,
    DEFAULT_RELATED_RULES,
)


class TestGetDefaultTags:
    """Test get_default_tags fallback logic."""

    def test_fallback_to_builtin_when_empty(self):
        SettingsLoader.reload(Path("/nonexistent/path.yaml"))
        tags = get_default_tags()
        assert tags == DEFAULT_TAGS

    def test_uses_external_config_when_set(self):
        custom_tags = ["custom1", "custom2"]
        SettingsLoader._instance = Settings(initial_tags=custom_tags)
        tags = get_default_tags()
        assert tags == custom_tags
        SettingsLoader._instance = None  # Reset


class TestGetDefaultRelatedRules:
    """Test get_default_related_rules fallback logic."""

    def test_fallback_to_builtin_when_empty(self):
        SettingsLoader.reload(Path("/nonexistent/path.yaml"))
        rules = get_default_related_rules()
        assert rules == DEFAULT_RELATED_RULES

    def test_uses_external_config_when_set(self):
        custom_rules = {"features": ["notes"], "fixes": ["features"]}
        SettingsLoader._instance = Settings(default_related_rules=custom_rules)
        rules = get_default_related_rules()
        assert rules == custom_rules
        SettingsLoader._instance = None  # Reset


class TestGetDefaultGroupConfigs:
    """Test get_default_group_configs fallback logic."""

    def test_fallback_has_description(self):
        SettingsLoader.reload(Path("/nonexistent/path.yaml"))
        from src.models.group import get_default_group_configs
        configs = get_default_group_configs()
        for group_name, config in configs.items():
            assert "description" in config, f"{group_name} 缺少 description 字段"
