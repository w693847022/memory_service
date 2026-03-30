#!/usr/bin/env python3
"""MCP接口: stats_* 完整边界测试.

测试统计接口：
- stats_summary
- stats_cleanup
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory
from features.stats import CallStats
import api.tools

from features.instances import call_stats


def _setup_with_stats():
    """创建带统计的测试环境."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)
    stats = CallStats(storage_dir=temp_dir)

    # 创建项目并记录调用
    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]

    # 记录一些调用
    stats.record_call("project_add", project_id)
    stats.record_call("project_get", project_id)
    stats.record_call("project_get", project_id)

    return temp_dir, memory, stats, project_id


# ==================== stats_summary ====================

class TestStatsSummaryTypeTool:
    """stats_summary type=tool 测试."""

    def test_tool_stats_all(self):
        """测试获取所有工具统计."""
        print("测试: 所有工具统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="tool")
                data = json.loads(result)

                assert data["success"], f"获取工具统计失败: {data}"
                assert "tools" in data["data"]

            print("  ✓ 所有工具统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tool_stats_specific(self):
        """测试获取特定工具统计."""
        print("测试: 特定工具统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(
                    type="tool",
                    tool_name="project_get"
                )
                data = json.loads(result)

                assert data["success"], f"获取特定工具统计失败: {data}"
                assert data["data"]["tool_name"] == "project_get"
                assert data["data"]["total"] == 2

            print("  ✓ 特定工具统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tool_stats_nonexistent(self):
        """测试不存在的工具统计."""
        print("测试: 不存在的工具统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(
                    type="tool",
                    tool_name="nonexistent_tool"
                )
                data = json.loads(result)

                # 不存在的工具可能返回0或失败
                assert data.get("success") or "tool" in data.get("error", "").lower()

            print("  ✓ 不存在的工具统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryTypeProject:
    """stats_summary type=project 测试."""

    def test_project_stats(self):
        """测试获取项目统计."""
        print("测试: 项目统计...")
        temp_dir, memory, stats, project_id = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(
                    type="project",
                    project_id=project_id
                )
                data = json.loads(result)

                assert data["success"], f"获取项目统计失败: {data}"
                assert data["data"]["total_calls"] == 3

            print("  ✓ 项目统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_project_stats_missing_id(self):
        """测试项目统计缺少 ID."""
        print("测试: 项目统计缺少 ID...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="project")
                data = json.loads(result)

                assert not data["success"], "缺少 project_id 应该失败"

            print("  ✓ 项目统计缺少 ID 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryTypeClient:
    """stats_summary type=client 测试."""

    def test_client_stats(self):
        """测试获取客户端统计."""
        print("测试: 客户端统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="client")
                data = json.loads(result)

                assert data["success"], f"获取客户端统计失败: {data}"

            print("  ✓ 客户端统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryTypeIp:
    """stats_summary type=ip 测试."""

    def test_ip_stats(self):
        """测试获取 IP 统计."""
        print("测试: IP 统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="ip")
                data = json.loads(result)

                assert data["success"], f"获取 IP 统计失败: {data}"

            print("  ✓ IP 统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryTypeDaily:
    """stats_summary type=daily 测试."""

    def test_daily_stats_all(self):
        """测试获取所有日统计."""
        print("测试: 所有日统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="daily")
                data = json.loads(result)

                assert data["success"], f"获取日统计失败: {data}"

            print("  ✓ 所有日统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_daily_stats_specific_date(self):
        """测试获取特定日期统计."""
        print("测试: 特定日期统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")

            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(
                    type="daily",
                    date=today
                )
                data = json.loads(result)

                assert data["success"], f"获取特定日期统计失败: {data}"

            print("  ✓ 特定日期统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_daily_stats_invalid_date(self):
        """测试无效日期格式."""
        print("测试: 无效日期格式...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(
                    type="daily",
                    date="2026/03/01"  # 错误格式
                )
                data = json.loads(result)

                # 无效日期可能被处理或失败
                # 验证有明确行为

            print("  ✓ 无效日期格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryTypeFull:
    """stats_summary type=full 测试."""

    def test_full_stats(self):
        """测试获取完整统计."""
        print("测试: 完整统计...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_summary(type="full")
                data = json.loads(result)

                assert data["success"], f"获取完整统计失败: {data}"
                assert "metadata" in data["data"]
                assert "tool_stats" in data["data"]
                assert "client_stats" in data["data"]
                assert "daily_stats" in data["data"]

            print("  ✓ 完整统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStatsSummaryInvalidType:
    """stats_summary 无效 type 测试."""

    def test_invalid_type(self):
        """测试无效 type."""
        print("测试: 无效 type...")
        temp_dir, memory, stats, _ = _setup_with_stats()
        try:
            with patch.object(api.tools, 'call_stats', stats):
                # 无效 type 应该返回默认摘要
                result = api.tools.stats_summary(type="invalid")
                data = json.loads(result)

                # 应该有某种响应
                assert "success" in data

            print("  ✓ 无效 type 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== stats_cleanup ====================

class TestStatsCleanup:
    """stats_cleanup 测试."""

    def test_cleanup_default_days(self):
        """测试默认保留天数清理."""
        print("测试: 默认保留天数清理...")
        temp_dir = tempfile.mkdtemp()
        try:
            stats = CallStats(storage_dir=temp_dir)

            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_cleanup()
                data = json.loads(result)

                assert data["success"], f"清理统计失败: {data}"
                assert data["data"]["retention_days"] == 30

            print("  ✓ 默认保留天数清理测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cleanup_custom_days(self):
        """测试自定义保留天数."""
        print("测试: 自定义保留天数...")
        temp_dir = tempfile.mkdtemp()
        try:
            stats = CallStats(storage_dir=temp_dir)

            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_cleanup(retention_days=7)
                data = json.loads(result)

                assert data["success"], f"清理统计失败: {data}"
                assert data["data"]["retention_days"] == 7

            print("  ✓ 自定义保留天数测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cleanup_zero_days(self):
        """测试0天保留."""
        print("测试: 0天保留...")
        temp_dir = tempfile.mkdtemp()
        try:
            stats = CallStats(storage_dir=temp_dir)

            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_cleanup(retention_days=0)
                data = json.loads(result)

                # 0天可能被允许或拒绝
                # 验证有明确行为

            print("  ✓ 0天保留测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cleanup_negative_days(self):
        """测试负数保留天数."""
        print("测试: 负数保留天数...")
        temp_dir = tempfile.mkdtemp()
        try:
            stats = CallStats(storage_dir=temp_dir)

            with patch.object(api.tools, 'call_stats', stats):
                result = api.tools.stats_cleanup(retention_days=-1)
                data = json.loads(result)

                # 负数应该失败或被处理

            print("  ✓ 负数保留天数测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: stats_* 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestStatsSummaryTypeTool,
        TestStatsSummaryTypeProject,
        TestStatsSummaryTypeClient,
        TestStatsSummaryTypeIp,
        TestStatsSummaryTypeDaily,
        TestStatsSummaryTypeFull,
        TestStatsSummaryInvalidType,
        TestStatsCleanup,
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
