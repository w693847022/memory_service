#!/usr/bin/env python3
"""project_remove 功能单元测试.

测试项目归档和永久删除功能。
"""

import sys
import os
import tempfile
import shutil
import tarfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory


def _setup_memory():
    """创建临时存储目录和 ProjectMemory 实例."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)
    return temp_dir, memory


def _register_project(memory, name="测试项目", summary="测试摘要", tags=None):
    """注册一个测试项目并返回 project_id."""
    result = memory.register_project(
        name=name,
        path="/tmp/test",
        summary=summary,
        tags=tags or ["test"]
    )
    assert result["success"], f"注册项目失败: {result}"
    return result["project_id"]


def test_archive_project_success():
    """测试归档项目成功."""
    print("测试: 归档项目成功...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "归档测试项目", "归档测试摘要")
        project_name = "归档测试项目"

        # 归档项目
        result = memory.remove_project(project_id, mode="archive")
        assert result["success"], f"归档失败: {result}"
        assert "已归档" in result["message"]

        # 验证原项目目录已删除
        project_dir = memory._get_project_dir(project_id)
        assert not project_dir.exists(), "原项目目录未删除"

        # 验证 .archived 目录存在 tar.gz 文件
        archive_dir = Path(temp_dir) / ".archived"
        assert archive_dir.exists(), ".archived 目录不存在"

        tar_files = list(archive_dir.glob("*.tar.gz"))
        assert len(tar_files) == 1, f"归档文件数量不正确: {len(tar_files)}"

        # 验证 tar.gz 内容包含项目目录
        with tarfile.open(str(tar_files[0]), "r:gz") as tar:
            names = tar.getnames()
            assert any(project_name in n for n in names), f"归档文件中未找到项目目录: {names}"

        print("  ✓ 归档项目测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_project_generates_meta_json():
    """测试归档生成元数据文件."""
    print("测试: 归档元数据文件...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "元数据测试", "元数据测试摘要", ["tag1", "tag2"])

        result = memory.remove_project(project_id, mode="archive")
        assert result["success"]

        # 查找元数据文件
        archive_dir = Path(temp_dir) / ".archived"
        meta_files = list(archive_dir.glob("*_meta.json"))
        assert len(meta_files) == 1, f"元数据文件数量不正确: {len(meta_files)}"

        # 验证元数据内容
        with open(meta_files[0], "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["id"] == project_id, f"元数据 id 不匹配: {meta['id']}"
        assert meta["name"] == "元数据测试", f"元数据 name 不匹配: {meta['name']}"
        assert meta["summary"] == "元数据测试摘要"
        assert "tag1" in meta["tags"], f"标签不包含 tag1: {meta['tags']}"
        assert "archived_at" in meta, "缺少 archived_at 字段"
        assert "archive_file" in meta, "缺少 archive_file 字段"
        assert meta["archive_file"].endswith(".tar.gz")

        print("  ✓ 归档元数据测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delete_project_permanent():
    """测试永久删除项目."""
    print("测试: 永久删除项目...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "删除测试项目")

        # 永久删除
        result = memory.remove_project(project_id, mode="delete")
        assert result["success"], f"删除失败: {result}"
        assert "已删除" in result["message"]

        # 验证项目目录已删除
        project_dir = memory._get_project_dir(project_id)
        assert not project_dir.exists(), "项目目录未删除"

        # 验证 .archived 中无文件
        archive_dir = Path(temp_dir) / ".archived"
        if archive_dir.exists():
            assert len(list(archive_dir.iterdir())) == 0, ".archived 中有残留文件"

        # 验证缓存已清理
        assert project_id not in memory._projects_cache

        print("  ✓ 永久删除测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_already_archived_project():
    """测试归档已归档的项目失败."""
    print("测试: 重复归档失败...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "重复归档测试")

        # 第一次归档
        result = memory.remove_project(project_id, mode="archive")
        assert result["success"]

        # 第二次归档应失败
        result = memory.remove_project(project_id, mode="archive")
        assert not result["success"], "重复归档应该失败"
        assert "已归档" in result["error"]

        # 第二次删除也应失败
        result = memory.remove_project(project_id, mode="delete")
        assert not result["success"], "归档后删除应该失败"

        print("  ✓ 重复归档测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_list_projects_hides_archived():
    """测试 project_list 默认隐藏归档项目."""
    print("测试: project_list 隐藏归档项目...")
    temp_dir, memory = _setup_memory()
    try:
        id1 = _register_project(memory, "活跃项目1")
        id2 = _register_project(memory, "活跃项目2")

        # 归档第二个项目
        result = memory.remove_project(id2, mode="archive")
        assert result["success"]

        # 默认不包含归档项目
        result = memory.list_projects(include_archived=False)
        assert result["success"]
        projects = result["projects"]
        assert len(projects) == 1, f"应只返回1个项目: {len(projects)}"
        assert projects[0]["name"] == "活跃项目1"

        print("  ✓ project_list 隐藏归档测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_list_projects_shows_archived():
    """测试 project_list include_archived=true 显示归档项目."""
    print("测试: project_list 显示归档项目...")
    temp_dir, memory = _setup_memory()
    try:
        id1 = _register_project(memory, "活跃项目A")
        id2 = _register_project(memory, "归档项目B")

        # 归档第二个项目
        result = memory.remove_project(id2, mode="archive")
        assert result["success"]

        # 包含归档项目
        result = memory.list_projects(include_archived=True)
        assert result["success"]
        projects = result["projects"]
        assert len(projects) == 2, f"应返回2个项目: {len(projects)}"

        # 验证活跃项目
        active = [p for p in projects if p.get("status") == "active"]
        assert len(active) == 1
        assert active[0]["name"] == "活跃项目A"

        # 验证归档项目
        archived = [p for p in projects if p.get("status") == "archived"]
        assert len(archived) == 1
        assert archived[0]["name"] == "归档项目B"
        assert "archived_at" in archived[0]

        print("  ✓ project_list 显示归档测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_data_operations_blocked_for_archived():
    """测试归档项目数据操作被拦截."""
    print("测试: 归档项目数据操作被拦截...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "归档操作测试")

        # 归档项目
        result = memory.remove_project(project_id, mode="archive")
        assert result["success"]

        # 尝试添加条目
        result = memory.add_item(project_id, "features", summary="测试", content="测试内容")
        assert not result["success"], "归档项目添加条目应该失败"
        assert "已归档" in result["error"]

        # 尝试更新条目（也应该因项目不存在而失败）
        result = memory.update_item(project_id, "features", "fake_id", summary="新摘要")
        assert not result["success"]

        # 尝试删除条目
        result = memory.delete_item(project_id, "features", "fake_id")
        assert not result["success"]

        print("  ✓ 归档项目数据操作拦截测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_nonexistent_project():
    """测试归档不存在的项目."""
    print("测试: 归档不存在的项目...")
    temp_dir, memory = _setup_memory()
    try:
        result = memory.remove_project("nonexistent-id", mode="archive")
        assert not result["success"]
        assert "不存在" in result["error"]

        print("  ✓ 归档不存在项目测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delete_nonexistent_project():
    """测试永久删除不存在的项目."""
    print("测试: 永久删除不存在的项目...")
    temp_dir, memory = _setup_memory()
    try:
        result = memory.remove_project("nonexistent-id", mode="delete")
        assert not result["success"]
        assert "不存在" in result["error"]

        print("  ✓ 永久删除不存在项目测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_invalid_mode():
    """测试无效的 mode 参数."""
    print("测试: 无效的 mode 参数...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "模式测试")

        result = memory.remove_project(project_id, mode="invalid")
        assert not result["success"]
        assert "无效的 mode" in result["error"]

        # 确保项目未被影响
        project_data = memory._load_project(project_id)
        assert project_data is not None, "项目不应被删除"

        print("  ✓ 无效 mode 测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive_cleans_cache():
    """测试归档后缓存被清理."""
    print("测试: 归档后缓存清理...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "缓存测试")

        # 加载项目到缓存
        memory._load_project(project_id)
        assert project_id in memory._project_data_cache

        # 归档
        result = memory.remove_project(project_id, mode="archive")
        assert result["success"]

        # 验证缓存已清理
        assert project_id not in memory._projects_cache
        assert project_id not in memory._project_data_cache

        print("  ✓ 归档缓存清理测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_is_project_archived():
    """测试 _is_project_archived 方法."""
    print("测试: _is_project_archived 方法...")
    temp_dir, memory = _setup_memory()
    try:
        project_id = _register_project(memory, "检查归档测试")

        # 未归档
        assert not memory._is_project_archived(project_id), "项目不应该标记为已归档"

        # 归档
        memory.remove_project(project_id, mode="archive")

        # 已归档
        assert memory._is_project_archived(project_id), "项目应该标记为已归档"

        # 不存在的项目
        assert not memory._is_project_archived("nonexistent-id")

        print("  ✓ _is_project_archived 测试通过")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# 运行所有测试
if __name__ == "__main__":
    tests = [
        test_archive_project_success,
        test_archive_project_generates_meta_json,
        test_delete_project_permanent,
        test_archive_already_archived_project,
        test_list_projects_hides_archived,
        test_list_projects_shows_archived,
        test_data_operations_blocked_for_archived,
        test_archive_nonexistent_project,
        test_delete_nonexistent_project,
        test_invalid_mode,
        test_archive_cleans_cache,
        test_is_project_archived,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} 失败: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 个")
    if failed == 0:
        print("全部测试通过!")
    else:
        sys.exit(1)
