#!/usr/bin/env python3
"""API层版本控制集成测试."""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService
from business.api.projects import init_services, router
from fastapi import FastAPI


@pytest.mark.asyncio
class TestApiVersionControl:
    """API层版本控制测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.tag_service = None
        self.app = None
        self.project_id = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()

        # 初始化存储和服务
        self.storage = Storage(storage_dir=self.temp_dir)
        self.project_service = ProjectService(self.storage)
        self.tag_service = TagService(self.storage)

        # 初始化API服务
        init_services(self.storage, self.project_service, self.tag_service)

        # 创建测试应用
        self.app = FastAPI()
        self.app.include_router(router)

    async def test_api_version_control(self):
        """测试API层版本控制功能."""
        await self.async_setup_method()

        # 使用 httpx AsyncClient 替代 TestClient 以支持异步
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 注册测试项目
            register_response = await client.post(
                "/api/projects",
                params={
                    "name": "版本控制测试项目",
                    "summary": "用于测试版本控制功能的项目",
                    "tags": "test,version"
                }
            )
            print(f"注册响应状态码: {register_response.status_code}")
            if register_response.status_code != 200:
                print(f"注册响应内容: {register_response.text}")
            assert register_response.status_code == 200
            project_id = register_response.json()["data"]["project_id"]

            # 添加测试条目
            add_response = await client.post(
                f"/api/projects/{project_id}/items",
                params={"group": "features"},
                json={
                    "summary": "测试功能",
                    "content": "这是一个测试功能",
                    "status": "pending",  # features组需要status参数
                    "tags": "test"
                }
            )
            print(f"添加条目响应状态码: {add_response.status_code}")
            if add_response.status_code != 200:
                print(f"添加条目响应内容: {add_response.text}")
            assert add_response.status_code == 200
            item_id = add_response.json()["data"]["item_id"]
            initial_version = add_response.json()["data"]["item"].get("_v", 1)

            print(f"✓ 创建条目成功，初始版本: {initial_version}")

            # 测试1: 不带版本号的更新（应该成功）
            update_response = await client.put(
                f"/api/projects/{project_id}/items/{item_id}",
                params={"group": "features"},
                json={"summary": "更新后的功能"}
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()["data"]
            new_version = updated_data["item"].get("_v", initial_version + 1)
            assert new_version == initial_version + 1
            print(f"✓ 无版本检查更新成功，版本递增至: {new_version}")

            # 测试2: 带正确版本号的更新（应该成功）
            update_response = await client.put(
                f"/api/projects/{project_id}/items/{item_id}",
                params={"group": "features"},
                json={
                    "summary": "再次更新的功能",
                    "version": new_version
                }
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()["data"]
            newer_version = updated_data["item"].get("_v", new_version + 1)
            assert newer_version == new_version + 1
            print(f"✓ 正确版本号更新成功，版本递增至: {newer_version}")

            # 测试3: 带错误版本号的更新（应该失败，返回409冲突）
            update_response = await client.put(
                f"/api/projects/{project_id}/items/{item_id}",
                params={"group": "features"},
                json={
                    "summary": "冲突的更新",
                    "version": 999  # 错误的版本号
                }
            )
            assert update_response.status_code == 409
            conflict_data = update_response.json()["detail"]
            assert conflict_data["error"] == "version_conflict"
            assert conflict_data["current_version"] == newer_version
            assert conflict_data["expected_version"] == 999
            print(f"✓ 版本冲突检测成功，当前版本: {conflict_data['current_version']}")

            # 验证数据没有被修改
            get_response = await client.get(
                f"/api/projects/{project_id}/items",
                params={
                    "group_name": "features",
                    "item_id": item_id
                }
            )
            assert get_response.status_code == 200
            item_data = get_response.json()["data"]["item"]
            assert item_data["summary"] == "再次更新的功能"
            assert item_data.get("_v", newer_version) == newer_version
            print(f"✓ 冲突后数据未被修改，版本保持: {newer_version}")

            print("✅ 所有API版本控制测试通过!")


# 为了向后兼容，保留同步版本的运行函数
def run_all_tests():
    """运行所有集成测试."""
    print("=" * 60)
    print("API层版本控制集成测试")
    print("=" * 60)
    print()
    print("注意：此测试已转换为异步版本，请使用 pytest 运行")
    print("命令：pytest test/integration/test_version_api.py -v")
    print()


if __name__ == "__main__":
    run_all_tests()
