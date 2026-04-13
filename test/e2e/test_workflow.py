#!/usr/bin/env python3
"""端到端工作流测试."""

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
from business.groups_service import GroupsService


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_workflow():
    """测试完整工作流: 注册→添加→查询→更新→删除."""
    print("测试: 完整工作流...")

    temp_dir = tempfile.mkdtemp()
    try:
        storage = Storage(storage_dir=temp_dir)
        groups_service = GroupsService(storage)
        project_service = ProjectService(storage, groups_service)
        tag_service = TagService(storage)

        # 1. 注册项目
        print("  步骤1: 注册项目...")
        result = await project_service.register_project(
            name="电商项目",
            path="/home/user/ecommerce",
            summary="在线购物平台",
            tags=["web", "ecommerce"]
        )
        assert result["success"], f"注册项目失败: {result}"
        project_id = result["data"]["project_id"]
        print(f"    ✓ 项目已注册 (ID: {project_id})")

        # 2. 注册标签
        print("  步骤2: 注册标签...")
        await tag_service.register_tag(project_id, "urgent", "紧急任务")
        await tag_service.register_tag(project_id, "feature", "新功能开发")
        await tag_service.register_tag(project_id, "backend", "后端模块")
        print("    ✓ 标签已注册")

        # 3. 添加功能
        print("  步骤3: 添加功能...")
        result = await project_service.add_item(
            project_id=project_id,
            group="features",
            content="实现用户认证功能的详细描述",
            summary="实现用户认证功能",
            status="pending",
            tags=["backend"]
        )
        assert result["success"], f"添加功能失败: {result}"
        feature_id = result["data"]["item_id"]
        print(f"    ✓ 功能已添加 (ID: {feature_id})")

        # 4. 添加笔记
        print("  步骤4: 添加笔记...")
        result = await project_service.add_item(
            project_id=project_id,
            group="notes",
            content="技术选型: 使用 PyJWT 库实现 token 验证，过期时间设置为 24 小时。",
            summary="JWT 实现方案",
            tags=["backend"]
        )
        assert result["success"], f"添加笔记失败: {result}"
        note_id = result["data"]["item_id"]
        print(f"    ✓ 笔记已添加 (ID: {note_id})")

        # 5. 查询项目
        print("  步骤5: 查询项目...")
        project_data = await project_service.get_project(project_id)
        assert project_data is not None, "查询项目失败"
        assert project_data["data"]["info"]["name"] == "电商项目", "项目名称不正确"
        print("    ✓ 项目查询成功")

        # 6. 查询功能列表
        print("  步骤6: 查询功能列表...")
        result = await project_service.get_project(project_id, include_items=True)
        assert result is not None, "查询失败"
        features = result["data"]["features"]
        assert len(features) >= 1, "未找到功能"
        print(f"    ✓ 功能查询成功 (找到 {len(features)} 个条目)")

        # 7. 更新功能状态
        print("  步骤7: 更新功能状态...")
        result = await project_service.update_item(project_id, "features", feature_id, status="in_progress")
        assert result["success"], f"更新功能失败: {result}"
        project_data = await project_service.get_project(project_id, include_items=True)
        feature = project_data["data"]["features"][0]
        assert feature["status"] == "in_progress", "状态更新不正确"
        print("    ✓ 功能状态已更新")

        # 8. 添加修复记录
        print("  步骤8: 添加修复记录...")
        result = await project_service.add_item(
            project_id=project_id,
            group="fixes",
            content="修复 token 刷新逻辑的详细描述",
            summary="修复 token 刷新逻辑",
            status="completed",
            severity="medium",
            tags=["backend"]
        )
        assert result["success"], f"添加修复失败: {result}"
        print("    ✓ 修复记录已添加")

        # 9. 添加规范
        print("  步骤9: 添加规范...")
        result = await project_service.add_item(
            project_id=project_id,
            group="standards",
            content="后端 API 统一使用 RESTful 风格，返回 JSON 格式数据。",
            summary="API 设计规范",
            tags=["backend"]
        )
        assert result["success"], f"添加规范失败: {result}"
        print("    ✓ 规范已添加")

        # 10. 查看分组统计
        print("  步骤10: 查看分组统计...")
        project_data = await project_service.get_project(project_id, include_items=True)
        data = project_data["data"]
        print(f"    ✓ 分组统计: features={len(data['features'])}, "
              f"notes={len(data['notes'])}, "
              f"fixes={len(data['fixes'])}, "
              f"standards={len(data['standards'])}")

        # 11. 删除功能
        print("  步骤11: 删除功能...")
        result = await project_service.delete_item(project_id, "features", feature_id)
        assert result["success"], f"删除功能失败: {result}"
        project_data = await project_service.get_project(project_id, include_items=True)
        assert len(project_data["data"]["features"]) == 0, "功能未正确删除"
        print("    ✓ 功能已删除")

        # 12. 重命名项目
        print("  步骤12: 重命名项目...")
        result = await project_service.project_rename(project_id, "电商平台升级")
        assert result["success"], f"重命名失败: {result}"
        project_data = await project_service.get_project(project_id)
        assert project_data["data"]["info"]["name"] == "电商平台升级", "名称未正确更新"
        print("    ✓ 项目已重命名")

        print("\n  ✓ 完整工作流测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multi_project_workflow():
    """测试多项目工作流."""
    print("测试: 多项目工作流...")

    temp_dir = tempfile.mkdtemp()
    try:
        storage = Storage(storage_dir=temp_dir)
        groups_service = GroupsService(storage)
        project_service = ProjectService(storage, groups_service)

        # 创建多个项目
        print("  创建多个项目...")
        project_a = await project_service.register_project("项目A", "/path/a", tags=["web"])
        project_b = await project_service.register_project("项目B", "/path/b", tags=["api"])
        project_c = await project_service.register_project("项目C", "/path/c", tags=["mobile"])

        # 为每个项目添加内容（使用 add_item 统一接口）
        await project_service.add_item(project_id=project_a["data"]["project_id"], group="features", content="Web前端功能内容", summary="Web前端功能", status="pending", tags=["web"])
        await project_service.add_item(project_id=project_b["data"]["project_id"], group="features", content="API接口功能内容", summary="API接口功能", status="pending", tags=["api"])
        await project_service.add_item(project_id=project_c["data"]["project_id"], group="features", content="移动端功能内容", summary="移动端功能", status="pending", tags=["mobile"])

        # 获取项目列表
        result = await project_service.list_projects()
        assert result["success"], f"获取项目列表失败: {result}"
        assert result["data"]["total"] == 3, f"项目数量不正确: {result['data']['total']}"

        # 验证各项目数据独立
        data_a = await project_service.get_project(project_a["data"]["project_id"], include_items=True)
        data_b = await project_service.get_project(project_b["data"]["project_id"], include_items=True)
        data_c = await project_service.get_project(project_c["data"]["project_id"], include_items=True)

        assert len(data_a["data"]["features"]) == 1, "项目A功能数量不正确"
        assert len(data_b["data"]["features"]) == 1, "项目B功能数量不正确"
        assert len(data_c["data"]["features"]) == 1, "项目C功能数量不正确"

        print("  ✓ 多项目工作流测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

