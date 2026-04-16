#!/usr/bin/env python3
"""MCP 资源端到端测试."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_server.guidelines import _build_guidelines_content, _build_chinese_guidelines, _build_english_guidelines


def test_guidelines_chinese():
    """测试中文指南资源."""
    print("测试: 中文指南资源...")

    guidelines = _build_chinese_guidelines()

    # 验证基本结构
    assert "version" in guidelines, "缺少 version 字段"
    assert "language" in guidelines, "缺少 language 字段"
    assert guidelines["language"] == "zh", "语言应该为 zh"
    assert "guidelines" in guidelines, "缺少 guidelines 内容"

    # 验证指南内容
    g = guidelines["guidelines"]
    assert "project_naming" in g, "缺少 project_naming 部分"
    assert "groups" in g, "缺少 groups 部分"
    assert "tag_standards" in g, "缺少 tag_standards 部分"
    assert "memory_workflow" in g, "缺少 memory_workflow 部分"
    assert "best_practices" in g, "缺少 best_practices 部分"

    print("  ✓ 中文指南资源测试通过")


def test_guidelines_english():
    """测试英文指南资源."""
    print("测试: 英文指南资源...")

    guidelines = _build_english_guidelines()

    # 验证基本结构
    assert "version" in guidelines, "缺少 version 字段"
    assert "language" in guidelines, "缺少 language 字段"
    assert guidelines["language"] == "en", "语言应该为 en"
    assert "guidelines" in guidelines, "缺少 guidelines 内容"

    print("  ✓ 英文指南资源测试通过")


def test_guidelines_content_builder():
    """测试指南内容构建器."""
    print("测试: 指南内容构建器...")

    # 测试中文
    zh = _build_guidelines_content("zh")
    assert zh["language"] == "zh", "应该返回中文指南"

    # 测试英文
    en = _build_guidelines_content("en")
    assert en["language"] == "en", "应该返回英文指南"

    # 测试默认（非 en 返回中文）
    default = _build_guidelines_content("fr")
    assert default["language"] == "zh", "非 en 语言应该默认返回中文"

    print("  ✓ 指南内容构建器测试通过")


def test_guidelines_structure():
    """测试指南结构完整性."""
    print("测试: 指南结构完整性...")

    guidelines = _build_chinese_guidelines()
    g = guidelines["guidelines"]

    # 验证 project_naming 结构
    pn = g["project_naming"]
    assert "title" in pn, "project_naming 缺少 title"
    assert "priority" in pn, "project_naming 缺少 priority"
    assert "workflow" in pn, "project_naming 缺少 workflow"
    assert len(pn["workflow"]) > 0, "workflow 不应该为空"

    # 验证 groups 结构
    groups = g["groups"]
    assert "groups_list" in groups, "groups 缺少 groups_list"
    assert len(groups["groups_list"]) == 4, "应该有 4 个分组"

    # 验证 tag_standards 结构
    ts = g["tag_standards"]
    assert "standard_tags" in ts, "tag_standards 缺少 standard_tags"
    assert len(ts["standard_tags"]) > 0, "standard_tags 不应该为空"

    # 验证 memory_workflow 结构
    mw = g["memory_workflow"]
    assert "query_flow" in mw, "memory_workflow 缺少 query_flow"
    assert "recording_guide" in mw, "memory_workflow 缺少 recording_guide"
    assert "cleanup" in mw, "memory_workflow 缺少 cleanup"

    print("  ✓ 指南结构完整性测试通过")


def run_all_tests():
    """运行所有资源测试."""
    print("=" * 60)
    print("MCP 资源端到端测试")
    print("=" * 60)
    print()

    tests = [
        test_guidelines_chinese,
        test_guidelines_english,
        test_guidelines_content_builder,
        test_guidelines_structure,
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
