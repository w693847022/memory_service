#!/usr/bin/env python3
"""MCP 工具层导入测试.

验证 features.tools 模块能够正确导入 memory 和 call_stats 实例。
这确保 MCP 工具层与全局实例层的导入链路正确。
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_features_tools_imports():
    """测试 mcp_server.tools 能够正确导入全局实例.

    这个测试验证导入链路:
    mcp_server/tools/*.py → clients/business_client.py

    如果 business_client 和 tools 的导入路径配置错误，测试将失败。
    """
    print("测试: mcp_server.tools 导入链路...")

    temp_dir = tempfile.mkdtemp()
    try:
        # 临时修改 MCP_STORAGE_DIR 以使用临时目录
        original_storage = os.environ.get("MCP_STORAGE_DIR")
        os.environ["MCP_STORAGE_DIR"] = temp_dir

        # 导入 mcp_server.tools 中的关键函数
        from mcp_server.tools import (
            project_list,
            project_register,
            project_get,
            project_add,
            project_update,
            project_delete,
            project_groups_list,
            project_tags_info,
            project_item_tag_manage,
            tag_register,
            tag_update,
            tag_delete,
            tag_merge,
        )

        # 验证导入的工具函数都是可调用的
        assert callable(project_list), "project_list 应该可调用"
        assert callable(project_register), "project_register 应该可调用"
        assert callable(project_get), "project_get 应该可调用"
        assert callable(project_add), "project_add 应该可调用"
        assert callable(project_update), "project_update 应该可调用"
        assert callable(project_delete), "project_delete 应该可调用"
        assert callable(project_groups_list), "project_groups_list 应该可调用"
        assert callable(project_tags_info), "project_tags_info 应该可调用"
        assert callable(project_item_tag_manage), "project_item_tag_manage 应该可调用"
        assert callable(tag_register), "tag_register 应该可调用"
        assert callable(tag_update), "tag_update 应该可调用"
        assert callable(tag_delete), "tag_delete 应该可调用"
        assert callable(tag_merge), "tag_merge 应该可调用"

        print("  ✓ mcp_server.tools 导入链路测试通过")
    finally:
        if original_storage is not None:
            os.environ["MCP_STORAGE_DIR"] = original_storage
        elif "MCP_STORAGE_DIR" in os.environ:
            del os.environ["MCP_STORAGE_DIR"]
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_instances_imports_memory_and_call_stats():
    """测试 business 层能正确提供 Storage 和 CallStats."""
    print("测试: business 层实例提供...")

    temp_dir = tempfile.mkdtemp()
    try:
        original_storage = os.environ.get("MCP_STORAGE_DIR")
        os.environ["MCP_STORAGE_DIR"] = temp_dir

        from business.storage import Storage
        from business.call_stats import CallStats

        # 创建实例验证它们可以正常初始化
        storage = Storage(storage_dir=temp_dir)
        call_stats = CallStats(storage_dir=temp_dir)

        # 验证 storage 有正确的方法
        assert hasattr(storage, "get_project_data"), "storage 应该有 get_project_data 方法"
        assert hasattr(storage, "save_project_data"), "storage 应该有 save_project_data 方法"

        # 验证 call_stats 有正确的方法
        assert hasattr(call_stats, "record_call"), "call_stats 应该有 record_call 方法"
        assert hasattr(call_stats, "get_tool_stats"), "call_stats 应该有 get_tool_stats 方法"

        print("  ✓ business 层实例测试通过")
    finally:
        if original_storage is not None:
            os.environ["MCP_STORAGE_DIR"] = original_storage
        elif "MCP_STORAGE_DIR" in os.environ:
            del os.environ["MCP_STORAGE_DIR"]
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有导入测试."""
    print("=" * 60)
    print("MCP 工具层导入测试")
    print("=" * 60)
    print()

    tests = [
        test_instances_imports_memory_and_call_stats,
        test_features_tools_imports,
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
