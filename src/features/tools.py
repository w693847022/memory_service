"""MCP 工具实现模块.

这些函数将在 server.py 中注册为 MCP 工具。
"""

import json
from typing import Optional

# 从 core 模块导入依赖（支持相对和绝对导入）
try:
    from ..core.config import memory, call_stats
    from ..core.utils import track_calls
    from ..models.response import ApiResponse
except ImportError:
    from core.config import memory, call_stats
    from core.utils import track_calls
    from models.response import ApiResponse


# ===================
# Helper Functions
# ===================

def _normalize_group(group: str) -> str:
    """标准化 group 参数.

    支持中英文别名：
    - features: "features", "feature", "功能", "feat"
    - fixes: "fixes", "fix", "修复", "bugfix"
    - notes: "notes", "note", "笔记"
    - standards: "standards", "standard", "规范", "标准"
    """
    group_lower = group.lower().strip()

    # 中文别名映射
    aliases = {
        "features": ["features", "feature", "功能", "feat"],
        "fixes": ["fixes", "fix", "修复", "bugfix"],
        "notes": ["notes", "note", "笔记"],
        "standards": ["standards", "standard", "规范", "标准"]
    }

    for normalized, variants in aliases.items():
        if group_lower in [v.lower() for v in variants]:
            return normalized

    return group_lower  # 返回原值，让调用者处理错误


def _parse_tags(tags_str: str) -> list:
    """解析标签字符串为列表."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def _validate_content_length(content: str, max_tokens: int = 30, min_tokens: int = None) -> tuple[bool, str]:
    """验证内容长度（基于 token 估算）.

    Args:
        content: 要验证的内容
        max_tokens: 最大 token 数
        min_tokens: 最小 token 数（可选）

    Returns:
        (是否有效, 错误信息)
    """
    if not content:
        return False, "内容不能为空"

    # 简化的 token 估算：1 token ≈ 3 字符（中英文混合平均）
    estimated_tokens = len(content) / 3

    # 最小长度验证
    if min_tokens is not None and estimated_tokens < min_tokens:
        return False, f"内容过短：预估 {int(estimated_tokens)} tokens，最小允许 {min_tokens} tokens（约 {min_tokens * 3} 字符）"

    # 最大长度验证
    if estimated_tokens > max_tokens:
        return False, f"内容过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
    return True, ""


def _validate_tag_length(tag: str, max_tokens: int = 10) -> tuple[bool, str]:
    """验证单个标签长度（基于 token 估算）.

    Args:
        tag: 要验证的标签
        max_tokens: 最大 token 数

    Returns:
        (是否有效, 错误信息)
    """
    if not tag:
        return False, "标签不能为空"

    # 简化的 token 估算：1 token ≈ 3 字符
    estimated_tokens = len(tag) / 3

    if estimated_tokens > max_tokens:
        return False, f"标签 '{tag}' 过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
    return True, ""


# ===================
# Project Memory Tools
# ===================

def project_register(name: str, path: str = "", description: str = "", tags: str = "") -> str:
    """注册一个新项目.
    Args:
        name: 项目名称
        path: 项目路径（可选）
        description: 项目描述（可选）
        tags: 项目标签，逗号分隔（可选）
    Returns:
        JSON 格式的注册结果
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = memory.register_project(name, path, description, tag_list)
    response = ApiResponse.from_result(result)
    return response.to_json()


def project_rename(project_id: str, new_name: str) -> str:
    """重命名项目（修改 name 字段并重命名目录）.

    Args:
        project_id: 项目 UUID
        new_name: 新的项目名称

    Returns:
        JSON 格式的操作结果
    """
    result = memory.project_rename(project_id, new_name)

    if result["success"]:
        data = {
            "old_name": result.get("old_name"),
            "new_name": result.get("new_name")
        }
        response = ApiResponse(success=True, data=data, message=result.get("message"))
    else:
        response = ApiResponse(success=False, error=result.get("error"))

    return response.to_json()


def project_list() -> str:
    """列出所有项目.

    Returns:
        JSON 格式的项目列表
    """
    result = memory.list_projects()

    if not result["success"]:
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    data = {
        "total": result["total"],
        "projects": result["projects"]
    }
    response = ApiResponse(success=True, data=data, message=f"共 {result['total']} 个项目")
    return response.to_json()


def project_groups_list(project_id: str) -> str:
    """列出项目的所有分组（功能、笔记、规范）.

    Args:
        project_id: 项目ID

    Returns:
        JSON 格式的分组列表及统计信息
    """
    result = memory.list_groups(project_id)

    if not result["success"]:
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    data = {
        "project_id": project_id,
        "groups": result["groups"]
    }
    response = ApiResponse(success=True, data=data, message="获取分组成功")
    return response.to_json()


def project_tags_info(
    project_id: str,
    group_name: str = "",
    tag_name: str = "",
    unregistered_only: bool = False
) -> str:
    """查询标签信息（统一接口）.

    Args:
        project_id: 项目ID
        group_name: 分组名称 ("features"|"notes"|"fixes"|"standards")，为空则返回所有已注册标签
        tag_name: 标签名称 (为空则返回所有标签)
        unregistered_only: 仅返回未注册标签

    Returns:
        JSON 格式的标签信息
    """
    # 不指定 group_name 时，列出所有已注册标签
    if not group_name:
        result = memory.list_all_registered_tags(project_id)

        if not result["success"]:
            response = ApiResponse(success=False, error=result.get('error', '未知错误'))
            return response.to_json()

        data = {
            "project_id": project_id,
            "total_tags": result["total_tags"],
            "tags": result["tags"]
        }
        response = ApiResponse(success=True, data=data, message=f"共 {result['total_tags']} 个已注册标签")
        return response.to_json()

    if group_name not in ["features", "notes", "fixes", "standards"]:
        response = ApiResponse(success=False, error=f"无效的分组名称: {group_name}")
        return response.to_json()

    # 查询特定标签
    if tag_name:
        result = memory.query_by_tag(project_id, group_name, tag_name)

        if not result["success"]:
            response = ApiResponse(success=False, error=result.get('error', '未知错误'))
            return response.to_json()

        data = {
            "project_id": project_id,
            "group_name": group_name,
            "tag_name": tag_name,
            "total": result["total"],
            "items": result["items"]
        }
        response = ApiResponse(success=True, data=data, message=f"共 {result['total']} 个条目")
        return response.to_json()

    # 仅返回未注册标签
    elif unregistered_only:
        result = memory.list_unregistered_tags(project_id, group_name)

        if not result["success"]:
            response = ApiResponse(success=False, error=result.get('error', '未知错误'))
            return response.to_json()

        data = {
            "project_id": project_id,
            "group_name": group_name,
            "total_tags": result["total_tags"],
            "tags": result["tags"]
        }
        response = ApiResponse(success=True, data=data, message=f"共 {result['total_tags']} 个未注册标签")
        return response.to_json()

    # 返回所有标签
    else:
        result = memory.list_group_tags(project_id, group_name)

        if not result["success"]:
            response = ApiResponse(success=False, error=result.get('error', '未知错误'))
            return response.to_json()

        data = {
            "project_id": project_id,
            "group_name": group_name,
            "total_tags": result["total_tags"],
            "tags": result["tags"]
        }
        response = ApiResponse(success=True, data=data, message=f"共 {result['total_tags']} 个标签")
        return response.to_json()



def _normalize_group(group: str) -> str:
    """标准化 group 参数.

    支持中英文别名：
    - features: "features", "feature", "功能", "feat"
    - fixes: "fixes", "fix", "修复", "bugfix"
    - notes: "notes", "note", "笔记"
    - standards: "standards", "standard", "规范", "标准"
    """
    group_lower = group.lower().strip()

    # 中文别名映射
    aliases = {
        "features": ["features", "feature", "功能", "feat"],
        "fixes": ["fixes", "fix", "修复", "bugfix"],
        "notes": ["notes", "note", "笔记"],
        "standards": ["standards", "standard", "规范", "标准"]
    }

    for normalized, variants in aliases.items():
        if group_lower in [v.lower() for v in variants]:
            return normalized

    return group_lower  # 返回原值，让调用者处理错误


def _parse_tags(tags_str: str) -> list:
    """解析标签字符串为列表."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def _validate_content_length(content: str, max_tokens: int = 30, min_tokens: int = None) -> tuple[bool, str]:
    """验证内容长度（基于 token 估算）.

    Args:
        content: 要验证的内容
        max_tokens: 最大 token 数
        min_tokens: 最小 token 数（可选）

    Returns:
        (是否有效, 错误信息)
    """
    if not content:
        return False, "内容不能为空"

    # 简化的 token 估算：1 token ≈ 3 字符（中英文混合平均）
    estimated_tokens = len(content) / 3

    # 最小长度验证
    if min_tokens is not None and estimated_tokens < min_tokens:
        return False, f"内容过短：预估 {int(estimated_tokens)} tokens，最小允许 {min_tokens} tokens（约 {min_tokens * 3} 字符）"

    # 最大长度验证
    if estimated_tokens > max_tokens:
        return False, f"内容过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
    return True, ""


def _validate_tag_length(tag: str, max_tokens: int = 10) -> tuple[bool, str]:
    """验证单个标签长度（基于 token 估算）.

    Args:
        tag: 要验证的标签
        max_tokens: 最大 token 数

    Returns:
        (是否有效, 错误信息)
    """
    if not tag:
        return False, "标签不能为空"

    # 简化的 token 估算：1 token ≈ 3 字符
    estimated_tokens = len(tag) / 3

    if estimated_tokens > max_tokens:
        return False, f"标签 '{tag}' 过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
    return True, ""



def project_add(
    project_id: str,
    group: str,
    content: str = "",
    description: str = "",
    status: str = None,  # 哨兵值，用于检测是否显式传入
    severity: str = "medium",
    related_feature: str = "",
    note_id: str = "",
    tags: str = ""
) -> str:
    """添加项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"（支持中文："功能"/"修复"/"笔记"/"规范"）
        content: 条目内容
            - features: 功能描述
            - fixes: 修复描述
            - notes: 笔记内容
            - standards: 规范内容
        description: 描述（所有分组必填，标准摘要描述）
        status: 状态（仅 features/fixes 使用，必填，有效值: pending/in_progress/completed）
        severity: 严重程度（仅 fixes 使用，默认 "medium"）
        related_feature: 关联功能ID（仅 fixes 使用）
        note_id: 关联笔记ID（仅 features/fixes 使用）
        tags: 标签列表，逗号分隔

    Returns:
        JSON 格式的操作结果
    """
    # 标准化 group 参数
    group_normalized = _normalize_group(group)

    # 验证 group 有效性
    if group_normalized not in ["features", "fixes", "notes", "standards"]:
        response = ApiResponse(success=False, error=f"无效的分组类型: {group} (支持: features/fixes/notes/standards 或 功能/修复/笔记/规范)")
        return response.to_json()

    # status 参数验证（仅 features/fixes 分组必填）
    if group_normalized in ["features", "fixes"]:
        if status is None:
            response = ApiResponse(success=False, error="features/fixes 分组必须传入 status 参数 (有效值: pending/in_progress/completed)")
            return response.to_json()
        if status not in ["pending", "in_progress", "completed"]:
            response = ApiResponse(success=False, error=f"无效的 status 值: {status} (有效值: pending/in_progress/completed)")
            return response.to_json()
    else:
        # notes/standards 忽略 status 参数
        status = None

    # 验证必需参数
    if not content:
        response = ApiResponse(success=False, error="content 参数不能为空")
        return response.to_json()

    # 根据 group 类型设置不同的 max_tokens
    # features/fixes/standards: 30 tokens, notes: 500 tokens (允许详细的技术笔记)
    max_tokens_map = {
        "features": 80,
        "fixes": 80,
        "notes": 500,
        "standards": 80
    }
    max_tokens = max_tokens_map.get(group_normalized, 30)

    # 验证 content 长度
    # notes 分组添加最小长度验证（1 token）
    min_tokens = 1 if group_normalized == "notes" else None
    is_valid, error_msg = _validate_content_length(content, max_tokens=max_tokens, min_tokens=min_tokens)
    if not is_valid:
        response = ApiResponse(success=False, error=error_msg)
        return response.to_json()

    # 验证 description 必填（所有分组）
    if not description or not description.strip():
        response = ApiResponse(success=False, error="description 参数不能为空，请提供标准摘要描述")
        return response.to_json()

    # 验证 description 长度
    # notes 分组 50 tokens，其他分组 30 tokens
    desc_max_tokens = 50 if group_normalized == "notes" else 30
    is_valid, error_msg = _validate_content_length(description, max_tokens=desc_max_tokens)
    if not is_valid:
        response = ApiResponse(success=False, error=error_msg)
        return response.to_json()

    # 解析标签
    tag_list = _parse_tags(tags)

    # 验证 tags 不能为空
    if not tag_list:
        response = ApiResponse(success=False, error="tags 参数不能为空，请至少提供一个标签")
        return response.to_json()

    # 验证每个 tag 长度 (1-10 tokens)
    for tag in tag_list:
        is_valid, error_msg = _validate_tag_length(tag, max_tokens=10)
        if not is_valid:
            response = ApiResponse(success=False, error=error_msg)
            return response.to_json()

    # 根据 group 分发
    if group_normalized == "features":
        result = memory.add_feature(
            project_id,
            content,  # feature content
            description,  # feature description (overview)
            status,
            tag_list,
            note_id or None
        )
        if result["success"]:
            data = {
                "project_id": project_id,
                "group": "features",
                "item_id": result["feature_id"],
                "item": {
                    "id": result["feature_id"],
                    "content": content,
                    "description": description,
                    "status": status,
                    "tags": tag_list,
                    "note_id": note_id or None
                }
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "fixes":
        result = memory.add_fix(
            project_id,
            content,  # fix content
            description,  # fix description (overview)
            status,
            severity,
            related_feature or None,
            note_id or None,
            tag_list
        )
        if result["success"]:
            data = {
                "project_id": project_id,
                "group": "fixes",
                "item_id": result["fix_id"],
                "item": {
                    "id": result["fix_id"],
                    "content": content,
                    "description": description,
                    "status": status,
                    "severity": severity,
                    "tags": tag_list,
                    "related_feature": related_feature or None,
                    "note_id": note_id or None
                }
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "notes":
        result = memory.add_note(
            project_id,
            content,  # note content
            tag_list,
            description
        )
        if result["success"]:
            data = {
                "project_id": project_id,
                "group": "notes",
                "item_id": result["note_id"],
                "item": {
                    "id": result["note_id"],
                    "content": content,
                    "description": description,
                    "tags": tag_list
                }
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "standards":
        result = memory.add_standard(
            project_id,
            content,  # standard content
            tag_list,
            description
        )
        if result["success"]:
            data = {
                "project_id": project_id,
                "group": "standards",
                "item_id": result["standard_id"],
                "item": {
                    "id": result["standard_id"],
                    "content": content,
                    "description": description,
                    "tags": tag_list
                }
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()


def project_update(
    project_id: str,
    group: str,
    item_id: str,
    content: str = None,
    description: str = None,
    status: str = None,
    severity: str = None,
    related_feature: str = None,
    note_id: str = None,
    tags: str = None
) -> str:
    """更新项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"
        item_id: 条目ID
        content: 内容更新（可选）
        description: 描述更新（可选）
        status: 状态更新（可选）
        severity: 严重程度更新（仅 fixes）
        related_feature: 关联功能更新（仅 fixes）
        note_id: 关联笔记更新（仅 features/fixes）
        tags: 标签更新（可选）

    Returns:
        JSON 格式的操作结果
    """
    # 标准化 group 参数
    group_normalized = _normalize_group(group)

    # 验证 group 有效性
    if group_normalized not in ["features", "fixes", "notes", "standards"]:
        response = ApiResponse(success=False, error=f"无效的分组类型: {group} (支持: features/fixes/notes/standards)")
        return response.to_json()

    # 验证必需参数
    if not item_id:
        response = ApiResponse(success=False, error="item_id 参数不能为空")
        return response.to_json()

    # 验证 content 长度
    if content is not None:
        # 根据 group 类型设置不同的 max_tokens
        # features/fixes/standards: 30 tokens, notes: 500 tokens (允许详细的技术笔记)
        max_tokens_map = {"features": 30, "fixes": 30, "notes": 500, "standards": 30}
        max_tokens = max_tokens_map.get(group_normalized, 30)
        # notes 分组添加最小长度验证（1 token）
        min_tokens = 1 if group_normalized == "notes" else None
        is_valid, error_msg = _validate_content_length(content, max_tokens=max_tokens, min_tokens=min_tokens)
        if not is_valid:
            response = ApiResponse(success=False, error=error_msg)
            return response.to_json()

    # 验证 description 长度
    if description is not None:
        # notes 分组 50 tokens，其他分组 30 tokens
        desc_max_tokens = 50 if group_normalized == "notes" else 30
        is_valid, error_msg = _validate_content_length(description, max_tokens=desc_max_tokens)
        if not is_valid:
            response = ApiResponse(success=False, error=error_msg)
            return response.to_json()

    # 根据 group 分发
    if group_normalized == "features":
        update_params = {}
        if content is not None:
            update_params["content"] = content
        if description is not None:
            update_params["description"] = description
        if status is not None:
            update_params["status"] = status
        if tags is not None:
            update_params["tags"] = _parse_tags(tags)
        if note_id is not None:
            update_params["note_id"] = note_id

        result = memory.update_feature(project_id, item_id, **update_params)

        if result["success"]:
            feature = result["feature"]
            data = {
                "project_id": project_id,
                "group": "features",
                "item_id": item_id,
                "item": feature
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "fixes":
        update_params = {}
        if content is not None:
            update_params["content"] = content
        if description is not None:
            update_params["description"] = description
        if status is not None:
            update_params["status"] = status
        if severity is not None:
            update_params["severity"] = severity
        if related_feature is not None:
            update_params["related_feature"] = related_feature
        if note_id is not None:
            update_params["note_id"] = note_id
        if tags is not None:
            update_params["tags"] = _parse_tags(tags)

        result = memory.update_fix(project_id, item_id, **update_params)

        if result["success"]:
            fix = result["fix"]
            data = {
                "project_id": project_id,
                "group": "fixes",
                "item_id": item_id,
                "item": fix
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "notes":
        update_params = {}
        if content is not None:
            update_params["content"] = content
        if description is not None:
            update_params["description"] = description
        if tags is not None:
            update_params["tags"] = _parse_tags(tags)

        result = memory.update_note(project_id, item_id, **update_params)

        if result["success"]:
            note = result["note"]
            data = {
                "project_id": project_id,
                "group": "notes",
                "item_id": item_id,
                "item": note
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif group_normalized == "standards":
        update_params = {}
        if content is not None:
            update_params["content"] = content
        if description is not None:
            update_params["description"] = description
        if tags is not None:
            update_params["tags"] = _parse_tags(tags)

        result = memory.update_standard(project_id, item_id, **update_params)

        if result["success"]:
            standard = result["standard"]
            data = {
                "project_id": project_id,
                "group": "standards",
                "item_id": item_id,
                "item": standard
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()


def project_delete(
    project_id: str,
    group: str,
    item_id: str
) -> str:
    """删除项目条目（统一接口）.

    Args:
        project_id: 项目ID
        group: 分组类型 - "features"/"fixes"/"notes"/"standards"
        item_id: 条目ID

    Returns:
        JSON 格式的操作结果
    """
    # 标准化 group 参数
    group_normalized = _normalize_group(group)

    # 验证 group 有效性
    if group_normalized not in ["features", "fixes", "notes", "standards"]:
        response = ApiResponse(success=False, error=f"无效的分组类型: {group} (支持: features/fixes/notes/standards)")
        return response.to_json()

    # 验证必需参数
    if not item_id:
        response = ApiResponse(success=False, error="item_id 参数不能为空")
        return response.to_json()

    # 根据 group 分发
    if group_normalized == "features":
        result = memory.delete_feature(project_id, item_id)
    elif group_normalized == "fixes":
        result = memory.delete_fix(project_id, item_id)
    elif group_normalized == "notes":
        result = memory.delete_note(project_id, item_id)
    elif group_normalized == "standards":
        result = memory.delete_standard(project_id, item_id)

    if result["success"]:
        data = {
            "project_id": project_id,
            "group": group_normalized,
            "item_id": item_id,
            "deleted": True
        }
        response = ApiResponse(success=True, data=data, message=result['message'])
        return response.to_json()
    response = ApiResponse(success=False, error=result.get('error', '未知错误'))
    return response.to_json()


def project_item_tag_manage(
    project_id: str,
    group_name: str,
    item_id: str,
    operation: str,
    tag: str = "",
    tags: str = ""
) -> str:
    """管理条目标签（统一接口）.

    Args:
        project_id: 项目ID
        group_name: 分组名称 ("features"|"notes"|"fixes"|"standards")
        item_id: 条目ID
        operation: 操作类型 - "set"|"add"|"remove"
        tag: 单个标签 (operation="add"|"remove"时)
        tags: 标签列表逗号分隔 (operation="set"时)

    Returns:
        JSON 格式的操作结果
    """
    if group_name not in ["features", "notes", "fixes", "standards"]:
        response = ApiResponse(success=False, error=f"无效的分组名称: {group_name}")
        return response.to_json()

    if operation == "set" or operation == "设置":
        if not tags:
            response = ApiResponse(success=False, error="operation='set' 时 tags 参数不能为空")
            return response.to_json()
        tag_list = [t.strip() for t in tags.split(",")]

        if group_name == "features":
            result = memory.update_feature_tags(project_id, item_id, tag_list)
        elif group_name == "notes":
            result = memory.update_note_tags(project_id, item_id, tag_list)
        elif group_name == "standards":
            result = memory.update_standard(project_id, item_id, tags=tag_list)
        else:  # fixes - need to use update_fix
            result = memory.update_fix(project_id, item_id, tags=tag_list)

        if result["success"]:
            data = {
                "project_id": project_id,
                "group_name": group_name,
                "item_id": item_id,
                "operation": "set",
                "tags": result.get('tags', tag_list)
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif operation == "add" or operation == "添加":
        if not tag:
            response = ApiResponse(success=False, error="operation='add' 时 tag 参数不能为空")
            return response.to_json()
        result = memory.add_item_tag(project_id, group_name, item_id, tag)

        if result["success"]:
            data = {
                "project_id": project_id,
                "group_name": group_name,
                "item_id": item_id,
                "operation": "add",
                "tag": tag,
                "tags": result.get("tags", [])
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    elif operation == "remove" or operation == "移除":
        if not tag:
            response = ApiResponse(success=False, error="operation='remove' 时 tag 参数不能为空")
            return response.to_json()
        result = memory.remove_item_tag(project_id, group_name, item_id, tag)

        if result["success"]:
            data = {
                "project_id": project_id,
                "group_name": group_name,
                "item_id": item_id,
                "operation": "remove",
                "tag": tag,
                "tags": result.get("tags", [])
            }
            response = ApiResponse(success=True, data=data, message=result['message'])
            return response.to_json()
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    else:
        response = ApiResponse(success=False, error=f"无效的操作类型: {operation} (支持: set/add/remove)")
        return response.to_json()


def tag_register(
    project_id: str,
    tag_name: str,
    description: str,
    aliases: str = ""
) -> str:
    """注册项目标签.

    标签必须先注册才能使用。注册时需要提供语义描述（建议10-50字）。

    Args:
        project_id: 项目ID
        tag_name: 标签名称（英文，无空格）
        description: 标签语义描述（10-50字）
        aliases: 别名列表，逗号分隔（可选）

    Returns:
        JSON 格式的注册结果
    """
    alias_list = [a.strip() for a in aliases.split(",")] if aliases else []

    result = memory.register_tag(
        project_id=project_id,
        tag_name=tag_name,
        description=description,
        aliases=alias_list
    )

    if result.get("success"):
        data = {
            "project_id": project_id,
            "tag_name": tag_name,
            "tag_info": result.get("tag_info", {})
        }
        response = ApiResponse(success=True, data=data, message=result['message'])
        return response.to_json()
    response = ApiResponse(success=False, error=result.get('error', '未知错误'))
    return response.to_json()


def tag_update(
    project_id: str,
    tag_name: str,
    description: str = ""
) -> str:
    """更新已注册标签的语义信息.

    Args:
        project_id: 项目ID
        tag_name: 标签名称
        description: 新的描述（可选）

    Returns:
        JSON 格式的更新结果
    """
    desc_param = description if description else None

    result = memory.update_tag(
        project_id=project_id,
        tag_name=tag_name,
        description=desc_param
    )

    if result.get("success"):
        data = {
            "project_id": project_id,
            "tag_name": tag_name,
            "updated": True
        }
        response = ApiResponse(success=True, data=data, message=result['message'])
        return response.to_json()
    response = ApiResponse(success=False, error=result.get('error', '未知错误'))
    return response.to_json()


def tag_delete(
    project_id: str,
    tag_name: str,
    force: str = "false"
) -> str:
    """删除标签注册.

    Args:
        project_id: 项目ID
        tag_name: 标签名称
        force: 是否强制删除（"true"/"false"，即使标签正在使用）

    Returns:
        JSON 格式的删除结果
    """
    force_flag = force.lower() == "true"

    result = memory.delete_tag(
        project_id=project_id,
        tag_name=tag_name,
        force=force_flag
    )

    if result.get("success"):
        data = {
            "project_id": project_id,
            "tag_name": tag_name,
            "force": force_flag,
            "deleted": True
        }
        response = ApiResponse(success=True, data=data, message=result['message'])
        return response.to_json()
    response = ApiResponse(success=False, error=result.get('error', '未知错误'))
    return response.to_json()


def tag_merge(
    project_id: str,
    old_tag: str,
    new_tag: str
) -> str:
    """合并标签：将所有 old_tag 的引用迁移到 new_tag.

    Args:
        project_id: 项目ID
        old_tag: 旧标签名称（将被删除）
        new_tag: 新标签名称（合并目标）

    Returns:
        JSON 格式的合并结果
    """
    result = memory.merge_tags(
        project_id=project_id,
        old_tag=old_tag,
        new_tag=new_tag
    )

    if result.get("success"):
        data = {
            "project_id": project_id,
            "old_tag": old_tag,
            "new_tag": new_tag,
            "merged": True
        }
        response = ApiResponse(success=True, data=data, message=result['message'])
        return response.to_json()
    response = ApiResponse(success=False, error=result.get('error', '未知错误'))
    return response.to_json()


def project_get(
    project_id: str,
    group_name: str = "",
    item_id: str = "",
    status: str = "",
    severity: str = "",
    tags: str = "",
    page: int = 1,
    size: int = 0
) -> str:
    """获取项目信息或查询条目列表/详情.

    查询模式:
        1. 整个项目信息 - 不传 group_name
        2. 分组列表模式 - 传 group_name，不传 item_id (不含 content)
        3. 条目详情模式 - 传 group_name + item_id (含完整 content)

    Args:
        project_id: 项目ID
        group_name: 分组名称 (可选): "features"|"notes"|"fixes"|"standards"
        item_id: 条目ID (可选): 查询单个条目时指定
        status: 状态过滤 (可选): 对 group_name="features" 或 "fixes" 有效，过滤状态 (pending/in_progress/completed)
        severity: 严重程度过滤 (可选): 仅对 group_name="fixes" 有效，过滤严重程度 (critical/high/medium/low)
        tags: 标签过滤 (可选): 逗号分隔的标签字符串，OR 逻辑匹配（至少包含一个标签即可），如 "api,enhancement"
        page: 页码 (可选): 从 1 开始，默认为 1
        size: 每页条数 (可选): 默认为 0 表示返回全部结果，大于 0 时启用分页

    Returns:
        JSON 格式的项目信息、条目列表或单个条目详情
        注意: 列表模式不返回 content 字段，需使用 item_id 查询详情获取完整内容

    使用示例:
        # 获取整个项目信息
        project_get(project_id="my_project")

        # 查询功能列表
        project_get(project_id="my_project", group_name="features")

        # 查询功能列表（带状态过滤）
        project_get(project_id="my_project", group_name="features", status="pending")

        # 查询修复列表（带过滤）
        project_get(project_id="my_project", group_name="fixes", status="pending", severity="high")

        # 查询功能列表（带标签过滤，OR 逻辑）
        project_get(project_id="my_project", group_name="features", tags="api,enhancement")

        # 查询功能列表（组合过滤）
        project_get(project_id="my_project", group_name="features", status="pending", tags="api")

        # 查询功能列表（分页）
        project_get(project_id="my_project", group_name="features", page=1, size=10)

        # 查询功能列表（过滤 + 分页）
        project_get(project_id="my_project", group_name="features", status="pending", page=1, size=10)

        # 查询单个条目详情
        project_get(project_id="my_project", group_name="features", item_id="feat_20260318_001")
    """
    result = memory.get_project(project_id)

    if not result["success"]:
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    data = result["data"]

    # 如果指定了 group_name
    if group_name:
        if group_name not in ["features", "notes", "fixes", "standards"]:
            response = ApiResponse(success=False, error=f"无效的分组名称: {group_name} (支持: features/notes/fixes/standards)")
            return response.to_json()

        items = data.get(group_name, [])

        # 如果指定了 item_id，返回单个条目详情
        if item_id:
            item = None
            for it in items:
                if it.get("id") == item_id:
                    item = it.copy()  # 复制以避免修改原始数据
                    break

            if not item:
                response = ApiResponse(success=False, error=f"在分组 '{group_name}' 中找不到条目 '{item_id}'")
                return response.to_json()

            # 对于 notes 分组，从 .md 文件加载 content
            if group_name == "notes":
                note_content = memory._load_note_content(project_id, item_id)
                if note_content is not None:
                    item["content"] = note_content

            response_data = {
                "project_id": project_id,
                "group_name": group_name,
                "item_id": item_id,
                "item": item
            }
            response = ApiResponse(success=True, data=response_data, message="获取条目详情成功")
            return response.to_json()

        # 如果只指定了 group_name 但没有 item_id，返回该分组列表
        # 列表模式不返回 content 字段以减少数据量，使用 item_id 查询详情可获取完整 content
        filtered_items = items

        # 解析 tags 参数
        tag_list = _parse_tags(tags) if tags else []

        # 应用过滤条件
        if group_name in ["features", "fixes"]:
            if status:
                filtered_items = [f for f in filtered_items if f.get("status") == status]
            if severity:
                filtered_items = [f for f in filtered_items if f.get("severity") == severity]

        # tags 过滤：OR 逻辑，适用于所有分组
        if tag_list:
            filtered_items = [f for f in filtered_items if any(tag in f.get("tags", []) for tag in tag_list)]

        # 分页处理：先过滤，后分页
        paginated_items = filtered_items
        pagination_meta = {}
        filtered_total = len(filtered_items)

        # 转换分页参数为整数（MCP 工具传入的参数是字符串类型）
        try:
            page_int = int(page) if page else 1
            size_int = int(size) if size else 0
        except (ValueError, TypeError):
            response = ApiResponse(success=False, error="分页参数必须为有效的整数")
            return response.to_json()

        if size_int > 0:
            # 验证 page 参数
            if page_int < 1:
                response = ApiResponse(success=False, error=f"无效的页码: {page_int} (页码必须大于 0)")
                return response.to_json()

            # 验证 size 参数
            if size_int < 0:
                response = ApiResponse(success=False, error=f"无效的每页条数: {size_int} (每页条数不能为负数)")
                return response.to_json()

            # 计算总页数
            total_pages = (filtered_total + size_int - 1) // size_int if filtered_total > 0 else 0

            # 计算起始和结束索引
            start_idx = (page_int - 1) * size_int
            end_idx = start_idx + size_int

            # 获取分页数据
            paginated_items = filtered_items[start_idx:end_idx]

            # 分页元信息
            pagination_meta = {
                "page": page_int,
                "size": size_int,
                "total_pages": total_pages,
                "has_next": page_int < total_pages,
                "has_prev": page_int > 1
            }

        # 列表模式过滤掉 content 字段
        filtered_items_without_content = [{k: v for k, v in item.items() if k != 'content'} for item in paginated_items]

        response_data = {
            "project_id": project_id,
            "project_name": data['info']['name'],
            "group_name": group_name,
            "total": len(items),
            "filtered_total": filtered_total,
            "items": filtered_items_without_content
        }

        # 添加分页元信息（仅在启用分页时）
        if pagination_meta:
            response_data.update(pagination_meta)

        # 添加过滤器信息（如果有过滤条件）
        if status or severity or tags:
            response_data["filters"] = {"status": status, "severity": severity, "tags": tags}

        response = ApiResponse(success=True, data=response_data, message=f"共 {filtered_total} 个条目")
        return response.to_json()

    # 默认行为：返回整个项目信息
    response_data = {
        "project_id": project_id,
        "info": data['info'],
        "features": data["features"],
        "notes": data["notes"],
        "fixes": data.get("fixes", [])
    }
    response = ApiResponse(success=True, data=response_data, message="获取项目信息成功")
    return response.to_json()


def project_stats() -> str:
    """获取全局统计信息.

    Returns:
        JSON 格式的统计数据
    """
    result = memory.get_stats()

    if not result["success"]:
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    stats = result["stats"]
    data = {
        "total_projects": stats['total_projects'],
        "total_features": stats['total_features'],
        "total_notes": stats['total_notes'],
        "feature_status": stats["feature_status"],
        "top_project_tags": stats["top_project_tags"],
        "top_feature_tags": stats["top_feature_tags"],
        "top_note_tags": stats["top_note_tags"]
    }
    response = ApiResponse(success=True, data=data, message="获取统计成功")
    return response.to_json()



def stats_summary(
    type: str = "",
    tool_name: str = "",
    project_id: str = "",
    date: str = ""
) -> str:
    """获取统计摘要（统一接口）.

    Args:
        type: 统计类型 - "tool"|"project"|"client"|"ip"|"daily"|"full"|""(所有)
        tool_name: 工具名称 (type="tool"时)
        project_id: 项目ID (type="project"时)
        date: 日期 YYYY-MM-DD (type="daily"时)

    Returns:
        JSON 格式的统计摘要
    """
    if type == "tool" or type == "工具":
        if tool_name:
            result = call_stats.get_tool_stats(tool_name)
            if not result["success"]:
                response = ApiResponse(success=False, error=result.get('error', '未知错误'))
                return response.to_json()

            data = {
                "type": "tool",
                "tool_name": tool_name,
                "total": result['total'],
                "first_called": result.get('first_called'),
                "last_called": result.get('last_called'),
                "by_project": result.get("by_project", {}),
                "by_client": result.get("by_client", {}),
                "by_ip": result.get("by_ip", {})
            }
            response = ApiResponse(success=True, data=data, message=f"工具 '{tool_name}' 调用统计")
            return response.to_json()
        else:
            result = call_stats.get_tool_stats()
            if not result["success"]:
                response = ApiResponse(success=False, error=result.get('error', '未知错误'))
                return response.to_json()

            data = {
                "type": "tool",
                "tools": result["tools"]
            }
            response = ApiResponse(success=True, data=data, message="所有工具调用统计")
            return response.to_json()

    elif type == "project" or type == "项目":
        if not project_id:
            response = ApiResponse(success=False, error="project_id 参数不能为空")
            return response.to_json()
        result = call_stats.get_project_stats(project_id)

        if not result["success"]:
            response = ApiResponse(success=False, error=result.get('error', '未知错误'))
            return response.to_json()

        data = {
            "type": "project",
            "project_id": project_id,
            "total_calls": result['total_calls'],
            "tools_called": result["tools_called"]
        }
        response = ApiResponse(success=True, data=data, message=f"项目 '{project_id}' 调用统计")
        return response.to_json()

    elif type == "client" or type == "客户端":
        result = call_stats.get_client_stats()

        if not result["success"]:
            response = ApiResponse(success=False, error="获取客户端统计失败")
            return response.to_json()

        data = {
            "type": "client",
            "clients": result["clients"]
        }
        response = ApiResponse(success=True, data=data, message="客户端调用统计")
        return response.to_json()

    elif type == "ip" or type == "IP":
        result = call_stats.get_ip_stats()

        if not result["success"]:
            response = ApiResponse(success=False, error="获取IP统计失败")
            return response.to_json()

        data = {
            "type": "ip",
            "ips": result["ips"]
        }
        response = ApiResponse(success=True, data=data, message="IP地址调用统计")
        return response.to_json()

    elif type == "daily" or type == "每日":
        if date:
            result = call_stats.get_daily_stats(date)
            if not result["success"]:
                response = ApiResponse(success=False, error=result.get('error', '未知错误'))
                return response.to_json()

            data = {
                "type": "daily",
                "date": date,
                "total_calls": result['total_calls'],
                "tools": result["tools"]
            }
            response = ApiResponse(success=True, data=data, message=f"日期 '{date}' 统计")
            return response.to_json()
        else:
            result = call_stats.get_daily_stats()
            if not result["success"]:
                response = ApiResponse(success=False, error="获取每日统计失败")
                return response.to_json()

            data = {
                "type": "daily",
                "recent_days": result["recent_days"],
                "stats": result["stats"]
            }
            response = ApiResponse(success=True, data=data, message="最近7天统计")
            return response.to_json()

    elif type == "full" or type == "完整":
        result = call_stats.get_full_summary()

        if not result["success"]:
            response = ApiResponse(success=False, error="获取完整统计失败")
            return response.to_json()

        data = {
            "type": "full",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "ip_stats": result["ip_stats"],
            "daily_stats": result["daily_stats"]
        }
        response = ApiResponse(success=True, data=data, message="完整统计")
        return response.to_json()

    else:
        # 默认返回所有统计摘要
        result = call_stats.get_full_summary()
        if not result["success"]:
            response = ApiResponse(success=False, error="获取完整统计失败")
            return response.to_json()

        data = {
            "type": "summary",
            "metadata": result["metadata"],
            "tool_stats": result["tool_stats"],
            "client_stats": result["client_stats"],
            "daily_stats": result["daily_stats"]
        }
        response = ApiResponse(success=True, data=data, message="统计摘要")
        return response.to_json()


def stats_cleanup(retention_days: int = 30) -> str:
    """手动清理过期统计数据.

    清理超过指定天数的统计数据，包括每日统计、工具调用统计、项目统计等。
    这可以帮助减少存储空间使用和提升性能。

    Args:
        retention_days: 保留天数（默认30天），超过此天数的数据将被清理

    Returns:
        JSON 格式的清理结果摘要
    """
    result = call_stats.cleanup_stats(retention_days)

    if not result["success"]:
        response = ApiResponse(success=False, error=result.get('error', '未知错误'))
        return response.to_json()

    cleanup_result = result["cleanup_result"]
    before = result["before"]
    after = result["after"]

    data = {
        "retention_days": retention_days,
        "cutoff_date": cleanup_result['cutoff_date'],
        "cleanup_details": {
            "daily_stats_removed": cleanup_result['daily_stats_removed'],
            "tools_removed": cleanup_result['tools_removed'],
            "projects_cleaned": cleanup_result['projects_cleaned'],
            "clients_cleaned": cleanup_result['clients_cleaned'],
            "ips_cleaned": cleanup_result['ips_cleaned']
        },
        "storage_before": before,
        "storage_after": after
    }
    response = ApiResponse(success=True, data=data, message="统计数据清理完成")
    return response.to_json()



