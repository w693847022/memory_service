#!/usr/bin/env python3
"""MCP 工具接口集成测试."""

import sys
import os
import tempfile
import shutil
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService


@pytest.mark.asyncio
class TestApiIntegration:
    """MCP 工具接口集成测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.tag_service = None
        self.project_id = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.project_service = ProjectService(self.storage)
        self.tag_service = TagService(self.storage)

    async def test_project_list_integration(self):
        """测试项目列表接口集成."""
        await self.async_setup_method()

        # 注册多个项目
        await self.project_service.register_project("项目A", "/path/a", tags=["web"])
        await self.project_service.register_project("项目B", "/path/b", tags=["api"])
        await self.project_service.register_project("项目C", "/path/c", tags=["mobile"])

        # 获取项目列表
        result = await self.project_service.list_projects()

        assert result["success"], f"获取项目列表失败: {result}"
        assert result["data"]["total"] == 3, f"项目数量不正确: {result['data']['total']}"

        # 验证项目信息
        projects = result["data"]["projects"]
        names = [p["name"] for p in projects]
        assert "项目A" in names, "项目A 不在列表中"
        assert "项目B" in names, "项目B 不在列表中"
        assert "项目C" in names, "项目C 不在列表中"

        print(f"✓ 项目列表接口测试通过 (共 {result['data']['total']} 个项目)")

    async def test_project_get_with_tags(self):
        """测试按标签查询接口."""
        await self.async_setup_method()

        result = await self.project_service.register_project("测试项目", "/tmp/test")
        project_id = result["data"]["project_id"]

        # 注册标签
        await self.tag_service.register_tag(project_id, "urgent", "紧急且高优先级的任务")
        await self.tag_service.register_tag(project_id, "bug", "程序错误和缺陷修复相关")
        await self.tag_service.register_tag(project_id, "api", "应用程序接口开发相关")

        # 添加带标签的功能（使用 add_item 统一接口）
        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="修复登录bug的详细描述",
            summary="修复登录bug",
            status="pending",
            tags=["urgent", "bug"]
        )

        await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="优化API性能的详细描述",
            summary="优化API性能",
            status="pending",
            tags=["api"]
        )

        # 查询所有数据并验证
        result = await self.project_service.get_project(project_id)

        assert result is not None, "查询失败"
        assert len(result["data"]["features"]) == 2, f"功能数量不正确: {len(result['data']['features'])}"

        print(f"✓ 按标签查询测试通过 (找到 {len(result['data']['features'])} 个条目)")

    async def test_tag_operations_integration(self):
        """测试标签操作集成."""
        await self.async_setup_method()

        result = await self.project_service.register_project("测试项目", "/tmp/test")
        project_id = result["data"]["project_id"]

        # 注册标签
        result = await self.tag_service.register_tag(project_id, "backend", "后端服务器端开发相关")
        assert result["success"], f"注册标签失败: {result}"

        # 查询标签信息 (使用 get_project 中的 tag_registry)
        project_data = await self.project_service.get_project(project_id)
        tag_registry = project_data["data"].get("tag_registry", {})
        assert "backend" in tag_registry, "标签未正确注册"

        # 合并标签
        await self.tag_service.register_tag(project_id, "server", "服务器端")
        result = await self.tag_service.merge_tags(project_id, "server", "backend")
        assert result["success"], f"合并标签失败: {result}"

        print("✓ 标签操作集成测试通过")

    async def test_groups_list_integration(self):
        """测试分组列表接口."""
        await self.async_setup_method()

        result = await self.project_service.register_project("测试项目", "/tmp/test")
        project_id = result["data"]["project_id"]

        # 添加各分组内容（使用 add_item 统一接口）
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
            content="测试笔记",
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
            content="测试规范",
            summary="规范",
            tags=[]
        )

        # 获取项目数据（包含所有分组）
        result = await self.project_service.get_project(project_id)

        assert result is not None, "获取项目数据失败"

        # 验证分组数据
        data = result["data"]
        assert len(data["features"]) == 1, f"features 分组计数错误: {len(data['features'])}"
        assert len(data["notes"]) == 1, f"notes 分组计数错误: {len(data['notes'])}"
        assert len(data["fixes"]) == 1, f"fixes 分组计数错误: {len(data['fixes'])}"
        assert len(data["standards"]) == 1, f"standards 分组计数错误: {len(data['standards'])}"

        print("✓ 分组列表接口测试通过")


# 为了向后兼容，保留同步版本的运行函数
def run_all_tests():
    """运行所有集成测试."""
    print("=" * 60)
    print("MCP 工具接口集成测试")
    print("=" * 60)
    print()
    print("注意：此测试已转换为异步版本，请使用 pytest 运行")
    print("命令：pytest test/integration/test_api.py -v")
    print()


if __name__ == "__main__":
    run_all_tests()
