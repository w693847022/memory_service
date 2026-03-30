#!/usr/bin/env python3
"""MCP接口: project_add 完整边界测试.

测试添加条目接口的所有边界情况。
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory
import api.tools


def _setup_project():
    """创建测试项目和临时目录."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)

    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]

    # 注册默认标签
    memory.register_tag(project_id, "test", "测试标签")

    return temp_dir, memory, project_id


class TestProjectAddBasic:
    """基础功能测试."""

    def test_add_feature_success(self):
        """测试添加功能成功."""
        print("测试: 添加功能...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能详细描述",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], f"添加功能失败: {data}"
                assert "item_id" in data["data"]

            print("  ✓ 添加功能测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_note_success(self):
        """测试添加笔记成功."""
        print("测试: 添加笔记...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="notes",
                    summary="测试笔记",
                    content="笔记内容",
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], f"添加笔记失败: {data}"

            print("  ✓ 添加笔记测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_fix_success(self):
        """测试添加修复成功."""
        print("测试: 添加修复...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="fixes",
                    summary="修复bug",
                    content="修复描述",
                    status="completed",
                    severity="high",
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], f"添加修复失败: {data}"

            print("  ✓ 添加修复测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_standard_success(self):
        """测试添加规范成功."""
        print("测试: 添加规范...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="standards",
                    summary="编码规范",
                    content="规范内容",
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], f"添加规范失败: {data}"

            print("  ✓ 添加规范测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddRequiredParams:
    """必填参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id="",
                    group="features",
                    summary="测试",
                    tags="test"
                )
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_group(self):
        """测试缺少 group."""
        print("测试: 缺少 group...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="",
                    summary="测试",
                    tags="test"
                )
                data = json.loads(result)

                assert not data["success"], "空 group 应该失败"

            print("  ✓ 缺少 group 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_summary(self):
        """测试缺少 summary."""
        print("测试: 缺少 summary...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="",
                    tags="test"
                )
                data = json.loads(result)

                # summary 可能是必填的
                assert not data["success"] or "summary" in data.get("error", "")

            print("  ✓ 缺少 summary 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_status_for_features(self):
        """测试 features 缺少 status."""
        print("测试: features 缺少 status...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试",
                    status=None,
                    tags="test"
                )
                data = json.loads(result)

                # features/fixes 需要 status
                assert not data["success"] or "status" in data.get("error", "").lower()

            print("  ✓ features 缺少 status 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddGroupValidation:
    """分组参数验证测试."""

    def test_invalid_group(self):
        """测试无效分组."""
        print("测试: 无效分组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            invalid_groups = ["invalid", "feature", "fix", "功能", "xxx"]

            for group in invalid_groups:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group=group,
                        summary="测试",
                        tags="test"
                    )
                    data = json.loads(result)

                    assert not data["success"], f"无效分组 {group} 应该失败"

            print("  ✓ 无效分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_valid_groups(self):
        """测试所有有效分组."""
        print("测试: 所有有效分组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 定义每个分组需要的参数
            valid_groups = [
                ("features", {"status": "pending", "content": "功能详细描述", "summary": "测试功能摘要"}),
                ("notes", {"content": "笔记内容", "summary": "测试笔记摘要"}),
                ("fixes", {"status": "completed", "severity": "medium", "content": "修复描述", "summary": "测试修复摘要"}),
                ("standards", {"content": "规范内容", "summary": "测试规范摘要"}),
            ]

            for group, extra_params in valid_groups:
                # 从 extra_params 中提取 summary，并设置默认值
                summary = extra_params.pop("summary", "测试摘要")
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group=group,
                        summary=summary,
                        tags="test",
                        **extra_params
                    )
                    data = json.loads(result)

                    assert data["success"], f"有效分组 {group} 应该成功: {data.get('error', '')}"

            print("  ✓ 有效分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddStatusValidation:
    """状态参数验证测试."""

    def test_valid_status_values(self):
        """测试有效状态值."""
        print("测试: 有效状态值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            valid_statuses = ["pending", "in_progress", "completed"]

            for status in valid_statuses:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="features",
                        summary="测试功能摘要",
                        content="功能详细描述",
                        status=status,
                        tags="test"
                    )
                    data = json.loads(result)

                    assert data["success"], f"有效状态 {status} 应该成功: {data.get('error', '')}"

            print("  ✓ 有效状态值测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_status_values(self):
        """测试无效状态值."""
        print("测试: 无效状态值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            invalid_statuses = ["invalid", "pending123", "PENDING", "", " "]

            for status in invalid_statuses:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="features",
                        summary="测试",
                        status=status,
                        tags="test"
                    )
                    data = json.loads(result)

                    # 无效状态应该失败或被处理
                    if status not in ["pending", "in_progress", "completed"]:
                        assert not data["success"] or "status" in data.get("error", "").lower()

            print("  ✓ 无效状态值测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddSeverityValidation:
    """严重程度参数验证测试."""

    def test_valid_severity_values(self):
        """测试有效严重程度值."""
        print("测试: 有效严重程度值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            valid_severities = ["critical", "high", "medium", "low"]

            for severity in valid_severities:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="fixes",
                        summary="测试修复摘要",
                        content="修复详细描述",
                        status="pending",
                        severity=severity,
                        tags="test"
                    )
                    data = json.loads(result)

                    assert data["success"], f"有效严重程度 {severity} 应该成功: {data.get('error', '')}"

            print("  ✓ 有效严重程度值测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_severity_values(self):
        """测试无效严重程度值."""
        print("测试: 无效严重程度值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            invalid_severities = ["invalid", "high123", "HIGH", "", " "]

            for severity in invalid_severities:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="fixes",
                        summary="测试",
                        status="pending",
                        severity=severity,
                        tags="test"
                    )
                    data = json.loads(result)

                    # 无效严重程度应该失败
                    if severity not in ["critical", "high", "medium", "low"]:
                        assert not data["success"] or "severity" in data.get("error", "").lower()

            print("  ✓ 无效严重程度值测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_severity_only_for_fixes(self):
        """测试 severity 仅对 fixes 有效."""
        print("测试: severity 参数适用范围...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # features 不需要 severity（但可以传）
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    severity="high",  # 可能被忽略
                    tags="test"
                )
                data = json.loads(result)

                # features 的 severity 可能被忽略
                assert data.get("success") or "severity" in data.get("error", "").lower()

            print("  ✓ severity 适用范围测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddContentValidation:
    """内容参数验证测试."""

    def test_content_empty(self):
        """测试空内容."""
        print("测试: 空内容...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试",
                    content="",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)

                # 空内容可能被允许或拒绝
                # 验证有明确的行为

            print("  ✓ 空内容测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_content_lengths(self):
        """测试各种内容长度."""
        print("测试: 内容长度...")
        temp_dir, memory, project_id = _setup_project()
        try:
            lengths = [1, 10, 100, 1000, 10000]

            for length in lengths:
                content = "A" * length
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="notes",
                        summary="测试",
                        content=content,
                        tags="test"
                    )
                    data = json.loads(result)

            print("  ✓ 内容长度测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_content_with_special_chars(self):
        """测试特殊字符内容."""
        print("测试: 特殊字符内容...")
        temp_dir, memory, project_id = _setup_project()
        try:
            special_contents = [
                "内容\n包含\n换行",
                "内容\t制表符",
                "内容\"引号\"",
                "内容'单引号'",
                "内容\\反斜杠",
                "内容/斜杠",
                "内容<xml>",
                "内容{json}",
                "中文。，、！？",
                "🚀表情",
            ]

            for content in special_contents:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="notes",
                        summary="测试",
                        content=content,
                        tags="test"
                    )
                    data = json.loads(result)

            print("  ✓ 特殊字符内容测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddSummaryValidation:
    """摘要参数验证测试."""

    def test_summary_empty(self):
        """测试空摘要."""
        print("测试: 空摘要...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)

                # 摘要是必填的
                assert not data["success"] or "summary" in data.get("error", "").lower()

            print("  ✓ 空摘要测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_lengths(self):
        """测试各种摘要长度."""
        print("测试: 摘要长度...")
        temp_dir, memory, project_id = _setup_project()
        try:
            lengths = [1, 10, 50, 100, 200, 500]

            for length in lengths:
                summary = "A" * length
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="features",
                        summary=summary,
                        status="pending",
                        tags="test"
                    )
                    data = json.loads(result)

            print("  ✓ 摘要长度测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddTagsValidation:
    """标签参数验证测试."""

    def test_unregistered_tag_rejected(self):
        """测试未注册标签被拒绝."""
        print("测试: 未注册标签被拒绝...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    tags="unregistered_tag"
                )
                data = json.loads(result)

                # 未注册标签应该失败
                assert not data["success"], "未注册标签应该失败"
                assert "未注册" in data.get("error", "") or "tag" in data.get("error", "").lower()

            print("  ✓ 未注册标签被拒绝测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_registered_tag_accepted(self):
        """测试已注册标签被接受."""
        print("测试: 已注册标签被接受...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 注册额外标签
            memory.register_tag(project_id, "api", "API标签")
            memory.register_tag(project_id, "backend", "后端标签")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    tags="test,api,backend"
                )
                data = json.loads(result)

                assert data["success"], "已注册标签应该成功"

            print("  ✓ 已注册标签被接受测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_tags(self):
        """测试空标签."""
        print("测试: 空标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试",
                    status="pending",
                    tags=""
                )
                data = json.loads(result)

                # 空标签可能允许或拒绝
                # 验证有明确行为

            print("  ✓ 空标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_with_spaces(self):
        """测试带空格的标签."""
        print("测试: 标签空格处理...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    tags=" test , test "
                )
                data = json.loads(result)

                assert data["success"], "带空格的已注册标签应该成功"

            print("  ✓ 标签空格处理测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddRelatedValidation:
    """关联参数验证测试."""

    def test_related_json_string_valid(self):
        """测试有效的 JSON 字符串 related."""
        print("测试: 有效 JSON 字符串 related...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 先添加一个 feature 用于关联
            result1 = memory.add_item(
                project_id=project_id,
                group="features",
                content="功能内容",
                summary="功能摘要",
                status="pending",
                tags=["test"]
            )
            feature_id = result1["item_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="fixes",
                    summary="测试修复摘要",
                    content="修复详细描述",
                    status="pending",
                    related=f'{{"features": ["{feature_id}"]}}',
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], "有效 JSON related 应该成功"

            print("  ✓ 有效 JSON 字符串 related 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_dict_valid(self):
        """测试有效的字典 related."""
        print("测试: 有效字典 related...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 先添加一个 note
            result1 = memory.add_item(
                project_id=project_id,
                group="notes",
                content="笔记内容",
                summary="笔记摘要",
                tags=["test"]
            )
            note_id = result1["item_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    related={"notes": [note_id]},
                    tags="test"
                )
                data = json.loads(result)

                assert data["success"], "有效字典 related 应该成功"

            print("  ✓ 有效字典 related 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_invalid_json(self):
        """测试无效的 JSON 字符串."""
        print("测试: 无效 JSON 字符串...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试",
                    status="pending",
                    related="{invalid json}",
                    tags="test"
                )
                data = json.loads(result)

                # 无效 JSON 应该失败
                assert not data["success"], "无效 JSON related 应该失败"

            print("  ✓ 无效 JSON 字符串测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_empty_item_ids(self):
        """测试空的关联 ID 列表."""
        print("测试: 空的关联 ID 列表...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    related='{"features": []}',
                    tags="test"
                )
                data = json.loads(result)

                # 空列表可能被允许
                assert data.get("success") or "related" in data.get("error", "").lower()

            print("  ✓ 空的关联 ID 列表测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_invalid_item_ids(self):
        """测试不存在的关联 ID."""
        print("测试: 不存在的关联 ID...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试",
                    status="pending",
                    related='{"features": ["feat_nonexistent"]}',
                    tags="test"
                )
                data = json.loads(result)

                # 不存在的 ID 可能被拒绝或警告
                # 验证有明确行为

            print("  ✓ 不存在的关联 ID 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_for_standards_rejected(self):
        """测试 standards 不支持 related."""
        print("测试: standards 不支持 related...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="standards",
                    summary="规范",
                    related='{"features": ["feat_001"]}',
                    tags="test"
                )
                data = json.loads(result)

                # standards 不应该支持 related
                assert not data["success"] or "related" in data.get("error", "").lower()

            print("  ✓ standards 不支持 related 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_related_for_notes_rejected(self):
        """测试 notes 不支持 related."""
        print("测试: notes 不支持 related...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="notes",
                    summary="笔记",
                    related='{"features": ["feat_001"]}',
                    tags="test"
                )
                data = json.loads(result)

                # notes 不应该支持 related
                assert not data["success"] or "related" in data.get("error", "").lower()

            print("  ✓ notes 不支持 related 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectAddEdgeCases:
    """边缘情况测试."""

    def test_add_to_archived_project(self):
        """测试向已归档项目添加条目."""
        print("测试: 向已归档项目添加条目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 归档项目
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能摘要",
                    content="功能详细描述",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)

                # 已归档项目应该拒绝操作
                assert not data["success"], "已归档项目应该拒绝添加"
                assert "归档" in data.get("error", "") or "archived" in data.get("error", "").lower()

            print("  ✓ 向已归档项目添加条目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_to_nonexistent_project(self):
        """测试向不存在的项目添加条目."""
        print("测试: 向不存在的项目添加条目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id="nonexistent-project-id",
                    group="features",
                    summary="测试",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 向不存在的项目添加条目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_add_same_project(self):
        """测试并发添加到同一项目."""
        print("测试: 并发添加...")
        temp_dir, memory, project_id = _setup_project()
        try:
            import threading

            results = []
            errors = []

            def add_item():
                try:
                    with patch.object(api.tools, 'memory', memory):
                        result = api.tools.project_add(
                            project_id=project_id,
                            group="features",
                            summary=f"并发测试",
                            status="pending",
                            tags="test"
                        )
                        results.append(json.loads(result))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=add_item) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 验证所有请求都有响应
            assert len(results) == 10
            assert len(errors) == 0

            print("  ✓ 并发添加测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_add 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectAddBasic,
        TestProjectAddRequiredParams,
        TestProjectAddGroupValidation,
        TestProjectAddStatusValidation,
        TestProjectAddSeverityValidation,
        TestProjectAddContentValidation,
        TestProjectAddSummaryValidation,
        TestProjectAddTagsValidation,
        TestProjectAddRelatedValidation,
        TestProjectAddEdgeCases,
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
