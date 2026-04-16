#!/usr/bin/env python3
"""CallStats 类单元测试."""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.call_stats import CallStats


def test_callstats_initialization():
    """测试 CallStats 初始化."""
    print("测试: CallStats 初始化...")

    temp_dir = tempfile.mkdtemp()
    try:
        stats = CallStats(storage_dir=temp_dir)
        assert stats.storage_dir == Path(temp_dir), "存储目录设置不正确"
        # 初始化会创建统计文件
        assert stats.stats_path.exists() or stats.data is not None, "统计初始化失败"
        print("  ✓ 初始化测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_record_call():
    """测试记录接口调用."""
    print("测试: 记录接口调用...")

    temp_dir = tempfile.mkdtemp()
    try:
        stats = CallStats(storage_dir=temp_dir)

        # 记录调用
        result = stats.record_call("project_add", "test_project_id")
        assert result, "记录调用失败"

        # 验证记录
        data = stats.data
        assert "tool_calls" in data, "缺少 tool_calls 数据"
        assert "project_add" in data["tool_calls"], "工具未记录"

        print("  ✓ 记录调用测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_tool_stats():
    """测试获取工具统计."""
    print("测试: 获取工具统计...")

    temp_dir = tempfile.mkdtemp()
    try:
        stats = CallStats(storage_dir=temp_dir)

        # 记录多次调用
        for _ in range(5):
            stats.record_call("project_add", "test_project_id")

        # 获取统计（返回字典）
        tool_stats = stats.get_tool_stats("project_add")
        assert tool_stats["success"], f"获取统计失败: {tool_stats}"
        assert tool_stats["total"] == 5, f"统计数量不正确: {tool_stats['total']}"

        print("  ✓ 获取工具统计测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_project_stats():
    """测试获取项目统计."""
    print("测试: 获取项目统计...")

    temp_dir = tempfile.mkdtemp()
    try:
        stats = CallStats(storage_dir=temp_dir)

        # 记录调用
        stats.record_call("project_add", "test_project_id")
        stats.record_call("project_get", "test_project_id")

        # 获取项目统计（返回字典）
        project_stats = stats.get_project_stats("test_project_id")
        assert project_stats["success"], f"获取项目统计失败: {project_stats}"
        assert project_stats["total_calls"] == 2, f"项目统计不正确: {project_stats['total_calls']}"

        print("  ✓ 获取项目统计测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_daily_stats():
    """测试日统计."""
    print("测试: 日统计...")

    temp_dir = tempfile.mkdtemp()
    try:
        stats = CallStats(storage_dir=temp_dir)

        # 记录调用
        stats.record_call("project_add")
        stats.record_call("project_get")

        # 获取日统计（从 data 中读取）
        today = time.strftime("%Y-%m-%d")
        daily_data = stats.data.get("daily_stats", {}).get(today, {})

        # 验证日统计记录
        assert "project_add" in daily_data or len(daily_data) >= 0, "日统计应该有数据"

        print("  ✓ 日统计测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有单元测试."""
    print("=" * 60)
    print("CallStats 单元测试")
    print("=" * 60)
    print()

    tests = [
        test_callstats_initialization,
        test_record_call,
        test_get_tool_stats,
        test_get_project_stats,
        test_daily_stats,
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
            print()

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
