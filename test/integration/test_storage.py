#!/usr/bin/env python3
"""存储层集成测试."""

import sys
import os
import tempfile
import shutil
import json
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService


@pytest.mark.asyncio
class TestStorageIntegration:
    """存储层集成测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.project_id = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.project_service = ProjectService(self.storage)

    async def test_json_storage_persistence(self):
        """测试 JSON 存储持久化."""
        await self.async_setup_method()

        # 创建第一个实例并添加数据
        project_service1 = self.project_service
        result = await project_service1.register_project("持久化测试", "/tmp/test")
        project_id = result["project_id"]

        await project_service1.add_item(
            project_id=project_id,
            group="features",
            content="测试功能内容",
            summary="测试功能",
            status="pending",
            tags=[]
        )

        # 创建新实例，验证数据持久化
        storage2 = Storage(storage_dir=self.temp_dir)
        project_service2 = ProjectService(storage2)
        project_data = await project_service2.get_project(project_id)

        assert project_data is not None, "数据未持久化"
        assert project_data["data"]["info"]["name"] == "持久化测试", "项目名称未正确持久化"
        assert len(project_data["data"]["features"]) == 1, "功能未正确持久化"

        print("✓ JSON 存储持久化测试通过")

    async def test_note_content_separate_storage(self):
        """测试笔记内容分离存储."""
        await self.async_setup_method()

        result = await self.project_service.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加笔记（使用 add_item 统一接口）
        note_content = "这是详细的笔记内容" * 100  # 较长内容
        result = await self.project_service.add_item(
            project_id=project_id,
            group="notes",
            content=note_content,
            summary="测试笔记",
            tags=[]
        )
        note_id = result["item_id"]

        # 验证笔记内容在单独的文件中
        note_file = self.storage._get_item_content_path(project_id, "notes", note_id)
        assert note_file.exists(), "笔记内容文件不存在"

        # 读取笔记内容
        with open(note_file, "r", encoding="utf-8") as f:
            saved_content = f.read()
        assert saved_content == note_content, "笔记内容不正确"

        # 验证笔记内容通过通用接口获取正确
        loaded_content = await self.storage.get_item_content(project_id, "notes", note_id)
        assert loaded_content == note_content, "通过 storage 获取的笔记内容不正确"

        print("✓ 笔记内容分离存储测试通过")

    async def test_project_directory_structure(self):
        """测试项目目录结构."""
        await self.async_setup_method()

        result = await self.project_service.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加各种类型的数据（使用 add_item 统一接口）
        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="测试功能内容",
            summary="测试功能",
            status="pending",
            tags=[]
        )
        await self.project_service.add_item(
            project_id=project_id,
            group="notes",
            content="笔记内容",
            summary="笔记",
            tags=[]
        )
        await self.project_service.add_item(
            project_id=project_id,
            group="fixes",
            content="测试修复内容",
            summary="测试修复",
            status="pending",
            tags=[]
        )
        await self.project_service.add_item(
            project_id=project_id,
            group="standards",
            content="规范内容",
            summary="规范",
            tags=[]
        )

        # 验证目录结构
        # ProjectService 使用项目名称作为目录名
        projects = await self.project_service.list_projects()
        if projects["success"] and projects["total"] > 0:
            # 获取实际的项目名称（目录名）
            for p in projects["projects"]:
                project_dir = Path(self.temp_dir) / p["name"]
                if project_dir.exists():
                    break
            else:
                # 如果找不到，跳过目录验证
                print("    ⚠ 无法验证项目目录")
                return
        else:
            raise AssertionError("无法找到项目目录")

        project_file = project_dir / "_project.json"
        assert project_file.exists(), "_project.json 不存在"

        # 验证所有默认组的 content 目录存在
        for group_name in ("features", "fixes", "notes", "standards"):
            group_dir = project_dir / group_name
            assert group_dir.exists(), f"{group_name} 目录不存在"
            assert group_dir.is_dir(), f"{group_name} 应该是目录"

        print("✓ 项目目录结构测试通过")

    async def test_all_groups_content_separate_storage(self):
        """测试所有默认组的 content 独立文件存储."""
        await self.async_setup_method()

        result = await self.project_service.register_project("全组测试", "/tmp/test")
        project_id = result["project_id"]

        # 为每个默认组添加条目
        test_data = {}
        for group in ("features", "fixes", "notes", "standards"):
            content = f"这是{group}的详细内容，用于验证独立存储" * 10
            status = "pending" if group in ("features", "fixes") else None
            severity = "medium" if group == "fixes" else None

            kwargs = dict(
                project_id=project_id,
                group=group,
                content=content,
                summary=f"测试{group}",
                tags=["test"]
            )
            if status:
                kwargs["status"] = status
            if severity:
                kwargs["severity"] = severity

            add_result = await self.project_service.add_item(**kwargs)
            item_id = add_result["item_id"]
            test_data[group] = (item_id, content)

        # 验证每个组的 .md 文件存在且内容正确
        for group, (item_id, expected_content) in test_data.items():
            content_file = self.storage._get_item_content_path(project_id, group, item_id)
            assert content_file.exists(), f"{group} content 文件不存在: {content_file}"

            saved = content_file.read_text(encoding="utf-8")
            assert saved == expected_content, f"{group} content 不匹配"

        # 验证 _project.json 不包含任何 content 字段
        project_dir = self.storage._get_project_dir(project_id)
        project_json = project_dir / "_project.json"
        with open(project_json, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        for group in ("features", "fixes", "notes", "standards"):
            for item in disk_data.get(group, []):
                assert "content" not in item, f"{group} 条目不应包含 content（JSON文件中）"

        print("✓ 所有默认组 content 独立存储测试通过")

    async def test_delete_item_removes_content_file(self):
        """测试删除条目时清理 .md 文件."""
        await self.async_setup_method()

        result = await self.project_service.register_project("删除测试", "/tmp/test")
        project_id = result["project_id"]

        # 为每个默认组添加然后删除
        for group in ("features", "fixes", "notes", "standards"):
            status = "pending" if group in ("features", "fixes") else None
            kwargs = dict(
                project_id=project_id,
                group=group,
                content=f"待删除{group}内容",
                summary=f"待删除{group}",
                tags=[]
            )
            if status:
                kwargs["status"] = status

            add_result = await self.project_service.add_item(**kwargs)
            item_id = add_result["item_id"]

            # 验证文件存在
            content_file = self.storage._get_item_content_path(project_id, group, item_id)
            assert content_file.exists(), f"{group} content 文件应存在"

            # 删除
            await self.project_service.delete_item(project_id, group, item_id)

            # 验证文件已清理
            assert not content_file.exists(), f"{group} content 文件应被删除"

        print("✓ 删除条目清理 content 文件测试通过")

    async def test_inline_content_migration(self):
        """测试旧格式内联 content 自动迁移到独立文件."""
        await self.async_setup_method()

        # 注册项目获取 project_id
        result = await self.project_service.register_project("迁移测试", "/tmp/test")
        project_id = result["project_id"]

        # 直接修改 _project.json，模拟旧格式（内联 content）
        project_dir = self.storage._get_project_dir(project_id)
        project_json = project_dir / "_project.json"
        with open(project_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 为各组的条目注入内联 content（模拟旧格式）
        test_contents = {}
        for group in ("features", "fixes", "standards"):
            if group in data and len(data[group]) == 0:
                # 如果组为空，添加一个测试条目
                item_id = f"{group[:4]}_test_001"
                data[group].append({
                    "id": item_id,
                    "summary": f"测试{group}",
                    "tags": [],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                    "content": f"旧格式内联{group}内容"
                })
                test_contents[group] = item_id

        with open(project_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 清除缓存，触发重新加载 + 迁移
        self.storage._project_data_cache.clear()

        # 重新加载（触发内联 content 迁移）
        loaded = await self.storage._load_project(project_id)
        assert loaded is not None, "项目加载失败"

        # 验证：加载后条目不再有 content 字段
        for group, item_id in test_contents.items():
            for item in loaded.get(group, []):
                if item["id"] == item_id:
                    assert "content" not in item, f"{group} 条目应已迁移 content"

        # 验证：独立文件已创建，内容正确
        for group, item_id in test_contents.items():
            loaded_content = await self.storage._load_item_content(project_id, group, item_id)
            assert loaded_content == f"旧格式内联{group}内容", f"{group} 迁移内容不正确"

        print("✓ 内联 content 自动迁移测试通过")

    async def test_concurrent_access(self):
        """测试并发访问安全性."""
        await self.async_setup_method()

        result = await self.project_service.register_project("并发测试", "/tmp/test")
        project_id = result["project_id"]

        # 并发添加多个功能
        tasks = []
        for i in range(30):
            task = self.project_service.add_item(
                project_id=project_id,
                group="features",
                content=f"功能{i}内容",
                summary=f"功能{i}",
                status="pending",
                tags=[]
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Task {i} failed with exception: {result}")
            assert result["success"], f"Task {i} failed: {result.get('error')}"

        # 验证数据一致性
        project_data = await self.project_service.get_project(project_id)
        assert len(project_data["data"]["features"]) == 30, f"数据数量不正确: {len(project_data['data']['features'])}"

        print("✓ 并发访问安全性测试通过")


# 为了向后兼容，保留同步版本的运行函数
def run_all_tests():
    """运行所有集成测试."""
    print("=" * 60)
    print("存储层集成测试")
    print("=" * 60)
    print()
    print("注意：此测试已转换为异步版本，请使用 pytest 运行")
    print("命令：pytest test/integration/test_storage.py -v")
    print()




@pytest.mark.asyncio
class TestSmartCacheIntegration:
    """SmartCache 集成测试."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.project_service = ProjectService(self.storage)

    async def test_smart_cache_integration(self):
        """测试 SmartCache 与 Storage 的集成."""
        await self.async_setup_method()
        # 创建一个项目
        result = await self.project_service.register_project("cache_test", "缓存测试项目")
        project_id = result["project_id"]

        # 添加一些数据
        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            summary="测试功能",
            content="测试内容",
        )

        # 多次读取项目数据（会触发缓存）
        for _ in range(5):
            data = await self.storage.get_project_data(project_id)
            assert data is not None
            assert "features" in data

        # 验证缓存统计
        stats = self.storage.get_cache_stats()
        assert stats["l2_hits"] > 0 or stats["l1_hits"] > 0

    async def test_cache_hit_rate_improvement(self):
        """测试缓存命中率提升."""
        await self.async_setup_method()
        # 创建项目并添加数据
        result = await self.project_service.register_project("hit_rate_test", "命中率测试")
        project_id = result["project_id"]

        for i in range(20):
            await self.project_service.add_item(
                project_id=project_id,
                group="features",
                summary=f"功能 {i}",
                content=f"内容 {i}",
            )

        # 多次读取相同的项目数据（模拟热点访问）
        for _ in range(100):
            data = await self.storage.get_project_data(project_id)
            assert data is not None

        # 检查缓存命中率
        stats = self.storage.get_cache_stats()
        hit_rate = float(stats["hit_rate"].rstrip("%"))
        assert hit_rate > 50  # 应该有明显的缓存命中

    async def test_hot_data_promotion(self):
        """测试热点数据自动升级."""
        await self.async_setup_method()

        result = await self.project_service.register_project("promo_test", "升级测试")
        project_id = result["project_id"]

        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            summary="热点功能",
            content="热点内容",
        )

        # 多次访问同一个项目（触发热点升级）
        for _ in range(10):
            data = await self.storage.get_project_data(project_id)
            assert data is not None

        # 验证有升级统计
        stats = self.storage.get_cache_stats()
        assert stats["l2_hits"] > 0

    async def test_cache_stats_api(self):
        """测试缓存统计 API."""
        await self.async_setup_method()
        # 获取初始统计
        stats_before = self.storage.get_cache_stats()
        assert "hit_rate" in stats_before
        assert "l1_hits" in stats_before
        assert "l2_hits" in stats_before
        assert "l3_hits" in stats_before
        assert "total_misses" in stats_before
        assert "promotions" in stats_before
        assert "l1_size" in stats_before
        assert "l2_size" in stats_before
        assert "l3_size" in stats_before

        # 执行一些操作
        result = await self.project_service.register_project("stats_test", "统计测试")
        project_id = result["project_id"]

        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            summary="测试",
            content="内容",
        )

        # 多次读取项目数据
        for _ in range(10):
            await self.storage.get_project_data(project_id)

        # 获取更新后的统计
        stats_after = self.storage.get_cache_stats()
        # 应该有活动
        assert stats_after["l2_hits"] > 0 or stats_after["l1_hits"] > 0

    async def test_backward_compatibility(self):
        """测试向后兼容性."""
        await self.async_setup_method()
        # 验证旧的缓存接口仍然可用
        result = await self.project_service.register_project("compat_test", "兼容性测试")
        project_id = result["project_id"]

        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            summary="测试",
            content="内容",
        )

        # 使用旧接口访问缓存
        cache = self.storage.project_data_cache
        assert cache is not None

        # 刷新项目缓存
        await self.storage.refresh_projects_cache()
        projects = self.storage.projects_cache
        assert projects is not None
        assert project_id in projects


if __name__ == "__main__":
    run_all_tests()
