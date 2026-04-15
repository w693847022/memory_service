#!/usr/bin/env python3
"""测试 status/severity 参数修复."""

import sys
import os
import asyncio
import tempfile
import shutil
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService


@pytest.mark.asyncio
async def test_status_severity_update():
    """测试 status 和 severity 参数能否正确更新."""
    print("测试: status/severity 参数更新...")

    temp_dir = tempfile.mkdtemp()
    try:
        os.environ["MCP_STORAGE_DIR"] = temp_dir
        storage = Storage()
        service = ProjectService(storage)

        # 1. 注册项目
        result = await service.register_project(
            name="测试项目",
            path="/tmp/test",
            summary="测试摘要",
            tags=["test"]
        )
        assert result["success"], f"注册项目失败: {result}"
        project_id = result["data"]["project_id"]
        print(f"  ✓ 项目注册成功: {project_id}")

        # 2. 添加一个 fix（必须提供 status）
        result = await service.add_item(
            project_id=project_id,
            group="fixes",
            content="修复内容",
            summary="修复摘要",
            status="pending",
            severity="high",
            tags=["bug", "fix"]
        )
        assert result["success"], f"添加 fix 失败: {result}"
        fix_id = result["data"]["item_id"]
        print(f"  ✓ Fix 添加成功: {fix_id}")

        # 3. 验证初始状态
        project_data = await storage.get_project_data(project_id)
        fix = next((item for item in project_data.groups.get("fixes", []) if item.id == fix_id), None)
        assert fix is not None, "找不到 fix 条目"
        print(f"  ✓ 初始状态: fix 条目字段: {list(fix.model_dump().keys())}")
        assert fix.status == "pending", f"初始状态应为 pending, 实际为 {fix.status}"
        assert fix.severity == "high", f"初始严重程度应为 high, 实际为 {fix.severity}"
        print(f"  ✓ 初始状态验证: status={fix.status}, severity={fix.severity}")

        # 4. 只更新 status
        result = await service.update_item(
            project_id=project_id,
            group="fixes",
            item_id=fix_id,
            status="in_progress"
        )
        assert result["success"], f"更新 status 失败: {result}"
        print(f"  ✓ Status 更新成功")

        # 5. 验证 status 已更新，severity 未改变
        project_data = await storage.get_project_data(project_id)
        fix = next((item for item in project_data.groups.get("fixes", []) if item.id == fix_id), None)
        assert fix is not None, "找不到 fix 条目"
        assert fix.status == "in_progress", f"status 应为 in_progress, 实际为 {fix.status}"
        assert fix.severity == "high", f"severity 应保持 high, 实际为 {fix.severity}"
        print(f"  ✓ 验证通过: status={fix.status}, severity={fix.severity}")

        # 6. 同时更新 status 和 severity
        result = await service.update_item(
            project_id=project_id,
            group="fixes",
            item_id=fix_id,
            status="completed",
            severity="low"
        )
        assert result["success"], f"更新 status 和 severity 失败: {result}"
        print(f"  ✓ Status 和 Severity 同时更新成功")

        # 7. 验证两个字段都已更新
        project_data = await storage.get_project_data(project_id)
        fix = next((item for item in project_data.groups.get("fixes", []) if item.id == fix_id), None)
        assert fix is not None, "找不到 fix 条目"
        assert fix.status == "completed", f"status 应为 completed, 实际为 {fix.status}"
        assert fix.severity == "low", f"severity 应为 low, 实际为 {fix.severity}"
        print(f"  ✓ 最终验证通过: status={fix.status}, severity={fix.severity}")

        print("\n✅ 所有测试通过! status/severity 参数修复有效!")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        if "MCP_STORAGE_DIR" in os.environ:
            del os.environ["MCP_STORAGE_DIR"]


if __name__ == "__main__":
    try:
        asyncio.run(test_status_severity_update())
        sys.exit(0)
    except Exception:
        sys.exit(1)
