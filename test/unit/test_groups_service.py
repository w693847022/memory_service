#!/usr/bin/env python3
"""GroupsService 单元测试."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.groups_service import GroupsService
from src.models.group import UnifiedGroupConfig, DEFAULT_GROUP_CONFIGS


def test_validate_tags_count_within_limit():
    """测试标签数量在限制内."""
    print("测试: 标签数量在限制内...")

    config = UnifiedGroupConfig(max_tags=2)

    # 测试2个标签（等于限制）
    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2"], config)
    assert is_valid, f"2个标签应该通过验证: {error}"
    assert error is None, "错误消息应该为空"

    # 测试1个标签（少于限制）
    is_valid, error = GroupsService.validate_tags_count(["tag1"], config)
    assert is_valid, f"1个标签应该通过验证: {error}"
    assert error is None, "错误消息应该为空"

    print("  ✓ 标签数量在限制内测试通过")


def test_validate_tags_count_exceeds_limit():
    """测试标签数量超过限制."""
    print("测试: 标签数量超过限制...")

    config = UnifiedGroupConfig(max_tags=2)

    # 测试3个标签（超过限制）
    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2", "tag3"], config)
    assert not is_valid, "3个标签应该验证失败"
    assert "标签数量超限" in error, f"错误消息应该包含超限提示: {error}"
    assert "当前 3 个" in error, f"错误消息应该包含当前数量: {error}"
    assert "最大允许 2 个" in error, f"错误消息应该包含最大限制: {error}"

    # 测试5个标签（远超限制）
    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2", "tag3", "tag4", "tag5"], config)
    assert not is_valid, "5个标签应该验证失败"
    assert "标签数量超限" in error, f"错误消息应该包含超限提示: {error}"
    assert "当前 5 个" in error, f"错误消息应该包含当前数量: {error}"

    print("  ✓ 标签数量超过限制测试通过")


def test_validate_tags_count_empty_list():
    """测试空标签列表."""
    print("测试: 空标签列表...")

    config = UnifiedGroupConfig(max_tags=2)

    # 测试空列表
    is_valid, error = GroupsService.validate_tags_count([], config)
    assert is_valid, f"空标签列表应该通过验证: {error}"
    assert error is None, "错误消息应该为空"

    print("  ✓ 空标签列表测试通过")


def test_validate_tags_count_boundary_zero():
    """测试边界值：max_tags=0."""
    print("测试: 边界值 max_tags=0...")

    config = UnifiedGroupConfig(max_tags=0)

    # 测试0个标签（应该通过）
    is_valid, error = GroupsService.validate_tags_count([], config)
    assert is_valid, f"0个标签应该通过验证（max_tags=0）: {error}"

    # 测试1个标签（应该失败）
    is_valid, error = GroupsService.validate_tags_count(["tag1"], config)
    assert not is_valid, "1个标签应该验证失败（max_tags=0）"
    assert "标签数量超限" in error, f"错误消息应该包含超限提示: {error}"

    print("  ✓ 边界值 max_tags=0 测试通过")


def test_validate_tags_count_boundary_one():
    """测试边界值：max_tags=1."""
    print("测试: 边界值 max_tags=1...")

    config = UnifiedGroupConfig(max_tags=1)

    # 测试1个标签（应该通过）
    is_valid, error = GroupsService.validate_tags_count(["tag1"], config)
    assert is_valid, f"1个标签应该通过验证（max_tags=1）: {error}"

    # 测试2个标签（应该失败）
    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2"], config)
    assert not is_valid, "2个标签应该验证失败（max_tags=1）"
    assert "标签数量超限" in error, f"错误消息应该包含超限提示: {error}"

    print("  ✓ 边界值 max_tags=1 测试通过")


def test_validate_tags_count_custom_config():
    """测试自定义配置."""
    print("测试: 自定义配置...")

    # 测试较大的限制值
    config = UnifiedGroupConfig(max_tags=10)

    is_valid, error = GroupsService.validate_tags_count(
        ["tag1", "tag2", "tag3", "tag4", "tag5"], config
    )
    assert is_valid, f"5个标签应该通过验证（max_tags=10）: {error}"

    is_valid, error = GroupsService.validate_tags_count(
        ["tag" + str(i) for i in range(11)], config
    )
    assert not is_valid, "11个标签应该验证失败（max_tags=10）"

    print("  ✓ 自定义配置测试通过")


def test_validate_tags_count_default_config():
    """测试默认配置."""
    print("测试: 默认配置...")

    # 使用默认配置（max_tags=2）
    config = UnifiedGroupConfig()

    # 测试默认值应该是2
    assert config.max_tags == 2, f"默认 max_tags 应该是2，实际是 {config.max_tags}"

    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2"], config)
    assert is_valid, f"2个标签应该通过默认配置验证: {error}"

    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2", "tag3"], config)
    assert not is_valid, "3个标签应该被默认配置拒绝"

    print("  ✓ 默认配置测试通过")


def test_validate_tags_count_none_config():
    """测试 None 配置（使用默认值）."""
    print("测试: None 配置...")

    # 传入 None 配置
    is_valid, error = GroupsService.validate_tags_count(["tag1"], None)
    assert is_valid, f"1个标签应该通过验证（None配置）: {error}"

    # None 配置应该使用默认值2
    is_valid, error = GroupsService.validate_tags_count(["tag1", "tag2", "tag3"], None)
    assert not is_valid, "3个标签应该被 None 配置拒绝（默认max_tags=2）"

    print("  ✓ None 配置测试通过")


def test_default_group_configs_have_max_tags():
    """测试所有默认组配置都有 max_tags 字段."""
    print("测试: 默认组配置包含 max_tags...")

    for group_name, group_config in DEFAULT_GROUP_CONFIGS.items():
        assert "max_tags" in group_config, f"{group_name} 缺少 max_tags 字段"
        assert group_config["max_tags"] == 2, f"{group_name} 的 max_tags 应该是2"
        print(f"  ✓ {group_name}: max_tags={group_config['max_tags']}")

    print("  ✓ 默认组配置包含 max_tags 测试通过")


def test_unified_group_config_max_tags_field():
    """测试 UnifiedGroupConfig 的 max_tags 字段."""
    print("测试: UnifiedGroupConfig max_tags 字段...")

    # 测试默认值
    config = UnifiedGroupConfig()
    assert config.max_tags == 2, f"默认 max_tags 应该是2，实际是 {config.max_tags}"

    # 测试自定义值
    config = UnifiedGroupConfig(max_tags=5)
    assert config.max_tags == 5, f"自定义 max_tags 应该是5，实际是 {config.max_tags}"

    # 测试边界值
    config = UnifiedGroupConfig(max_tags=0)
    assert config.max_tags == 0, f"max_tags=0 应该被允许"

    print("  ✓ UnifiedGroupConfig max_tags 字段测试通过")


def test_unified_group_config_from_dict_with_max_tags():
    """测试 UnifiedGroupConfig.from_dict 加载 max_tags."""
    print("测试: UnifiedGroupConfig.from_dict 加载 max_tags...")

    # 测试加载 max_tags
    config = UnifiedGroupConfig.from_dict({"max_tags": 10})
    assert config.max_tags == 10, f"from_dict 应该加载 max_tags=10，实际是 {config.max_tags}"

    # 测试默认值（不提供 max_tags）
    config = UnifiedGroupConfig.from_dict({})
    assert config.max_tags == 2, f"from_dict 默认 max_tags 应该是2，实际是 {config.max_tags}"

    # 测试完整的配置
    full_config = {
        "content_max_bytes": 4000,
        "summary_max_bytes": 90,
        "allow_related": True,
        "max_tags": 5
    }
    config = UnifiedGroupConfig.from_dict(full_config)
    assert config.max_tags == 5, f"from_dict 应该加载 max_tags=5"

    print("  ✓ UnifiedGroupConfig.from_dict 加载 max_tags 测试通过")
