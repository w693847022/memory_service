#!/usr/bin/env python3
"""ProjectService 关联目标校验单元测试 - fix_20260512_2.

测试 _validate_related_targets 方法的存在性和自引用校验逻辑。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.business.project_service import ProjectService


# ==================== Fixtures ====================

def create_mock_storage():
    """创建模拟的 storage 对象."""
    return MagicMock()


def create_project_service(storage=None):
    """创建 ProjectService 实例."""
    if storage is None:
        storage = create_mock_storage()
    return ProjectService(storage)


def create_mock_project_data(items_map=None):
    """创建模拟的 ProjectData 对象.

    Args:
        items_map: dict, 格式为 {group: {item_id: mock_item}}
    """
    project_data = MagicMock()

    def mock_get_item(group, item_id):
        group_items = (items_map or {}).get(group, {})
        return group_items.get(item_id)

    project_data.get_item = mock_get_item
    return project_data


# ==================== 存在性校验测试 ====================

def test_related_none_passes():
    """测试 related_dict 为 None 时直接通过."""
    service = create_project_service()
    project_data = create_mock_project_data()

    is_valid, error_msg = service._validate_related_targets(project_data, None)
    assert is_valid is True
    assert error_msg is None


def test_related_empty_dict_passes():
    """测试 related_dict 为空 dict 时直接通过."""
    service = create_project_service()
    project_data = create_mock_project_data()

    is_valid, error_msg = service._validate_related_targets(project_data, {})
    assert is_valid is True
    assert error_msg is None


def test_related_all_targets_exist():
    """测试所有关联目标都存在时通过."""
    service = create_project_service()
    mock_item = MagicMock()
    mock_item.id = "feat_20260501_1"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item}
    })

    related_dict = {"features": ["feat_20260501_1"]}
    is_valid, error_msg = service._validate_related_targets(project_data, related_dict)
    assert is_valid is True
    assert error_msg is None


def test_related_target_not_exist():
    """测试关联目标不存在时失败."""
    service = create_project_service()
    project_data = create_mock_project_data({
        "features": {}  # 空分组
    })

    related_dict = {"features": ["feat_nonexistent_1"]}
    is_valid, error_msg = service._validate_related_targets(project_data, related_dict)
    assert is_valid is False
    assert "关联目标不存在" in error_msg
    assert "feat_nonexistent_1" in error_msg


def test_related_multi_group_some_missing():
    """测试多分组关联，部分目标不存在时失败."""
    service = create_project_service()
    mock_item = MagicMock()
    mock_item.id = "feat_20260501_1"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item},
        "notes": {}  # notes 分组为空
    })

    related_dict = {"features": ["feat_20260501_1"], "notes": ["note_nonexistent_1"]}
    is_valid, error_msg = service._validate_related_targets(project_data, related_dict)
    assert is_valid is False
    assert "关联目标不存在" in error_msg
    assert "note_nonexistent_1" in error_msg


# ==================== 自引用校验测试 ====================

def test_self_reference_rejected():
    """测试关联自身条目时被拒绝."""
    service = create_project_service()
    mock_item = MagicMock()
    mock_item.id = "feat_20260501_1"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item}
    })

    related_dict = {"features": ["feat_20260501_1"]}
    is_valid, error_msg = service._validate_related_targets(
        project_data, related_dict, current_item_id="feat_20260501_1"
    )
    assert is_valid is False
    assert "不能关联自身条目" in error_msg
    assert "feat_20260501_1" in error_msg


def test_reference_other_in_same_group_passes():
    """测试关联同组其他条目时通过."""
    service = create_project_service()
    mock_item1 = MagicMock()
    mock_item1.id = "feat_20260501_1"
    mock_item2 = MagicMock()
    mock_item2.id = "feat_20260501_2"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item1, "feat_20260501_2": mock_item2}
    })

    related_dict = {"features": ["feat_20260501_2"]}
    is_valid, error_msg = service._validate_related_targets(
        project_data, related_dict, current_item_id="feat_20260501_1"
    )
    assert is_valid is True
    assert error_msg is None


def test_no_current_item_id_skips_self_check():
    """测试未传入 current_item_id 时跳过自引用校验（用于 add_item）."""
    service = create_project_service()
    mock_item = MagicMock()
    mock_item.id = "feat_20260501_1"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item}
    })

    related_dict = {"features": ["feat_20260501_1"]}
    # add_item 时 current_item_id=None，不应该报错
    is_valid, error_msg = service._validate_related_targets(
        project_data, related_dict, current_item_id=None
    )
    assert is_valid is True
    assert error_msg is None


# ==================== 边界情况测试 ====================

def test_related_with_empty_item_ids():
    """测试 item_ids 为空列表时通过."""
    service = create_project_service()
    project_data = create_mock_project_data()

    related_dict = {"features": []}
    is_valid, error_msg = service._validate_related_targets(project_data, related_dict)
    assert is_valid is True
    assert error_msg is None


def test_related_multiple_valid_targets():
    """测试多个有效关联目标时通过."""
    service = create_project_service()
    mock_item1 = MagicMock()
    mock_item1.id = "feat_20260501_1"
    mock_item2 = MagicMock()
    mock_item2.id = "note_20260501_1"
    project_data = create_mock_project_data({
        "features": {"feat_20260501_1": mock_item1},
        "notes": {"note_20260501_1": mock_item2}
    })

    related_dict = {"features": ["feat_20260501_1"], "notes": ["note_20260501_1"]}
    is_valid, error_msg = service._validate_related_targets(project_data, related_dict)
    assert is_valid is True
    assert error_msg is None


# ==================== 运行所有测试 ====================

def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("ProjectService 关联目标校验单元测试")
    print("fix_20260512_2 - 测试 _validate_related_targets 方法")
    print("=" * 60)

    tests = [
        ("related None 通过", test_related_none_passes),
        ("related 空 dict 通过", test_related_empty_dict_passes),
        ("所有目标存在", test_related_all_targets_exist),
        ("目标不存在", test_related_target_not_exist),
        ("多分组部分缺失", test_related_multi_group_some_missing),
        ("自引用被拒绝", test_self_reference_rejected),
        ("同组其他条目通过", test_reference_other_in_same_group_passes),
        ("无 current_item_id 跳过自检查", test_no_current_item_id_skips_self_check),
        ("空 item_ids 通过", test_related_with_empty_item_ids),
        ("多个有效目标", test_related_multiple_valid_targets),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"  ✓ {test_name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {test_name} - 失败: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test_name} - 错误: {e}")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
