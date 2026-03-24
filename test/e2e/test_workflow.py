#!/usr/bin/env python3
"""端到端工作流测试."""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from memory import ProjectMemory


def test_complete_workflow():
    """测试完整工作流: 注册→添加→查询→更新→删除."""
    print("测试: 完整工作流...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        # 1. 注册项目
        print("  步骤1: 注册项目...")
        result = memory.register_project(
            name="电商项目",
            path="/home/user/ecommerce",
            summary="在线购物平台",
            tags=["web", "ecommerce"]
        )
        assert result["success"], f"注册项目失败: {result}"
        project_id = result["project_id"]
        print(f"    ✓ 项目已注册 (ID: {project_id})")

        # 2. 注册标签
        print("  步骤2: 注册标签...")
        memory.register_tag(project_id, "urgent", "紧急任务")
        memory.register_tag(project_id, "feature", "新功能")
        memory.register_tag(project_id, "backend", "后端模块")
        print("    ✓ 标签已注册")

        # 3. 添加功能
        print("  步骤3: 添加功能...")
        result = memory.add_feature(
            project_id,
            content="实现用户认证功能的详细描述",
            summary="实现用户认证功能",
            status="pending"
        )
        assert result["success"], f"添加功能失败: {result}"
        feature_id = result["feature_id"]
        print(f"    ✓ 功能已添加 (ID: {feature_id})")

        # 4. 添加笔记
        print("  步骤4: 添加笔记...")
        result = memory.add_note(
            project_id,
            note="技术选型: 使用 PyJWT 库实现 token 验证，过期时间设置为 24 小时。",
            summary="JWT 实现方案",
            tags=["backend"]
        )
        assert result["success"], f"添加笔记失败: {result}"
        note_id = result["note_id"]
        print(f"    ✓ 笔记已添加 (ID: {note_id})")

        # 5. 查询项目
        print("  步骤5: 查询项目...")
        project_data = memory.get_project(project_id)
        assert project_data is not None, "查询项目失败"
        assert project_data["data"]["info"]["name"] == "电商项目", "项目名称不正确"
        print("    ✓ 项目查询成功")

        # 6. 查询功能列表
        print("  步骤6: 查询功能列表...")
        result = memory.get_project(project_id)
        assert result is not None, "查询失败"
        features = result["data"]["features"]
        assert len(features) >= 1, "未找到功能"
        print(f"    ✓ 功能查询成功 (找到 {len(features)} 个条目)")

        # 7. 更新功能状态
        print("  步骤7: 更新功能状态...")
        result = memory.update_feature(project_id, feature_id, status="in_progress")
        assert result["success"], f"更新功能失败: {result}"
        project_data = memory.get_project(project_id)
        feature = project_data["data"]["features"][0]
        assert feature["status"] == "in_progress", "状态更新不正确"
        print("    ✓ 功能状态已更新")

        # 8. 添加修复记录
        print("  步骤8: 添加修复记录...")
        result = memory.add_fix(
            project_id,
            content="修复 token 刷新逻辑的详细描述",
            summary="修复 token 刷新逻辑",
            status="completed",
            severity="medium"
        )
        assert result["success"], f"添加修复失败: {result}"
        print("    ✓ 修复记录已添加")

        # 9. 添加规范
        print("  步骤9: 添加规范...")
        result = memory.add_standard(
            project_id,
            content="后端 API 统一使用 RESTful 风格，返回 JSON 格式数据。",
            summary="API 设计规范"
        )
        assert result["success"], f"添加规范失败: {result}"
        print("    ✓ 规范已添加")

        # 10. 查看分组统计
        print("  步骤10: 查看分组统计...")
        project_data = memory.get_project(project_id)
        data = project_data["data"]
        print(f"    ✓ 分组统计: features={len(data['features'])}, "
              f"notes={len(data['notes'])}, "
              f"fixes={len(data['fixes'])}, "
              f"standards={len(data['standards'])}")

        # 11. 删除功能
        print("  步骤11: 删除功能...")
        result = memory.delete_feature(project_id, feature_id)
        assert result["success"], f"删除功能失败: {result}"
        project_data = memory.get_project(project_id)
        assert len(project_data["data"]["features"]) == 0, "功能未正确删除"
        print("    ✓ 功能已删除")

        # 12. 重命名项目
        print("  步骤12: 重命名项目...")
        result = memory.project_rename(project_id, "电商平台升级")
        assert result["success"], f"重命名失败: {result}"
        project_data = memory.get_project(project_id)
        assert project_data["data"]["info"]["name"] == "电商平台升级", "名称未正确更新"
        print("    ✓ 项目已重命名")

        print("\n  ✓ 完整工作流测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_multi_project_workflow():
    """测试多项目工作流."""
    print("测试: 多项目工作流...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        # 创建多个项目
        print("  创建多个项目...")
        project_a = memory.register_project("项目A", "/path/a", tags=["web"])
        project_b = memory.register_project("项目B", "/path/b", tags=["api"])
        project_c = memory.register_project("项目C", "/path/c", tags=["mobile"])

        # 为每个项目添加内容
        memory.add_feature(project_a["project_id"], "Web前端功能内容", "Web前端功能", status="pending")
        memory.add_feature(project_b["project_id"], "API接口功能内容", "API接口功能", status="pending")
        memory.add_feature(project_c["project_id"], "移动端功能内容", "移动端功能", status="pending")

        # 获取项目列表
        result = memory.list_projects()
        assert result["total"] == 3, f"项目数量不正确: {result['total']}"

        # 验证各项目数据独立
        data_a = memory.get_project(project_a["project_id"])
        data_b = memory.get_project(project_b["project_id"])
        data_c = memory.get_project(project_c["project_id"])

        assert len(data_a["data"]["features"]) == 1, "项目A功能数量不正确"
        assert len(data_b["data"]["features"]) == 1, "项目B功能数量不正确"
        assert len(data_c["data"]["features"]) == 1, "项目C功能数量不正确"

        print("  ✓ 多项目工作流测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有端到端测试."""
    print("=" * 60)
    print("端到端工作流测试")
    print("=" * 60)
    print()

    tests = [
        test_complete_workflow,
        test_multi_project_workflow,
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
