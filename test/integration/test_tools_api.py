#!/usr/bin/env python3
"""MCP 工具接口调用测试.

测试 features.tools 中的所有 MCP 工具接口实际调用。
"""

import sys
import os
import tempfile
import shutil
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class ToolsApiTest:
    """MCP 工具接口测试类."""

    def __init__(self):
        self.temp_dir = None
        self.original_storage = None
        self.project_id = None
        self.feature_id = None
        self.fix_id = None

    def setup(self):
        """设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_storage = os.environ.get("MCP_STORAGE_DIR")
        os.environ["MCP_STORAGE_DIR"] = self.temp_dir

    def cleanup(self):
        """清理测试环境."""
        if self.original_storage is not None:
            os.environ["MCP_STORAGE_DIR"] = self.original_storage
        elif "MCP_STORAGE_DIR" in os.environ:
            del os.environ["MCP_STORAGE_DIR"]
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def parse_response(self, response_str):
        """解析 JSON 响应."""
        return json.loads(response_str)

    def call_with_stats(self, func, *args, **kwargs):
        """调用函数，自动 patch call_stats."""
        # 实际上不需要 patch call_stats，因为测试环境隔离
        return func(*args, **kwargs)

    def run_all_tests(self):
        """运行所有接口测试."""
        print("=" * 60)
        print("MCP 工具接口调用测试")
        print("=" * 60)
        print()

        try:
            self.setup()

            # 1. project_register
            self.test_project_register()
            print()

            # 2. project_list
            self.test_project_list()
            print()

            # 3. project_get
            self.test_project_get()
            print()

            # 4. project_groups_list
            self.test_project_groups_list()
            print()

            # 5. project_add
            self.test_project_add()
            print()

            # 6. project_update
            self.test_project_update()
            print()

            # 6.5. project_update status/severity
            self.test_project_update_status_severity()
            print()

            # 7. project_delete
            self.test_project_delete()
            print()

            # 8. tag_register
            self.test_tag_register()
            print()

            # 9. tag_update
            self.test_tag_update()
            print()

            # 10. tag_delete
            self.test_tag_delete()
            print()

            # 11. tag_merge
            self.test_tag_merge()
            print()

            # 12. project_item_tag_manage
            self.test_project_item_tag_manage()
            print()

            # 13. project_tags_info
            self.test_project_tags_info()
            print()

            # 14. project_rename
            self.test_project_rename()
            print()

            # 15. project_stats
            self.test_project_stats()
            print()

            # 16. stats_summary
            self.test_stats_summary()
            print()

            # 17. stats_cleanup
            self.test_stats_cleanup()
            print()

            print("=" * 60)
            print("所有接口测试通过!")
            print("=" * 60)
            return True

        except AssertionError as e:
            print(f"  ✗ 测试失败: {e}")
            return False
        except Exception as e:
            print(f"  ✗ 测试错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()

    def test_project_register(self):
        """测试 project_register 接口."""
        print("测试: project_register...")

        from mcp_server.tools import project_register

        result = self.call_with_stats(project_register, name="测试项目", path="/tmp/test", summary="测试摘要", tags="api,test")
        resp = self.parse_response(result)

        assert resp["success"], f"注册失败: {resp}"
        assert "project_id" in resp["data"], f"缺少 project_id: {resp}"
        self.project_id = resp["data"]["project_id"]
        print(f"  ✓ project_register 测试通过 (project_id: {self.project_id})")

    def test_project_list(self):
        """测试 project_list 接口."""
        print("测试: project_list...")

        from mcp_server.tools import project_list, project_register

        # 注册额外项目
        self.call_with_stats(project_register, name="项目A", path="/tmp/a", tags="a")
        self.call_with_stats(project_register, name="项目B", path="/tmp/b", tags="b")

        result = self.call_with_stats(project_list)
        resp = self.parse_response(result)

        assert resp["success"], f"获取列表失败: {resp}"
        assert resp["data"]["total"] == 3, f"项目数量错误: {resp['data']['total']}"
        print(f"  ✓ project_list 测试通过 (共 {resp['data']['total']} 个项目)")

    def test_project_get(self):
        """测试 project_get 接口."""
        print("测试: project_get...")

        from mcp_server.tools import project_get, project_add

        # 添加数据
        self.call_with_stats(project_add, self.project_id, group="features", content="功能内容", summary="功能摘要", status="pending", tags="api")

        # 获取整个项目
        result = self.call_with_stats(project_get, self.project_id)
        resp = self.parse_response(result)
        assert resp["success"], f"获取项目失败: {resp}"

        # 获取分组列表
        result = self.call_with_stats(project_get, self.project_id, group_name="features")
        resp = self.parse_response(result)
        assert resp["success"], f"获取分组失败: {resp}"

        print(f"  ✓ project_get 测试通过")

    def test_project_groups_list(self):
        """测试 project_groups_list 接口."""
        print("测试: project_groups_list...")

        from mcp_server.tools import project_groups_list

        result = self.call_with_stats(project_groups_list, self.project_id)
        resp = self.parse_response(result)

        assert resp["success"], f"获取分组失败: {resp}"
        assert "groups" in resp["data"], f"缺少 groups: {resp}"
        print(f"  ✓ project_groups_list 测试通过")

    def test_project_add(self):
        """测试 project_add 接口 (features/fixes/notes/standards)."""
        print("测试: project_add...")

        from mcp_server.tools import project_add, tag_register

        # 先注册所有需要的标签
        for tag in ["api", "bug", "idea", "style"]:
            self.call_with_stats(tag_register, self.project_id, tag_name=tag, summary=f"{tag} 标签")

        # 添加 feature
        result = self.call_with_stats(project_add, self.project_id, group="features", content="功能内容", summary="功能摘要", status="pending", tags="api")
        resp = self.parse_response(result)
        assert resp["success"], f"添加 feature 失败: {resp}"
        self.feature_id = resp["data"]["item_id"]

        # 添加 fix
        result = self.call_with_stats(project_add, self.project_id, group="fixes", content="修复内容", summary="修复摘要", status="pending", tags="bug", severity="high")
        resp = self.parse_response(result)
        assert resp["success"], f"添加 fix 失败: {resp}"
        self.fix_id = resp["data"]["item_id"]

        # 添加 note
        result = self.call_with_stats(project_add, self.project_id, group="notes", content="笔记内容", summary="笔记摘要", tags="idea")
        resp = self.parse_response(result)
        assert resp["success"], f"添加 note 失败: {resp}"

        # 添加 standard
        result = self.call_with_stats(project_add, self.project_id, group="standards", content="规范内容", summary="规范摘要", tags="style")
        resp = self.parse_response(result)
        assert resp["success"], f"添加 standard 失败: {resp}"

        print(f"  ✓ project_add 测试通过 (feature_id: {self.feature_id}, fix_id: {self.fix_id})")

    def test_project_update(self):
        """测试 project_update 接口."""
        print("测试: project_update...")

        from mcp_server.tools import project_update

        result = self.call_with_stats(project_update, self.project_id, group="features", item_id=self.feature_id, summary="更新后的摘要", status="completed")
        resp = self.parse_response(result)

        assert resp["success"], f"更新失败: {resp}"
        print(f"  ✓ project_update 测试通过")

    def test_project_delete(self):
        """测试 project_delete 接口."""
        print("测试: project_delete...")

        from mcp_server.tools import project_delete

        result = self.call_with_stats(project_delete, self.project_id, group="features", item_id=self.feature_id)
        resp = self.parse_response(result)

        assert resp["success"], f"删除失败: {resp}"
        assert resp["data"]["deleted"] is True, f"删除标记错误: {resp}"
        print(f"  ✓ project_delete 测试通过")

    def test_tag_register(self):
        """测试 tag_register 接口."""
        print("测试: tag_register...")

        from mcp_server.tools import tag_register

        result = self.call_with_stats(tag_register, self.project_id, tag_name="newtag", summary="新标签描述", aliases="nt,new")
        resp = self.parse_response(result)

        assert resp["success"], f"注册标签失败: {resp}"
        print(f"  ✓ tag_register 测试通过")

    def test_tag_update(self):
        """测试 tag_update 接口."""
        print("测试: tag_update...")

        from mcp_server.tools import tag_register, tag_update

        self.call_with_stats(tag_register, self.project_id, tag_name="updatetag", summary="原始描述")
        result = self.call_with_stats(tag_update, self.project_id, tag_name="updatetag", summary="更新后的描述")
        resp = self.parse_response(result)

        assert resp["success"], f"更新标签失败: {resp}"
        print(f"  ✓ tag_update 测试通过")

    def test_tag_delete(self):
        """测试 tag_delete 接口."""
        print("测试: tag_delete...")

        from mcp_server.tools import tag_register, tag_delete

        self.call_with_stats(tag_register, self.project_id, tag_name="deletetag", summary="删除标签")
        result = self.call_with_stats(tag_delete, self.project_id, tag_name="deletetag")
        resp = self.parse_response(result)

        assert resp["success"], f"删除标签失败: {resp}"
        print(f"  ✓ tag_delete 测试通过")

    def test_tag_merge(self):
        """测试 tag_merge 接口."""
        print("测试: tag_merge...")

        from mcp_server.tools import tag_register, tag_merge

        self.call_with_stats(tag_register, self.project_id, tag_name="oldtag", summary="旧标签")
        result = self.call_with_stats(tag_merge, self.project_id, old_tag="oldtag", new_tag="newtag")
        resp = self.parse_response(result)

        assert resp["success"], f"合并标签失败: {resp}"
        print(f"  ✓ tag_merge 测试通过")

    def test_project_item_tag_manage(self):
        """测试 project_item_tag_manage 接口."""
        print("测试: project_item_tag_manage...")

        from mcp_server.tools import project_item_tag_manage, tag_register, project_add

        # 先注册需要的标签
        for tag in ["added", "updated"]:
            self.call_with_stats(tag_register, self.project_id, tag_name=tag, summary=f"{tag} 描述")

        # 添加 feature（因为上一个测试删除了）
        result = self.call_with_stats(project_add, self.project_id, group="features", content="功能内容", summary="功能摘要", status="pending", tags="api")
        resp = self.parse_response(result)
        assert resp["success"], f"添加 feature 失败: {resp}"
        feature_id = resp["data"]["item_id"]

        # add tag
        result = self.call_with_stats(project_item_tag_manage, self.project_id, group_name="features", item_id=feature_id, operation="add", tag="added")
        resp = self.parse_response(result)
        assert resp["success"], f"添加标签失败: {resp}"

        # set tags
        result = self.call_with_stats(project_item_tag_manage, self.project_id, group_name="features", item_id=feature_id, operation="set", tags="api,updated")
        resp = self.parse_response(result)
        assert resp["success"], f"设置标签失败: {resp}"

        # remove tag
        result = self.call_with_stats(project_item_tag_manage, self.project_id, group_name="features", item_id=feature_id, operation="remove", tag="api")
        resp = self.parse_response(result)
        assert resp["success"], f"移除标签失败: {resp}"

        print(f"  ✓ project_item_tag_manage 测试通过")

    def test_project_tags_info(self):
        """测试 project_tags_info 接口."""
        print("测试: project_tags_info...")

        from mcp_server.tools import project_tags_info, tag_register

        self.call_with_stats(tag_register, self.project_id, tag_name="infotag", summary="信息标签")

        result = self.call_with_stats(project_tags_info, self.project_id)
        resp = self.parse_response(result)
        assert resp["success"], f"获取标签信息失败: {resp}"

        result = self.call_with_stats(project_tags_info, self.project_id, group_name="features")
        resp = self.parse_response(result)
        assert resp["success"], f"按分组获取标签失败: {resp}"

        print(f"  ✓ project_tags_info 测试通过")

    def test_project_rename(self):
        """测试 project_rename 接口."""
        print("测试: project_rename...")

        from mcp_server.tools import project_rename

        result = self.call_with_stats(project_rename, self.project_id, new_name="新项目名")
        resp = self.parse_response(result)

        assert resp["success"], f"重命名失败: {resp}"
        print(f"  ✓ project_rename 测试通过")

    def test_project_stats(self):
        """测试 project_stats 接口."""
        print("测试: project_stats...")

        from mcp_server.tools import project_stats

        result = self.call_with_stats(project_stats)
        resp = self.parse_response(result)

        assert resp["success"], f"获取统计失败: {resp}"
        print(f"  ✓ project_stats 测试通过")

    def test_stats_summary(self):
        """测试 stats_summary 接口."""
        print("测试: stats_summary...")

        from mcp_server.tools import stats_summary

        # 测试无类型（获取所有）
        result = self.call_with_stats(stats_summary)
        resp = self.parse_response(result)
        assert resp["success"], f"获取摘要失败: {resp}"

        # 测试 tool 类型
        result = self.call_with_stats(stats_summary, type="tool")
        resp = self.parse_response(result)
        assert resp["success"], f"获取工具统计失败: {resp}"

        print(f"  ✓ stats_summary 测试通过")

    def test_stats_cleanup(self):
        """测试 stats_cleanup 接口."""
        print("测试: stats_cleanup...")

        from mcp_server.tools import stats_cleanup

        result = self.call_with_stats(stats_cleanup, retention_days=7)
        resp = self.parse_response(result)

        assert resp["success"], f"清理统计失败: {resp}"
        print(f"  ✓ stats_cleanup 测试通过")

    def test_project_update_status_severity(self):
        """测试 project_update 接口的 status 和 severity 参数更新."""
        print("测试: project_update status/severity...")

        from mcp_server.tools import project_add, project_update, project_get

        # 1. 创建一个 fix 类型的条目（需要 severity）
        result = self.call_with_stats(
            project_add,
            self.project_id,
            group="fixes",
            content="修复内容",
            summary="修复摘要",
            severity="high",
            tags="bug,fix"
        )
        resp = self.parse_response(result)
        assert resp["success"], f"添加 fix 失败: {resp}"
        fix_id = resp["data"]["item_id"]

        # 2. 验证初始状态
        result = self.call_with_stats(
            project_get,
            self.project_id,
            group="fixes",
            item_id=fix_id
        )
        resp = self.parse_response(result)
        assert resp["success"], f"获取 fix 失败: {resp}"
        assert resp["data"]["item"]["status"] == "pending", f"初始状态应为 pending: {resp['data']['item']}"
        assert resp["data"]["item"]["severity"] == "high", f"初始严重程度应为 high: {resp['data']['item']}"

        # 3. 只更新 status
        result = self.call_with_stats(
            project_update,
            self.project_id,
            group="fixes",
            item_id=fix_id,
            status="in_progress"
        )
        resp = self.parse_response(result)
        assert resp["success"], f"更新 status 失败: {resp}"

        # 4. 验证 status 已更新，severity 未改变
        result = self.call_with_stats(
            project_get,
            self.project_id,
            group="fixes",
            item_id=fix_id
        )
        resp = self.parse_response(result)
        assert resp["success"], f"获取更新后的 fix 失败: {resp}"
        assert resp["data"]["item"]["status"] == "in_progress", f"status 应为 in_progress: {resp['data']['item']}"
        assert resp["data"]["item"]["severity"] == "high", f"severity 应保持 high: {resp['data']['item']}"

        # 5. 同时更新 status 和 severity
        result = self.call_with_stats(
            project_update,
            self.project_id,
            group="fixes",
            item_id=fix_id,
            status="completed",
            severity="low"
        )
        resp = self.parse_response(result)
        assert resp["success"], f"更新 status 和 severity 失败: {resp}"

        # 6. 验证两个字段都已更新
        result = self.call_with_stats(
            project_get,
            self.project_id,
            group="fixes",
            item_id=fix_id
        )
        resp = self.parse_response(result)
        assert resp["success"], f"获取最终状态失败: {resp}"
        assert resp["data"]["item"]["status"] == "completed", f"status 应为 completed: {resp['data']['item']}"
        assert resp["data"]["item"]["severity"] == "low", f"severity 应为 low: {resp['data']['item']}"

        print(f"  ✓ project_update status/severity 测试通过")


def run_all_tests():
    """运行所有接口测试."""
    test = ToolsApiTest()
    return test.run_all_tests()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
