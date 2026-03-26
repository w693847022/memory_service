"""Project Module - 项目管理模块."""

import json
import time
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta

# Import ProjectStorage from core (avoid circular import by using sys.path)
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from core.storage_base import ProjectStorage
from core.groups import GroupType, all_group_names, is_group_with_status
from models.item import Item, ItemRelated

# Constants
DEFAULT_TAGS = [
    "implementation", "enhancement", "bug", "docs",
    "refactor", "test", "ops", "security"
]

# ==================== ProjectMemory ====================

class ProjectMemory(ProjectStorage):
    """项目记忆管理类 - 继承 ProjectStorage 提供业务逻辑."""

    def __init__(self, storage_dir: Union[str, Path, None] = None):
        """初始化项目记忆管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        super().__init__(storage_dir)

    def _validate_tag_name(self, tag_name: str) -> bool:
        """验证标签名称格式."""
        import re
        pattern = r'^[a-zA-Z0-9_-]{1,30}$'
        return bool(re.match(pattern, tag_name))

    def _validate_description(self, description: str) -> bool:
        """验证描述长度（10-200字符，约10-50 token）.

        Args:
            description: 描述文本

        Returns:
            是否有效
        """
        return 3 <= len(description) <= 200

    def _generate_timestamps(self) -> Dict[str, str]:
        """生成创建和更新时间戳字典."""
        now = datetime.now().isoformat()
        return {"created_at": now, "updated_at": now}

    def _update_timestamp(self, item: Dict[str, Any]) -> None:
        """更新条目的 updated_at 字段."""
        item["updated_at"] = datetime.now().isoformat()

    # ==================== 项目注册 ====================

    def register_project(
        self,
        name: str,
        path: Optional[str] = None,
        summary: str = "",
        tags: Optional[List[str]] = None,
        git_remote: Optional[str] = None,
        git_remote_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """注册新项目."""
        project_id = self._generate_id(name)

        project_data = {
            "id": project_id,
            "info": {
                "name": name,
                "path": path or "",
                "git_remote": git_remote or "",
                "git_remote_url": git_remote_url or "",
                "summary": summary,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": tags or []
            },
            "features": [],
            "notes": [],
            "fixes": [],
            "standards": [],
            "tag_registry": {}
        }

        tag_registry = {}
        # 首先注册默认标签
        for tag in DEFAULT_TAGS:
            tag_registry[tag] = {
                "summary": f"默认标签: {tag}",
                "created_at": datetime.now().isoformat(),
                "usage_count": 0,
                "aliases": []
            }
        # 合并用户传入的额外标签
        if tags:
            for tag in tags:
                if self._validate_tag_name(tag) and tag not in tag_registry:
                    tag_registry[tag] = {
                        "summary": f"项目标签: {tag}",
                        "created_at": datetime.now().isoformat(),
                        "usage_count": 0,
                        "aliases": []
                    }
        project_data["tag_registry"] = tag_registry

        try:
            project_dir = self.storage_dir / name
            project_dir.mkdir(parents=True, exist_ok=True)

            project_json_path = project_dir / "project.json"
            with open(project_json_path, "w", encoding="utf-8") as f:
                save_data = project_data.copy()
                if "notes" in save_data:
                    save_data["notes"] = [
                        {k: v for k, v in note.items() if k != "content"}
                        for note in save_data["notes"]
                    ]
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            self._projects_cache[project_id] = name
            self._uuid_to_name_cache[project_id] = name
            self._project_data_cache[project_id] = project_data
            self._save_metadata()

            return {
                "success": True,
                "project_id": project_id,
                "message": f"项目 '{name}' 已成功注册，ID: {project_id}"
            }
        except IOError:
            return {
                "success": False,
                "error": "保存数据失败"
            }

    def _check_tags_registered(self, project_data: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
        """检查标签是否已注册.

        Args:
            project_data: 项目数据
            tags: 标签列表

        Returns:
            检查结果，如果所有标签都已注册则返回 {"success": True}，
            否则返回 {"success": False, "error": "...", "unregistered_tags": [...]}
        """
        tag_registry = project_data.get("tag_registry", {})
        unregistered = [tag for tag in tags if tag not in tag_registry]

        if unregistered:
            return {
                "success": False,
                "error": f"标签未注册：{', '.join(unregistered)}。\n建议先使用 project_tags_info 查询已注册标签，确认无合适标签后再使用 tag_register 注册新标签",
                "unregistered_tags": unregistered
            }

        return {"success": True}

    def find_project_by_git_remote(self, git_remote: str) -> Optional[str]:
        """通过 Git remote URL 查找项目ID.

        Args:
            git_remote: Git remote URL（完整，带 .git）

        Returns:
            项目ID，如果未找到返回 None
        """
        if not git_remote:
            return None

        # 刷新缓存以确保获取最新数据
        self._refresh_projects_cache()

        # 遍历所有已注册项目
        for project_id in self._projects_cache.keys():
            try:
                project_data = self._load_project(project_id)
                if project_data and "info" in project_data:
                    project_git_remote = project_data["info"].get("git_remote", "")
                    # 比较 git_remote（处理可能的后缀差异）
                    if project_git_remote == git_remote:
                        return project_id
                    # 也尝试不带 .git 的比较
                    if project_git_remote.rstrip(".git") == git_remote.rstrip(".git"):
                        return project_id
            except Exception:
                continue

        return None

    # ==================== 基本信息设置 ====================

    def set_info(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """设置项目基本信息.

        Args:
            project_id: 项目ID
            **kwargs: 要更新的字段（name, path, description, tags）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        for key, value in kwargs.items():
            if key in ["name", "path", "description", "tags"]:
                project_data["info"][key] = value

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            if "name" in kwargs:
                self._projects_cache[project_id] = kwargs["name"]
            return {
                "success": True,
                "message": f"项目 '{project_id}' 信息已更新"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== 统一添加接口 ====================

    def add_item(
        self,
        project_id: str,
        group: str,
        content: str = "",
        summary: str = "",
        status: Optional[str] = None,
        severity: str = "medium",
        related: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """统一添加项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型 - "features"/"fixes"/"notes"/"standards"
            content: 条目内容（notes 分组会存为独立文件）
            summary: 条目摘要（必须）
            status: 状态（仅 features/fixes 分组有效）
            severity: 严重程度（仅 fixes 分组有效）
            related: 关联ID字典，格式: {"features": [], "fixes": [], "notes": [], "standards": []}
            tags: 标签列表

        Returns:
            操作结果，包含 item_id
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 验证 summary 必填
        if not summary or not summary.strip():
            return {"success": False, "error": "summary 参数不能为空"}

        # 解析标签
        tag_list = tags or []

        # 强制注册检查：所有标签必须已注册
        if tag_list:
            check_result = self._check_tags_registered(project_data, tag_list)
            if not check_result["success"]:
                return check_result

        # 验证 related 中的 ID 存在性
        if related:
            for rel_group, rel_ids in related.items():
                if not rel_ids:
                    continue
                # 验证关联分组存在
                if rel_group not in project_data:
                    return {"success": False, "error": f"related 中指定的分组 '{rel_group}' 不存在"}
                # 验证每个 ID 存在
                existing_ids = [item.get("id") for item in project_data.get(rel_group, [])]
                for rel_id in rel_ids:
                    if rel_id not in existing_ids:
                        return {"success": False, "error": f"related 中引用的 ID '{rel_id}' 在分组 '{rel_group}' 中不存在"}

        # 生成时间戳
        timestamps = self._generate_timestamps()

        # 生成唯一ID
        id_prefix = {"features": "feat", "fixes": "fix", "notes": "note", "standards": "std"}[group]
        item_id = self._generate_item_id(id_prefix, project_id, project_data)

        # 构建 Item 对象
        item_related = ItemRelated.from_dict(related) if related else None
        item = Item(
            id=item_id,
            summary=summary,
            content=content,
            tags=tag_list,
            status=status,
            severity=severity if severity != "medium" else None,
            related=item_related,
            created_at=timestamps["created_at"],
            updated_at=timestamps["updated_at"]
        )

        # 更新标签使用计数
        if tag_list:
            tag_registry = project_data.get("tag_registry", {})
            for tag in tag_list:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

        # 保存到对应分组
        if group == GroupType.NOTES.value:
            # notes 的 content 存为独立文件，不存入 project.json
            if content and not self._save_note_content(project_id, item_id, content):
                return {"success": False, "error": "保存笔记内容失败"}
            # 从 item dict 中移除 content（已单独存储）
            item_dict = item.to_dict()
            item_dict.pop("content", None)
            project_data[group].append(item_dict)
        else:
            project_data[group].append(item.to_dict())
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "item_id": item_id,
                "message": f"已添加 {group} 记录到项目 '{project_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    def delete_item(self, project_id: str, group: str, item_id: str) -> Dict[str, Any]:
        """统一删除项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型 - "features"/"fixes"/"notes"/"standards"
            item_id: 条目ID

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 验证分组存在
        if group not in project_data:
            return {"success": False, "error": f"分组 '{group}' 不存在"}

        # 查找并删除条目
        items = project_data[group]
        for i, item in enumerate(items):
            if item.get("id") == item_id:
                # 如果是 notes 类型，同时删除 content 文件
                if group == GroupType.NOTES.value:
                    content_path = self._get_note_content_path(project_id, item_id)
                    if content_path.exists():
                        try:
                            content_path.unlink()
                        except IOError:
                            pass

                # 删除条目
                items.pop(i)
                project_data["info"]["updated_at"] = datetime.now().isoformat()

                if self._save_project(project_id, project_data):
                    return {
                        "success": True,
                        "message": f"已删除 {group} 条目 '{item_id}'"
                    }
                return {"success": False, "error": "保存数据失败"}

        return {"success": False, "error": f"条目 '{item_id}' 不存在"}

    def update_item(
        self,
        project_id: str,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        related: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """统一更新项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型 - "features"/"fixes"/"notes"/"standards"
            item_id: 条目ID
            content: 新的内容（可选）
            summary: 新的摘要（可选）
            status: 新的状态（可选，仅 features/fixes）
            severity: 新的严重程度（可选，仅 fixes）
            related: 新的关联ID字典（可选）
            tags: 新的标签列表（可选）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 验证分组存在
        if group not in project_data:
            return {"success": False, "error": f"分组 '{group}' 不存在"}

        # 查找条目
        item_index = None
        for i, item in enumerate(project_data[group]):
            if item.get("id") == item_id:
                item_index = i
                break

        if item_index is None:
            return {"success": False, "error": f"条目 '{item_id}' 不存在"}

        item = project_data[group][item_index]

        # 验证 related 中的 ID 存在性
        if related:
            for rel_group, rel_ids in related.items():
                if not rel_ids:
                    continue
                if rel_group not in project_data:
                    return {"success": False, "error": f"related 中指定的分组 '{rel_group}' 不存在"}
                existing_ids = [it.get("id") for it in project_data.get(rel_group, [])]
                for rel_id in rel_ids:
                    if rel_id not in existing_ids:
                        return {"success": False, "error": f"related 中引用的 ID '{rel_id}' 在分组 '{rel_group}' 中不存在"}

        # 处理标签更新
        if tags is not None:
            old_tags = item.get("tags", [])
            tag_registry = project_data.get("tag_registry", {})

            # 递减旧标签的使用计数
            for old_tag in old_tags:
                if old_tag in tag_registry:
                    current_count = tag_registry[old_tag].get("usage_count", 0)
                    tag_registry[old_tag]["usage_count"] = max(0, current_count - 1)

            # 递增新标签的使用计数
            for new_tag in tags:
                if new_tag in tag_registry:
                    tag_registry[new_tag]["usage_count"] = tag_registry[new_tag].get("usage_count", 0) + 1

            project_data["tag_registry"] = tag_registry
            item["tags"] = tags

        # 更新提供的字段
        if content is not None:
            if group == GroupType.NOTES.value:
                # notes 的 content 存为独立文件
                if not self._save_note_content(project_id, item_id, content):
                    return {"success": False, "error": "保存笔记内容失败"}
            else:
                item["content"] = content

        if summary is not None:
            item["summary"] = summary

        if status is not None and is_group_with_status(group):
            item["status"] = status

        if severity is not None and group == GroupType.FIXES.value:
            item["severity"] = severity

        if related is not None:
            item["related"] = related

        project_data[group][item_index] = item
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "item": item,
                "message": f"已更新 {group} 条目 '{item_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== 查询功能 ====================

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取项目完整信息.

        Args:
            project_id: 项目ID

        Returns:
            项目信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        return {
            "success": True,
            "project_id": project_id,
            "data": project_data
        }

    def list_projects(self) -> Dict[str, Any]:
        """列出所有项目.

        Returns:
            项目列表
        """
        self._refresh_projects_cache()
        projects = []

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data:
                projects.append({
                    "id": project_id,
                    "name": project_data["info"]["name"],
                    "summary": project_data["info"].get("summary", ""),
                    "tags": project_data["info"]["tags"],
                    "created_at": project_data["info"]["created_at"]
                })

        return {
            "success": True,
            "total": len(projects),
            "projects": projects
        }

    # ==================== 搜索功能 ====================

    def search(self, keyword: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """搜索项目.

        Args:
            keyword: 关键词（搜索名称、描述、功能、笔记）
            tags: 标签过滤

        Returns:
            搜索结果
        """
        results = []
        self._refresh_projects_cache()

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data is None:
                continue

            # 标签过滤
            if tags:
                project_tags = set(project_data["info"]["tags"])
                if not set(tags).intersection(project_tags):
                    continue

            # 关键词搜索
            if keyword:
                keyword_lower = keyword.lower()
                match = False

                # 搜索名称和摘要
                project_summary = project_data["info"].get("summary", "")
                if (keyword_lower in project_data["info"]["name"].lower() or
                    keyword_lower in project_summary.lower()):
                    match = True

                # 搜索功能
                for feature in project_data["features"]:
                    if keyword_lower in feature.get("summary", "").lower():
                        match = True
                        break

                # 搜索笔记
                for note in project_data["notes"]:
                    if keyword_lower in note["content"].lower():
                        match = True
                        break

                if not match:
                    continue

            results.append({
                "id": project_id,
                "name": project_data["info"]["name"],
                "summary": project_data["info"].get("summary", ""),
                "tags": project_data["info"]["tags"]
            })

        return {
            "success": True,
            "total": len(results),
            "results": results
        }

    # ==================== 分层查询功能 ====================

    def list_groups(self, project_id: str) -> Dict[str, Any]:
        """列出项目的所有分组及其统计信息.

        Args:
            project_id: 项目ID

        Returns:
            分组列表及统计信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        groups = [
            {
                "name": "features",
                "count": len(project_data["features"]),
                "summary": "功能列表"
            },
            {
                "name": "notes",
                "count": len(project_data["notes"]),
                "summary": "开发笔记"
            },
            {
                "name": "fixes",
                "count": len(project_data.get("fixes", [])),
                "summary": "Bug修复记录"
            },
            {
                "name": "standards",
                "count": len(project_data.get("standards", [])),
                "summary": "项目规范"
            }
        ]

        return {
            "success": True,
            "project_id": project_id,
            "groups": groups
        }

    def list_all_registered_tags(self, project_id: str) -> Dict[str, Any]:
        """列出项目中所有已注册的标签.

        Args:
            project_id: 项目ID

        Returns:
            所有已注册标签的列表，包含描述、使用次数、所属分组等信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})
        groups = all_group_names()

        # 构建标签列表
        tags_list = []
        for tag_name, tag_info in tag_registry.items():
            # 统计该标签在哪些分组中被使用
            tag_groups = []
            group_counts = {}
            for group in groups:
                items = project_data.get(group, [])
                count = sum(1 for item in items if tag_name in item.get("tags", []))
                if count > 0:
                    tag_groups.append(group)
                    group_counts[group] = count

            tags_list.append({
                "tag": tag_name,
                "summary": tag_info.get("summary", ""),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "aliases": tag_info.get("aliases", []),
                "groups": tag_groups,
                "group_counts": group_counts
            })

        # 按注册时间排序（最新的在前）
        tags_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "success": True,
            "project_id": project_id,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def list_group_tags(self, project_id: str, group_name: str) -> Dict[str, Any]:
        """列出指定分组下的所有标签及使用次数.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)

        Returns:
            标签列表及每个标签的条目数量，包含标签语义信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 从 tag_registry 获取所有注册标签
        tag_registry = project_data.get("tag_registry", {})
        items = project_data.get(group_name, [])

        # 统计每个注册标签的使用次数
        tag_counts = {}
        for tag in tag_registry.keys():
            count = sum(1 for item in items if tag in item.get("tags", []))
            if count > 0:
                tag_counts[tag] = count

        # 按使用次数排序并包含语义信息
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = []
        for tag, count in sorted_tags:
            tag_info = tag_registry.get(tag, {})
            tags_list.append({
                "tag": tag,
                "count": count,
                "summary": tag_info.get("summary", "未注册"),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "is_registered": tag in tag_registry
            })

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def list_unregistered_tags(self, project_id: str, group_name: str) -> Dict[str, Any]:
        """列出指定分组下所有未注册的标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)

        Returns:
            未注册标签列表，包含每个标签的使用次数和建议
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 获取所有使用的标签
        used_tags = set()
        items = project_data.get(group_name, [])

        for item in items:
            item_tags = item.get("tags", [])
            used_tags.update(item_tags)

        # 获取已注册的标签
        tag_registry = project_data.get("tag_registry", {})

        # 找出未注册的标签
        unregistered_tags = used_tags - set(tag_registry.keys())

        # 统计每个未注册标签的使用次数
        unregistered_tag_counts = {}
        for tag in unregistered_tags:
            count = sum(1 for item in items if tag in item.get("tags", []))
            unregistered_tag_counts[tag] = count

        # 按使用次数排序
        sorted_tags = sorted(unregistered_tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = []
        for tag, count in sorted_tags:
            tags_list.append({
                "tag": tag,
                "count": count,
                "suggestion": "建议使用 tag_register 注册此标签"
            })

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def query_by_tag(self, project_id: str, group_name: str, tag: str) -> Dict[str, Any]:
        """查询指定分组下某标签的所有条目.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)
            tag: 标签名称

        Returns:
            该标签下的所有条目列表，包含标签语义信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        items = project_data.get(group_name, [])
        matched_items = []

        for item in items:
            item_tags = item.get("tags", [])
            if tag in item_tags:
                matched_items.append(item)

        # 获取标签注册信息
        tag_registry = project_data.get("tag_registry", {})
        tag_info = tag_registry.get(tag, {})
        is_registered = tag in tag_registry

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tag": tag,
            "total": len(matched_items),
            "items": matched_items,
            "tag_info": {
                "summary": tag_info.get("summary", "未注册"),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "is_registered": is_registered
            } if is_registered else None
        }

    # ==================== 标签管理功能 ====================

    def register_tag(self, project_id: str, tag_name: str,
                     summary: str, aliases: Optional[List[str]] = None) -> Dict[str, Any]:
        """注册新标签到项目标签库.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            summary: 标签语义摘要（10-200字符）
            aliases: 别名列表（可选）

        Returns:
            操作结果
        """
        # 验证标签名称
        if not self._validate_tag_name(tag_name):
            return {
                "success": False,
                "error": f"标签名称格式无效：'{tag_name}'。只允许英文字母、数字、下划线、连字符，长度1-30字符"
            }

        # 验证摘要长度
        if not self._validate_description(summary):
            return {
                "success": False,
                "error": f"摘要长度无效：需要10-200字符，当前为 {len(summary)} 字符"
            }

        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        # 检查标签是否已注册
        if tag_name in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 已经注册",
                "tag_info": tag_registry[tag_name]
            }

        # 注册新标签
        tag_registry[tag_name] = {
            "summary": summary,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
            "aliases": aliases or []
        }

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已成功注册",
                "tag_name": tag_name,
                "tag_info": tag_registry[tag_name]
            }

        return {"success": False, "error": "保存数据失败"}

    def update_tag(self, project_id: str, tag_name: str,
                   summary: Optional[str] = None) -> Dict[str, Any]:
        """更新已注册标签的语义信息.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            summary: 新的摘要（可选）

        Returns:
            操作结果
        """
        if summary is not None and not self._validate_description(summary):
            return {
                "success": False,
                "error": f"摘要长度无效：需要10-200字符，当前为 {len(summary)} 字符"
            }

        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        if tag_name not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 未注册"
            }

        # 更新摘要
        if summary is not None:
            tag_registry[tag_name]["summary"] = summary

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已更新",
                "tag_info": tag_registry[tag_name]
            }

        return {"success": False, "error": "保存数据失败"}

    def delete_tag(self, project_id: str, tag_name: str,
                   force: bool = False) -> Dict[str, Any]:
        """删除标签注册.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            force: 是否强制删除（即使标签正在使用）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        if tag_name not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 未注册"
            }

        # 检查标签是否正在使用
        usage_count = tag_registry[tag_name].get("usage_count", 0)

        if usage_count > 0 and not force:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 正在被 {usage_count} 个条目使用，请使用 force=True 强制删除"
            }

        # 删除标签
        del tag_registry[tag_name]

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已删除"
            }

        return {"success": False, "error": "保存数据失败"}

    def merge_tags(self, project_id: str, old_tag: str,
                   new_tag: str) -> Dict[str, Any]:
        """合并标签：将所有 old_tag 的引用迁移到 new_tag.

        Args:
            project_id: 项目ID
            old_tag: 旧标签名称（将被删除）
            new_tag: 新标签名称（合并目标）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        # 检查两个标签都已注册
        if old_tag not in tag_registry:
            return {
                "success": False,
                "error": f"旧标签 '{old_tag}' 未注册"
            }

        if new_tag not in tag_registry:
            return {
                "success": False,
                "error": f"新标签 '{new_tag}' 未注册"
            }

        if old_tag == new_tag:
            return {
                "success": False,
                "error": "旧标签和新标签不能相同"
            }

        # 统计需要迁移的条目数量
        migrated_count = 0

        # 在 features 中迁移标签
        for feature in project_data.get("features", []):
            tags = feature.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                feature["tags"] = tags
                migrated_count += 1

        # 在 notes 中迁移标签
        for note in project_data.get("notes", []):
            tags = note.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                note["tags"] = tags
                migrated_count += 1

        # 在 fixes 中迁移标签
        for fix in project_data.get("fixes", []):
            tags = fix.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                fix["tags"] = tags
                migrated_count += 1

        # 在 standards 中迁移标签
        for standard in project_data.get("standards", []):
            tags = standard.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                standard["tags"] = tags
                migrated_count += 1

        # 更新使用计数
        old_usage = tag_registry[old_tag].get("usage_count", 0)
        new_usage = tag_registry[new_tag].get("usage_count", 0)
        tag_registry[new_tag]["usage_count"] = new_usage + old_usage

        # 删除旧标签
        del tag_registry[old_tag]

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"已将标签 '{old_tag}' 合并到 '{new_tag}'，迁移了 {migrated_count} 个条目",
                "migrated_count": migrated_count
            }

        return {"success": False, "error": "保存数据失败"}


    def add_item_tag(self, project_id: str, group_name: str, item_id: str, tag: str) -> Dict[str, Any]:
        """为条目添加单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/standards)
            item_id: 条目ID
            tag: 要添加的标签

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 强制注册检查：标签必须先注册才能使用
        tag_registry = project_data.get("tag_registry", {})
        if tag not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag}' 未注册，请先使用 tag_register 注册该标签"
            }

        items = project_data.get(group_name, [])
        item_index = None

        for i, item in enumerate(items):
            if item.get("id") == item_id:
                item_index = i
                break

        if item_index is None:
            return {"success": False, "error": f"条目ID '{item_id}' 不存在"}

        current_tags = items[item_index].get("tags", [])
        if tag not in current_tags:
            current_tags.append(tag)
            items[item_index]["tags"] = current_tags

            # 更新使用计数
            tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

            project_data["info"]["updated_at"] = datetime.now().isoformat()

            if self._save_project(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已为条目 '{item_id}' 添加标签 '{tag}'",
                    "tags": current_tags
                }
            return {"success": False, "error": "保存数据失败"}

        return {"success": True, "message": f"标签 '{tag}' 已存在", "tags": current_tags}

    def remove_item_tag(self, project_id: str, group_name: str, item_id: str, tag: str) -> Dict[str, Any]:
        """从条目移除单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/standards)
            item_id: 条目ID
            tag: 要移除的标签

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        items = project_data.get(group_name, [])
        item_index = None

        for i, item in enumerate(items):
            if item.get("id") == item_id:
                item_index = i
                break

        if item_index is None:
            return {"success": False, "error": f"条目ID '{item_id}' 不存在"}

        current_tags = items[item_index].get("tags", [])
        if tag in current_tags:
            current_tags.remove(tag)
            items[item_index]["tags"] = current_tags

            # 更新使用计数
            tag_registry = project_data.get("tag_registry", {})
            if tag in tag_registry:
                current_count = tag_registry[tag].get("usage_count", 0)
                tag_registry[tag]["usage_count"] = max(0, current_count - 1)
                project_data["tag_registry"] = tag_registry

            project_data["info"]["updated_at"] = datetime.now().isoformat()

            if self._save_project(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已从条目 '{item_id}' 移除标签 '{tag}'",
                    "tags": current_tags
                }
            return {"success": False, "error": "保存数据失败"}

        return {"success": True, "message": f"标签 '{tag}' 不存在", "tags": current_tags}

    # ==================== 项目管理 ====================

    def project_rename(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """重命名项目（修改 name 字段并重命名目录）。

        使用安全迁移流程：新建目录→拷贝数据→归档原目录

        Args:
            project_id: 项目 UUID
            new_name: 新的项目名称

        Returns:
            操作结果
        """
        # 加载项目数据
        project_data = self._load_project(project_id)
        if not project_data:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 获取当前项目名称（目录名）
        old_name = project_data.get("name") or project_data.get("info", {}).get("name")
        if not old_name:
            return {"success": False, "error": "无法获取当前项目名称"}

        # 验证新名称
        if not new_name or not new_name.strip():
            return {"success": False, "error": "新名称不能为空"}

        new_name = new_name.strip()

        # 检查新名称是否已存在
        new_dir_path = self.storage_dir / new_name
        if new_dir_path.exists() and new_dir_path != self.storage_dir / old_name:
            return {"success": False, "error": f"项目名称 '{new_name}' 已存在"}

        # 更新项目数据中的 name 字段
        if "info" in project_data:
            project_data["info"]["name"] = new_name
        else:
            project_data["name"] = new_name

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        # 保存更新后的数据到原目录
        old_dir_path = self.storage_dir / old_name
        project_json_path = old_dir_path / "project.json"

        try:
            with open(project_json_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            return {"success": False, "error": f"保存数据失败: {str(e)}"}

        # 使用安全迁移函数移动目录
        migrate_result = self._safe_migrate_project_dir(
            old_path=old_dir_path,
            new_path=new_dir_path,
            project_name=old_name
        )

        if not migrate_result.get("success"):
            return {
                "success": False,
                "error": f"目录迁移失败: {migrate_result.get('error', '未知错误')}"
            }

        # 删除归档文件（不阻塞）
        archived_path = migrate_result.get("archived_path")
        self._delete_archive_file(archived_path)

        # 清除缓存
        if project_id in self._project_data_cache:
            del self._project_data_cache[project_id]
        if project_id in self._uuid_to_name_cache:
            del self._uuid_to_name_cache[project_id]

        # 刷新缓存
        self._refresh_projects_cache()

        return {
            "success": True,
            "message": f"项目已从 '{old_name}' 重命名为 '{new_name}'",
            "old_name": old_name,
            "new_name": new_name,
            "archived_path": migrate_result.get("archived_path")
        }

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """删除项目（同时清理缓存）.

        Args:
            project_id: 项目ID

        Returns:
            操作结果
        """
        project_path = self._get_project_path(project_id)
        if not project_path.exists():
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 获取项目名称用于返回消息
        project_data = self._load_project(project_id)
        project_name = project_data["info"]["name"] if project_data else project_id

        try:
            project_path.unlink()
            # 清理缓存
            if project_id in self._projects_cache:
                del self._projects_cache[project_id]
            # 清理 TTL 缓存
            self._project_data_cache.pop(project_id, None)
            self._save_metadata()
            return {
                "success": True,
                "message": f"项目 '{project_name}' (ID: {project_id}) 已删除"
            }
        except IOError:
            return {"success": False, "error": "删除文件失败"}

    # ==================== 导入导出 ====================

    def export_data(self, output_path: Union[str, Path, None] = None) -> Dict[str, Any]:
        """导出所有项目数据.

        Args:
            output_path: 输出文件路径（可选，默认导出到当前目录）

        Returns:
            操作结果
        """
        if output_path is None:
            output_file = Path.cwd() / f"project_memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            output_file = Path(output_path)

        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 收集所有项目数据
            all_projects = {}
            self._refresh_projects_cache()
            for project_id in self._projects_cache.keys():
                project_data = self._load_project(project_id)
                if project_data:
                    all_projects[project_id] = project_data

            export_data = {
                "projects": all_projects,
                "metadata": {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "total_projects": len(all_projects)
                }
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "message": f"数据已导出到 {output_file}",
                "path": str(output_file)
            }
        except IOError as e:
            return {"success": False, "error": f"导出失败: {str(e)}"}

    def import_data(self, input_path: Union[str, Path], merge: bool = False) -> Dict[str, Any]:
        """导入项目数据.

        Args:
            input_path: 输入文件路径
            merge: 是否合并（True）还是替换（False）

        Returns:
            操作结果
        """
        input_file = Path(input_path)

        if not input_file.exists():
            return {"success": False, "error": f"文件不存在: {input_file}"}

        try:
            with open(input_file, "r", encoding="utf-8") as f:
                imported_data = json.load(f)

            # 支持旧格式（包含 "projects" 键）和新格式
            if "projects" in imported_data:
                projects_to_import = imported_data["projects"]
            else:
                # 新格式：直接是项目数据字典
                projects_to_import = imported_data

            if merge:
                # 合并模式：添加不存在的项目
                count = 0
                for project_id, project_data in projects_to_import.items():
                    project_file = self._get_project_path(project_id)
                    if not project_file.exists():
                        if self._save_project(project_id, project_data):
                            self._projects_cache[project_id] = project_data["info"]["name"]
                            count += 1

                self._save_metadata()
                return {
                    "success": True,
                    "message": f"已导入 {count} 个新项目（合并模式）"
                }
            else:
                # 替换模式：删除所有现有项目，然后导入
                count = 0
                for existing_file in self.storage_dir.glob("*.json"):
                    if existing_file.name != "_metadata.json":
                        existing_file.unlink()

                self._projects_cache.clear()

                for project_id, project_data in projects_to_import.items():
                    if self._save_project(project_id, project_data):
                        self._projects_cache[project_id] = project_data["info"]["name"]
                        count += 1

                self._save_metadata()
                return {
                    "success": True,
                    "message": f"已导入 {count} 个项目（替换模式）"
                }

        except (json.JSONDecodeError, IOError) as e:
            return {"success": False, "error": f"导入失败: {str(e)}"}

    # ==================== 统计功能 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据
        """
        self._refresh_projects_cache()
        total_projects = len(self._projects_cache)

        # 统计项目级标签
        all_tags = []
        feature_stats = {"pending": 0, "in_progress": 0, "completed": 0}
        total_features = 0
        total_notes = 0

        # 统计条目级标签
        feature_tag_counts = {}
        note_tag_counts = {}

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data is None:
                continue

            all_tags.extend(project_data["info"]["tags"])

            total_features += len(project_data["features"])
            for feature in project_data["features"]:
                status = feature.get("status", "pending")
                if status in feature_stats:
                    feature_stats[status] += 1

                # 统计功能标签
                for tag in feature.get("tags", []):
                    feature_tag_counts[tag] = feature_tag_counts.get(tag, 0) + 1

            total_notes += len(project_data["notes"])

            # 统计笔记标签
            for note in project_data["notes"]:
                for tag in note.get("tags", []):
                    note_tag_counts[tag] = note_tag_counts.get(tag, 0) + 1

        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "success": True,
            "stats": {
                "total_projects": total_projects,
                "total_features": total_features,
                "total_notes": total_notes,
                "feature_status": feature_stats,
                "top_project_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "top_feature_tags": sorted(feature_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "top_note_tags": sorted(note_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        }
