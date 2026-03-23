#!/usr/bin/env python3
"""ProjectMemory 类单元测试."""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from memory import ProjectMemory


def test_project_memory_initialization():
    """测试 ProjectMemory 初始化."""
    print("测试: ProjectMemory 初始化...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)
        assert memory.storage_dir == Path(temp_dir), "存储目录设置不正确"
        assert memory.storage_dir.exists(), "存储目录不存在"
        print("  ✓ 初始化测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_register_project():
    """测试项目注册."""
    print("测试: 项目注册...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        # 测试注册
        result = memory.register_project(
            name="测试项目",
            path="/tmp/test",
            description="测试描述",
            tags=["test", "demo"]
        )

        assert result["success"], f"注册失败: {result}"
        assert "project_id" in result, "返回结果缺少 project_id"

        project_id = result["project_id"]

        # 验证项目已创建
        project_data = memory.get_project(project_id)
        assert project_data is not None, "项目未正确保存"
        assert project_data["data"]["info"]["name"] == "测试项目", "项目名称不正确"

        print(f"  ✓ 项目注册测试通过 (ID: {project_id})")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_feature():
    """测试添加功能."""
    print("测试: 添加功能...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        # 先注册项目
        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加功能（不使用标签）
        result = memory.add_feature(
            project_id,
            content="实现用户登录功能",
            description="用户登录",
            status="pending"
        )

        assert result["success"], f"添加功能失败: {result}"
        assert "feature_id" in result, "返回结果缺少 feature_id"

        # 验证功能已添加
        project_data = memory.get_project(project_id)
        features = project_data["data"]["features"]
        assert len(features) == 1, "功能数量不正确"
        assert features[0]["content"] == "实现用户登录功能", "功能内容不正确"
        assert features[0]["description"] == "用户登录", "功能描述不正确"

        print(f"  ✓ 添加功能测试通过 (ID: {result['feature_id']})")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_note():
    """测试添加笔记."""
    print("测试: 添加笔记...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加笔记（不使用标签，避免未注册错误）
        result = memory.add_note(
            project_id,
            note="这是测试笔记内容",
            description="测试笔记"
        )

        assert result["success"], f"添加笔记失败: {result}"

        # 验证笔记已添加
        project_data = memory.get_project(project_id)
        notes = project_data["data"]["notes"]
        assert len(notes) == 1, "笔记数量不正确"

        print(f"  ✓ 添加笔记测试通过 (ID: {result['note_id']})")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_fix():
    """测试添加修复."""
    print("测试: 添加修复...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加修复（不使用标签）
        result = memory.add_fix(
            project_id,
            content="修复登录bug的详细描述",
            description="修复登录bug",
            status="completed",
            severity="high"
        )

        assert result["success"], f"添加修复失败: {result}"

        # 验证修复已添加
        project_data = memory.get_project(project_id)
        fixes = project_data["data"]["fixes"]
        assert len(fixes) == 1, "修复数量不正确"
        assert fixes[0]["content"] == "修复登录bug的详细描述", "修复内容不正确"
        assert fixes[0]["description"] == "修复登录bug", "修复描述不正确"

        print(f"  ✓ 添加修复测试通过 (ID: {result['fix_id']})")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_standard():
    """测试添加规范."""
    print("测试: 添加规范...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加规范（不使用标签）
        result = memory.add_standard(
            project_id,
            content="代码风格规范",
            description="命名和格式规范"
        )

        assert result["success"], f"添加规范失败: {result}"

        # 验证规范已添加
        project_data = memory.get_project(project_id)
        standards = project_data["data"]["standards"]
        assert len(standards) == 1, "规范数量不正确"

        print(f"  ✓ 添加规范测试通过 (ID: {result['standard_id']})")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_update_item():
    """测试更新条目."""
    print("测试: 更新条目...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加功能
        result = memory.add_feature(project_id, "测试功能内容", "测试功能", status="pending")
        feature_id = result["feature_id"]

        # 更新功能
        result = memory.update_feature(
            project_id,
            feature_id,
            status="completed"
        )

        assert result["success"], f"更新功能失败: {result}"

        # 验证更新
        project_data = memory.get_project(project_id)
        feature = project_data["data"]["features"][0]
        assert feature["status"] == "completed", "状态更新不正确"

        print("  ✓ 更新条目测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delete_item():
    """测试删除条目."""
    print("测试: 删除条目...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("测试项目", "/tmp/test")
        project_id = result["project_id"]

        # 添加功能
        result = memory.add_feature(project_id, "测试功能内容", "测试功能", status="pending")
        feature_id = result["feature_id"]

        # 删除功能
        result = memory.delete_feature(project_id, feature_id)

        assert result["success"], f"删除功能失败: {result}"

        # 验证删除
        project_data = memory.get_project(project_id)
        features = project_data["data"]["features"]
        assert len(features) == 0, "功能未正确删除"

        print("  ✓ 删除条目测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_rename_project():
    """测试项目重命名."""
    print("测试: 项目重命名...")

    temp_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=temp_dir)

        result = memory.register_project("旧名称", "/tmp/test")
        project_id = result["project_id"]

        # 重命名
        result = memory.project_rename(project_id, "新名称")

        assert result["success"], f"重命名失败: {result}"

        # 验证重命名
        project_data = memory.get_project(project_id)
        assert project_data["data"]["info"]["name"] == "新名称", "名称未正确更新"

        print("  ✓ 项目重命名测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有单元测试."""
    print("=" * 60)
    print("ProjectMemory 单元测试")
    print("=" * 60)
    print()

    tests = [
        test_project_memory_initialization,
        test_register_project,
        test_add_feature,
        test_add_note,
        test_add_fix,
        test_add_standard,
        test_update_item,
        test_delete_item,
        test_rename_project,
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
