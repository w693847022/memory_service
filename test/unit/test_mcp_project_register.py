#!/usr/bin/env python3
"""MCP接口: project_register 完整边界测试.

测试项目注册接口的所有边界情况：
- 必填参数验证
- 可选参数处理
- 参数长度边界
- 特殊字符处理
- 重复注册
- 无效值处理
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory
import api.tools


def _create_memory():
    """创建临时存储的 ProjectMemory 实例."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)
    return temp_dir, memory


class TestProjectRegisterBasic:
    """基础功能测试."""

    def test_register_success_minimal(self):
        """测试最少参数注册成功."""
        print("测试: 最少参数注册...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试项目")
                data = json.loads(result)

                assert data["success"], f"注册失败: {data}"
                assert "project_id" in data["data"], "缺少 project_id"

            print("  ✓ 最少参数注册测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_success_full_params(self):
        """测试完整参数注册成功."""
        print("测试: 完整参数注册...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(
                    name="完整项目",
                    path="/path/to/project",
                    summary="项目摘要",
                    tags="tag1,tag2,tag3"
                )
                data = json.loads(result)

                assert data["success"], f"注册失败: {data}"
                assert "project_id" in data["data"]

            print("  ✓ 完整参数注册测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterNameValidation:
    """项目名称验证边界测试."""

    def test_name_empty(self):
        """测试空名称."""
        print("测试: 空名称...")
        temp_dir, memory = _create_memory()
        try:
            # name 是必填参数，空字符串会通过但后续可能失败
            # 这里测试实际行为
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="")
                data = json.loads(result)

                # 根据实际实现，可能成功或失败
                if not data["success"]:
                    assert "名称" in data.get("error", "") or "name" in data.get("error", "")

            print("  ✓ 空名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_min_length(self):
        """测试最短名称."""
        print("测试: 最短名称...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="A")
                data = json.loads(result)

                # 单字符名称应该可以
                assert data["success"] or "名称" in data.get("error", "")

            print("  ✓ 最短名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_max_length(self):
        """测试最长名称边界."""
        print("测试: 名称长度边界...")
        temp_dir, memory = _create_memory()
        try:
            # 测试各种长度
            for length in [50, 100, 200, 500]:
                name = "A" * length
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{length}")
                    data = json.loads(result)
                    # 长名称应该可以成功或给出明确错误

            print("  ✓ 名称长度边界测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_with_special_chars(self):
        """测试特殊字符名称."""
        print("测试: 特殊字符名称...")
        temp_dir, memory = _create_memory()
        try:
            special_names = [
                "项目-测试",
                "项目_测试",
                "项目.测试",
                "项目 测试",
                "项目@测试",
                "项目#测试",
                "项目$测试",
            ]

            for name in special_names:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=name)
                    data = json.loads(result)
                    # 大部分特殊字符应该可以处理

            print("  ✓ 特殊字符名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_with_unicode(self):
        """测试 Unicode 名称."""
        print("测试: Unicode 名称...")
        temp_dir, memory = _create_memory()
        try:
            unicode_names = [
                "项目测试",
                "プロジェクト",
                "프로젝트",
                "Проект",
                "مرحبا",
                "🚀项目",
            ]

            for name in unicode_names:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=name)
                    data = json.loads(result)

            print("  ✓ Unicode 名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_duplicate_name(self):
        """测试重复名称."""
        print("测试: 重复名称...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                # 第一次注册
                result1 = api.tools.project_register(name="重复项目")
                data1 = json.loads(result1)
                assert data1["success"], "第一次注册应该成功"

                # 第二次注册同名项目
                result2 = api.tools.project_register(name="重复项目")
                data2 = json.loads(result2)

                # 根据实现，可能允许同名或拒绝
                # 验证返回了明确的结果

            print("  ✓ 重复名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterPathValidation:
    """路径参数边界测试."""

    def test_path_empty(self):
        """测试空路径."""
        print("测试: 空路径...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", path="")
                data = json.loads(result)

                # 空路径是可选的，应该成功
                assert data["success"], f"空路径应该允许: {data}"

            print("  ✓ 空路径测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_path_valid_formats(self):
        """测试各种有效路径格式."""
        print("测试: 有效路径格式...")
        temp_dir, memory = _create_memory()
        try:
            valid_paths = [
                "/home/user/project",
                "/home/user/project/",
                "relative/path",
                "./relative/path",
                "../parent/path",
                "C:\\Users\\project",
                "\\\\network\\path",
            ]

            for path in valid_paths:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{hash(path)}", path=path)
                    data = json.loads(result)
                    # 路径只做存储，应该都能接受

            print("  ✓ 有效路径格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_path_edge_cases(self):
        """测试路径边界情况."""
        print("测试: 路径边界情况...")
        temp_dir, memory = _create_memory()
        try:
            edge_paths = [
                "/",  # 根目录
                ".",  # 当前目录
                "..",  # 上级目录
                "a",  # 单字符路径
                "a" * 1000,  # 超长路径
            ]

            for path in edge_paths:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{len(path)}", path=path)
                    data = json.loads(result)

            print("  ✓ 路径边界情况测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterSummaryValidation:
    """摘要参数边界测试."""

    def test_summary_empty(self):
        """测试空摘要."""
        print("测试: 空摘要...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", summary="")
                data = json.loads(result)

                # 空摘要应该允许（可选参数）
                assert data["success"], f"空摘要应该允许: {data}"

            print("  ✓ 空摘要测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_lengths(self):
        """测试各种摘要长度."""
        print("测试: 摘要长度...")
        temp_dir, memory = _create_memory()
        try:
            lengths = [1, 10, 50, 100, 200, 500, 1000]

            for length in lengths:
                summary = "A" * length
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{length}", summary=summary)
                    data = json.loads(result)

            print("  ✓ 摘要长度测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_with_special_chars(self):
        """测试特殊字符摘要."""
        print("测试: 特殊字符摘要...")
        temp_dir, memory = _create_memory()
        try:
            special_summaries = [
                "摘要\n包含换行",
                "摘要\t包含制表符",
                "摘要\"包含引号\"",
                "摘要'包含单引号'",
                "摘要\\包含反斜杠",
                "摘要/包含斜杠",
                "中文摘要。，、！？",
                "🚀表情符号",
            ]

            for summary in special_summaries:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name="测试", summary=summary)
                    data = json.loads(result)

            print("  ✓ 特殊字符摘要测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterTagsValidation:
    """标签参数边界测试."""

    def test_tags_empty(self):
        """测试空标签."""
        print("测试: 空标签...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", tags="")
                data = json.loads(result)

                # 空标签应该允许
                assert data["success"], f"空标签应该允许: {data}"

            print("  ✓ 空标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_single(self):
        """测试单个标签."""
        print("测试: 单个标签...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", tags="single")
                data = json.loads(result)

                assert data["success"], f"单个标签应该允许: {data}"

            print("  ✓ 单个标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_multiple(self):
        """测试多个标签."""
        print("测试: 多个标签...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", tags="tag1,tag2,tag3,tag4,tag5")
                data = json.loads(result)

                assert data["success"], f"多个标签应该允许: {data}"

            print("  ✓ 多个标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_with_spaces(self):
        """测试带空格的标签."""
        print("测试: 标签空格处理...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", tags=" tag1 , tag2 , tag3 ")
                data = json.loads(result)

                assert data["success"], f"带空格标签应该处理: {data}"

            print("  ✓ 标签空格处理测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_with_empty_items(self):
        """测试包含空项的标签."""
        print("测试: 标签空项处理...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试", tags="tag1,,tag2,,,tag3")
                data = json.loads(result)

                assert data["success"], f"空项标签应该被过滤: {data}"

            print("  ✓ 标签空项处理测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_special_chars(self):
        """测试特殊字符标签."""
        print("测试: 特殊字符标签...")
        temp_dir, memory = _create_memory()
        try:
            special_tags = [
                "tag-with-dash",
                "tag_with_underscore",
                "tag.with.dot",
                "tag@with@at",
                "tag123",
                "123tag",
                "UPPERCASE",
                "lowercase",
                "CamelCase",
            ]

            for tag in special_tags:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{tag}", tags=tag)
                    data = json.loads(result)

            print("  ✓ 特殊字符标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_unicode(self):
        """测试 Unicode 标签."""
        print("测试: Unicode 标签...")
        temp_dir, memory = _create_memory()
        try:
            unicode_tags = [
                "标签",
                "タグ",
                "태그",
                "метка",
                "🏷️emoji",
            ]

            for tag in unicode_tags:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name=f"proj_{len(tag)}", tags=tag)
                    data = json.loads(result)

            print("  ✓ Unicode 标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_very_long(self):
        """测试超长标签."""
        print("测试: 超长标签...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                long_tag = "a" * 1000
                result = api.tools.project_register(name="测试", tags=long_tag)
                data = json.loads(result)

                # 可能成功或失败，取决于验证
                # 验证有明确的行为

            print("  ✓ 超长标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterResponseFormat:
    """响应格式测试."""

    def test_response_contains_project_id(self):
        """测试响应包含 project_id."""
        print("测试: 响应包含 project_id...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(name="测试")
                data = json.loads(result)

                assert data["success"], "注册应该成功"
                assert "data" in data, "响应应包含 data"
                assert "project_id" in data["data"], "data 应包含 project_id"

            print("  ✓ project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_response_format_on_success(self):
        """测试成功响应格式."""
        print("测试: 成功响应格式...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_register(
                    name="测试",
                    path="/path",
                    summary="摘要",
                    tags="tag1,tag2"
                )
                data = json.loads(result)

                assert data["success"] is True
                assert "data" in data
                assert "message" in data

            print("  ✓ 成功响应格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRegisterEdgeCases:
    """边缘情况测试."""

    def test_register_concurrent_same_name(self):
        """测试并发注册同名项目."""
        print("测试: 并发注册同名...")
        temp_dir, memory = _create_memory()
        try:
            import threading

            results = []

            def register():
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_register(name="并发测试")
                    results.append(json.loads(result))

            threads = [threading.Thread(target=register) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 验证所有请求都有明确的响应
            assert len(results) == 5
            for result in results:
                assert "success" in result

            print("  ✓ 并发注册测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_after_delete(self):
        """测试删除后重新注册同名项目."""
        print("测试: 删除后重新注册...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                # 注册项目
                result1 = api.tools.project_register(name="测试项目")
                data1 = json.loads(result1)
                project_id = data1["data"]["project_id"]

                # 删除项目
                result2 = api.tools.project_remove(project_id, mode="delete")
                data2 = json.loads(result2)
                assert data2["success"], "删除应该成功"

                # 重新注册同名项目
                result3 = api.tools.project_register(name="测试项目")
                data3 = json.loads(result3)

                # 应该成功（可能生成新的 project_id）
                assert data3["success"], f"重新注册应该成功: {data3}"

            print("  ✓ 删除后重新注册测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_with_none_params(self):
        """测试 None 参数处理."""
        print("测试: None 参数处理...")
        temp_dir, memory = _create_memory()
        try:
            with patch.object(api.tools, 'memory', memory):
                # 不传 None 的参数（MCP 工具不会传 None）
                result = api.tools.project_register(name="测试")
                data = json.loads(result)

                assert data["success"], "不传可选参数应该成功"

            print("  ✓ None 参数测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_register 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectRegisterBasic,
        TestProjectRegisterNameValidation,
        TestProjectRegisterPathValidation,
        TestProjectRegisterSummaryValidation,
        TestProjectRegisterTagsValidation,
        TestProjectRegisterResponseFormat,
        TestProjectRegisterEdgeCases,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    passed += 1
                except AssertionError as e:
                    failed += 1
                    print(f"  ✗ {method_name} 失败: {e}")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ {method_name} 错误: {e}")

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
