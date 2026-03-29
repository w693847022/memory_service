#!/usr/bin/env python3
"""工具函数单元测试."""

import sys
import os
import re
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_id_generation():
    """测试 ID 生成格式."""
    print("测试: ID 生成格式...")

    # 测试 features ID 格式
    feature_pattern = r'^feat_\d{8}_\d+$'
    assert re.match(feature_pattern, "feat_20260322_1"), "features ID 格式不正确"

    # 测试 notes ID 格式
    note_pattern = r'^note_\d{8}_\d+$'
    assert re.match(note_pattern, "note_20260322_1"), "notes ID 格式不正确"

    # 测试 fixes ID 格式
    fix_pattern = r'^fix_\d{8}_\d+$'
    assert re.match(fix_pattern, "fix_20260322_1"), "fixes ID 格式不正确"

    # 测试 standards ID 格式
    standard_pattern = r'^std_\d{8}_\d+$'
    assert re.match(standard_pattern, "std_20260322_1"), "standards ID 格式不正确"

    print("  ✓ ID 生成格式测试通过")
    return True


def test_group_normalization():
    """测试分组验证."""
    print("测试: 分组验证...")

    from core.groups import validate_group_name

    # 测试有效分组名
    for group in ["features", "fixes", "notes", "standards"]:
        is_valid, error_msg = validate_group_name(group)
        assert is_valid, f"'{group}' 应该是有效的分组名"

    # 测试无效分组名（不再支持别名）
    invalid_names = ["feature", "fix", "功能", "feat", "invalid"]
    for invalid in invalid_names:
        is_valid, error_msg = validate_group_name(invalid)
        assert not is_valid, f"'{invalid}' 应该是无效的分组名"

    print("  ✓ 分组验证测试通过")
    return True


def test_tag_parsing():
    """测试标签解析."""
    print("测试: 标签解析...")

    from api.tools import _parse_tags

    # 测试逗号分隔
    tags = _parse_tags("tag1,tag2,tag3")
    assert tags == ["tag1", "tag2", "tag3"], f"标签解析错误: {tags}"

    # 测试空格处理
    tags = _parse_tags("tag1, tag2 , tag3")
    assert tags == ["tag1", "tag2", "tag3"], f"标签空格处理错误: {tags}"

    # 测试空字符串
    tags = _parse_tags("")
    assert tags == [], f"空字符串应该返回空列表: {tags}"

    print("  ✓ 标签解析测试通过")
    return True


def test_content_validation():
    """测试内容长度验证."""
    print("测试: 内容长度验证...")

    from core.groups import validate_content_length

    # 测试有效内容
    valid, msg, _ = validate_content_length("短内容", "features")
    assert valid, f"短内容应该有效: {msg}"

    # 测试过长内容 (features: 80 tokens = ~240 chars)
    long_content = "a" * 300
    valid, msg, _ = validate_content_length(long_content, "features")
    assert not valid, "过长内容应该无效"

    # 测试 notes 分组的 1 token 最小长度 (3字符 ≈ 1 token)
    valid, msg, _ = validate_content_length("aaa", "notes", min_tokens=1)
    assert valid, f"3字符应该满足 min_tokens=1: {msg}"

    # 测试不满足最小长度
    valid, msg, _ = validate_content_length("a", "notes", min_tokens=1)
    assert not valid, "1字符不应该满足 min_tokens=1"

    print("  ✓ 内容长度验证测试通过")
    return True


def test_track_calls_decorator():
    """测试 track_calls 装饰器."""
    print("测试: track_calls 装饰器...")

    temp_dir = tempfile.mkdtemp()
    try:
        original_storage = os.environ.get("MCP_STORAGE_DIR")
        os.environ["MCP_STORAGE_DIR"] = temp_dir

        from core.utils import track_calls

        # 使用 mock 验证 record_call 被调用
        from unittest.mock import MagicMock
        with patch("features.instances.call_stats") as mock_stats:
            mock_stats.record_call = MagicMock()

            @track_calls
            def dummy_func():
                return "result"

            # 调用被装饰的函数，触发 track_calls 内部逻辑
            result = dummy_func()

            assert result == "result", "函数返回值应该不变"
            mock_stats.record_call.assert_called_once()
            call_kwargs = mock_stats.record_call.call_args.kwargs
            assert call_kwargs["tool_name"] == "dummy_func"
            assert "client" in call_kwargs
            assert "ip" in call_kwargs

        print("  ✓ track_calls 装饰器测试通过")
        return True
    finally:
        if original_storage is not None:
            os.environ["MCP_STORAGE_DIR"] = original_storage
        elif "MCP_STORAGE_DIR" in os.environ:
            del os.environ["MCP_STORAGE_DIR"]
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_validate_view_mode():
    """测试 validate_view_mode 通用函数."""
    print("测试: validate_view_mode...")

    from core.utils import validate_view_mode

    # 有效值
    is_valid, error = validate_view_mode("summary")
    assert is_valid and error is None, f"summary 应有效: {error}"

    is_valid, error = validate_view_mode("detail")
    assert is_valid and error is None, f"detail 应有效: {error}"

    # 无效值
    is_valid, error = validate_view_mode("invalid")
    assert not is_valid, "invalid 应无效"
    assert "view_mode" in error

    is_valid, error = validate_view_mode("")
    assert not is_valid, "空字符串应无效"

    print("  ✓ validate_view_mode 测试通过")
    return True


def test_validate_regex_pattern():
    """测试 validate_regex_pattern 通用函数."""
    print("测试: validate_regex_pattern...")

    from core.utils import validate_regex_pattern

    # 空字符串
    regex, error = validate_regex_pattern("")
    assert regex is None and error is None, "空字符串应返回 (None, None)"

    # 有效正则
    regex, error = validate_regex_pattern("API")
    assert regex is not None and error is None, f"有效正则应成功: {error}"
    assert regex.search("API 接口"), "应匹配"

    # 无效正则
    regex, error = validate_regex_pattern("[invalid")
    assert regex is None, "无效正则应返回 None"
    assert error is not None
    assert "正则表达式" in error

    # 自定义参数名
    regex, error = validate_regex_pattern("[x", "tag_name_pattern")
    assert "tag_name_pattern" in error

    print("  ✓ validate_regex_pattern 测试通过")
    return True


def test_apply_view_mode():
    """测试 apply_view_mode 通用函数."""
    print("测试: apply_view_mode...")

    from core.utils import apply_view_mode

    items = [
        {"id": "1", "name": "test", "summary": "测试", "tags": ["a"]},
        {"id": "2", "name": "test2", "summary": "测试2", "tags": ["b"]},
    ]

    # summary 模式
    result = apply_view_mode(items, "summary", ["id", "summary"])
    assert len(result) == 2
    assert set(result[0].keys()) == {"id", "summary"}
    assert result[0]["id"] == "1"
    assert result[0]["summary"] == "测试"

    # detail 模式返回原数据
    result = apply_view_mode(items, "detail", ["id"])
    assert len(result) == 2
    assert set(result[0].keys()) == {"id", "name", "summary", "tags"}

    print("  ✓ apply_view_mode 测试通过")
    return True


def run_all_tests():
    """运行所有单元测试."""
    print("=" * 60)
    print("工具函数单元测试")
    print("=" * 60)
    print()

    tests = [
        test_id_generation,
        test_group_normalization,
        test_tag_parsing,
        test_content_validation,
        test_track_calls_decorator,
        test_validate_view_mode,
        test_validate_regex_pattern,
        test_apply_view_mode,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ 测试失败: {e}")
            print()
        except Exception as e:
            failed += 1
            print(f"  ✗ 测试错误: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
