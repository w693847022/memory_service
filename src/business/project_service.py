"""Project Service Module - 项目管理业务逻辑服务.

提供项目注册、查询、管理等业务逻辑。
"""

from datetime import datetime
from typing import Optional, Dict, List, Any, Union
import threading

from business.core.groups import (
    GroupType, all_group_names, DEFAULT_TAGS,
    validate_group_name, validate_status, validate_severity,
    validate_content_length, validate_summary_length,
    get_group_config, validate_related, get_all_groups,
    UnifiedGroupConfig, DEFAULT_RELATED_RULES,
    CONTENT_SEPARATE_GROUPS,
)
from business.core.lock_manager import LockGranularity
from business.models.item import Item, ItemRelated


class ProjectService:
    """项目管理业务逻辑服务类.

    封装项目管理相关的业务逻辑，包括：
    - 项目注册、重命名、删除、归档
    - 条目添加、更新、删除
    - 项目信息查询
    """

    def __init__(self, storage):
        """初始化项目服务.

        Args:
            storage: 存储层实例（需要实现项目数据访问方法）
        """
        self.storage = storage
        # 项目级锁字典（用于服务层并发控制）
        self._project_locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()  # 保护 project_locks 字典的锁 = storage

    # ==================== 锁管理 ====================

    def _get_project_lock(self, project_id: str) -> threading.Lock:
        """获取项目级锁（双重检查锁定）.

        Args:
            project_id: 项目ID

        Returns:
            该项目的锁对象
        """
        lock = self._project_locks.get(project_id)
        if lock is None:
            with self._locks_lock:
                lock = self._project_locks.get(project_id)
                if lock is None:
                    lock = threading.Lock()
                    self._project_locks[project_id] = lock
        return lock

    def _cleanup_project_lock(self, project_id: str) -> None:
        """清理项目锁（在项目删除时调用）.

        Args:
            project_id: 项目ID
        """
        with self._locks_lock:
            if project_id in self._project_locks:
                del self._project_locks[project_id]

    # ==================== 验证辅助方法 ====================

    def _validate_tag_name(self, tag_name: str) -> bool:
        """验证标签名称格式.

        Args:
            tag_name: 标签名称

        Returns:
            是否有效
        """
        import re
        pattern = r'^[a-zA-Z0-9_-]{1,30}$'
        return bool(re.match(pattern, tag_name))

    def _validate_tag_length(self, tag: str, max_tokens: int = 10) -> tuple[bool, str]:
        """验证单个标签长度（基于 token 估算）.

        Args:
            tag: 要验证的标签
            max_tokens: 最大 token 数

        Returns:
            (是否有效, 错误信息)
        """
        if not tag:
            return False, "标签不能为空"
        estimated_tokens = len(tag) / 3
        if estimated_tokens > max_tokens:
            return False, f"标签 '{tag}' 过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
        return True, ""

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
        """注册新项目.

        Args:
            name: 项目名称
            path: 项目路径（可选）
            summary: 项目摘要（可选）
            tags: 项目标签列表（可选）
            git_remote: Git 远程名称（可选）
            git_remote_url: Git 远程 URL（可选）

        Returns:
            操作结果
        """
        project_id = self.storage._generate_id(name)

        # 使用项目级锁
        with self.storage.lock_manager.acquire_project(project_id) as lock_result:
            if not lock_result.acquired:
                return {
                    "success": False,
                    "error": "concurrent_update",
                    "retryable": True,
                    "message": "项目正在被创建，请稍后重试"
                }

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

            # 初始化标签注册表
            tag_registry = {}
            for tag in DEFAULT_TAGS:
                tag_registry[tag] = {
                    "summary": f"默认标签: {tag}",
                    "created_at": datetime.now().isoformat(),
                    "usage_count": 0,
                    "aliases": []
                }
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

            if self.storage.save_project_data(project_id, project_data):
                return {
                    "success": True,
                    "project_id": project_id,
                    "message": f"项目 '{name}' 已成功注册，ID: {project_id}"
                }

            return {"success": False, "error": "保存数据失败"}

    def project_rename(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """重命名项目（修改 name 字段并重命名目录）.

        Args:
            project_id: 项目 UUID
            new_name: 新的项目名称

        Returns:
            操作结果
        """
        project_data = self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        old_name = project_data["info"]["name"]

        # 检查新名称是否已存在
        existing_projects = self.storage.list_all_projects()
        for pid, pname in existing_projects.items():
            if pname == new_name and pid != project_id:
                return {"success": False, "error": f"项目名称 '{new_name}' 已存在"}

        # 检查项目是否已归档
        if self.storage.is_archived(project_id):
            return {"success": False, "error": "已归档的项目不能重命名"}

        # 获取项目路径
        project_dir = self.storage._get_project_dir(project_id)
        new_dir = self.storage.storage_dir / new_name

        if project_dir.exists() and project_dir.name != new_name:
            # 执行目录重命名
            result = self.storage.safe_migrate_project_dir(project_dir, new_dir, new_name)
            if not result["success"]:
                return {"success": False, "error": result.get("error", "重命名失败")}
            # 清理归档文件
            self.storage.delete_archive_file(result.get("archived_path"))

        # 更新内存中的项目数据
        project_data["info"]["name"] = new_name
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self.storage.save_project_data(project_id, project_data):
            # 更新缓存
            self.storage.refresh_projects_cache()
            return {
                "success": True,
                "old_name": old_name,
                "new_name": new_name,
                "message": f"项目已从 '{old_name}' 重命名为 '{new_name}'"
            }

        return {"success": False, "error": "保存数据失败"}

    # ==================== 项目查询 ====================

    def list_projects(self, include_archived: bool = False) -> Dict[str, Any]:
        """列出所有项目.

        Args:
            include_archived: 是否包含归档项目

        Returns:
            项目列表
        """
        self.storage.refresh_projects_cache()
        projects = []

        for project_id, name in self.storage.list_all_projects().items():
            project_data = self.storage.get_project_data(project_id)
            if project_data and "info" in project_data:
                info = project_data["info"]
                projects.append({
                    "id": project_id,
                    "name": name,
                    "summary": info.get("summary", ""),
                    "tags": info.get("tags", []),
                    "status": "archived" if self.storage.is_archived(project_id) else "active"
                })

        if include_archived:
            # 添加归档项目
            for archived in self.storage.get_archived_projects():
                projects.append({
                    "id": archived.get("id", ""),
                    "name": archived.get("name", ""),
                    "summary": archived.get("summary", ""),
                    "tags": archived.get("tags", []),
                    "status": "archived",
                    "archived_at": archived.get("archived_at", "")
                })

        return {
            "success": True,
            "projects": projects,
            "total": len(projects)
        }

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息.

        Args:
            project_id: 项目ID

        Returns:
            项目信息
        """
        project_data = self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        return {
            "success": True,
            "data": project_data
        }

    # ==================== 条目操作 ====================

    def validate_add_item(
        self,
        group: str,
        content: str,
        summary: str,
        status: Optional[str],
        severity: str,
        related: Optional[Union[str, Dict[str, List[str]]]],
        tag_list: List[str],
        custom_groups: Optional[Dict[str, UnifiedGroupConfig]] = None,
        default_rules: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """统一验证添加条目的所有参数.

        Args:
            group: 分组类型
            content: 条目内容
            summary: 条目摘要
            status: 状态（可选）
            severity: 严重程度
            related: 关联数据
            tag_list: 标签列表
            custom_groups: 自定义组配置字典（可选）
            default_rules: 默认关联规则（可选）

        Returns:
            验证结果
        """
        # 验证 group 有效性
        is_valid, error_msg = validate_group_name(group, custom_groups)
        if not is_valid:
            return {"success": False, "error": error_msg}

        # 获取自定义组配置
        custom_config = custom_groups.get(group) if custom_groups else None

        # status 参数验证
        config = get_group_config(group)
        if config and config.status_values:
            if status is None:
                return {"success": False, "error": "features/fixes 分组必须传入 status 参数 (有效值: pending/in_progress/completed)"}
            is_valid, error_msg = validate_status(status, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}
        elif custom_config and custom_config.enable_status:
            if status is None:
                return {"success": False, "error": f"'{group}' 分组必须传入 status 参数"}
            is_valid, error_msg = validate_status(status, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}
        else:
            status = None

        # severity 参数验证
        if severity is not None:
            is_valid, error_msg = validate_severity(severity, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        # 验证必需参数
        if not content:
            return {"success": False, "error": "content 参数不能为空"}

        # 验证 content 长度
        is_valid, error_msg, _ = validate_content_length(content, group, custom_config)
        if not is_valid:
            return {"success": False, "error": error_msg}

        # 验证 summary
        if not summary or not summary.strip():
            return {"success": False, "error": "summary 参数不能为空"}

        is_valid, error_msg, _ = validate_summary_length(summary, group, custom_config)
        if not is_valid:
            return {"success": False, "error": error_msg}

        # 验证 tags
        if not tag_list:
            return {"success": False, "error": "tags 参数不能为空"}

        for tag in tag_list:
            is_valid, error_msg = self._validate_tag_length(tag, max_tokens=10)
            if not is_valid:
                return {"success": False, "error": error_msg}

        # 解析并验证 related 参数
        is_valid, error_msg, related_dict = validate_related(related, group, custom_config, default_rules)
        if not is_valid:
            return {"success": False, "error": error_msg}

        return {"success": True, "related_dict": related_dict}

    def validate_update_item(
        self,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        related: Optional[Union[str, Dict[str, List[str]]]] = None,
        custom_groups: Optional[Dict[str, UnifiedGroupConfig]] = None,
        default_rules: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """统一验证更新条目参数.

        Args:
            group: 分组类型
            item_id: 条目ID
            content: 新内容（可选）
            summary: 新摘要（可选）
            related: 关联数据（可选）
            custom_groups: 自定义组配置字典（可选）
            default_rules: 默认关联规则（可选）

        Returns:
            验证结果
        """
        is_valid, error_msg = validate_group_name(group, custom_groups)
        if not is_valid:
            return {"success": False, "error": error_msg}

        custom_config = custom_groups.get(group) if custom_groups else None

        # 验证 content
        if content is not None:
            if not content:
                return {"success": False, "error": "content 不能为空"}
            is_valid, error_msg, _ = validate_content_length(content, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        # 验证 summary
        if summary is not None:
            if not summary.strip():
                return {"success": False, "error": "summary 不能为空"}
            is_valid, error_msg, _ = validate_summary_length(summary, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        # 验证 related
        related_dict = None
        if related is not None:
            is_valid, error_msg, related_dict = validate_related(related, group, custom_config, default_rules)
            if not is_valid:
                return {"success": False, "error": error_msg}

        return {"success": True, "related_dict": related_dict}

    def add_item(
        self,
        project_id: str,
        group: str,
        content: str,
        summary: str,
        status: Optional[str] = None,
        severity: str = "medium",
        related: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """添加项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            content: 条目内容
            summary: 条目摘要
            status: 状态（可选）
            severity: 严重程度（可选）
            related: 关联数据（可选）
            tags: 标签列表（可选）

        Returns:
            操作结果
        """
        # 使用分组级锁
        with self.storage.lock_manager.acquire_group(project_id, group) as lock_result:
            if not lock_result.acquired:
                return {
                    "success": False,
                    "error": "concurrent_update",
                    "retryable": True,
                    "message": f"分组 '{group}' 正在被修改，请稍后重试"
                }

            project_data = self.storage.get_project_data(project_id)
            if project_data is None:
                return {"success": False, "error": f"项目 '{project_id}' 不存在"}

            # 确定 ID 前缀
            prefix_map = {"features": "feat", "notes": "note", "fixes": "fix", "standards": "std"}
            prefix = prefix_map.get(group, "feat")

            # 生成新条目 ID
            item_id = self.storage.generate_item_id(prefix, project_id, project_data)

            # 生成时间戳
            timestamps = self.storage.generate_timestamps()

            # 创建新条目
            new_item = {
                "id": item_id,
                "summary": summary,
                "content": content,
                "tags": tags or [],
                "created_at": timestamps["created_at"],
                "updated_at": timestamps["updated_at"]
            }

            if status:
                new_item["status"] = status
            if severity:
                new_item["severity"] = severity
            if related:
                new_item["related"] = related

            # 添加到对应分组
            if group not in project_data:
                project_data[group] = []
            project_data[group].append(new_item)

            # 更新标签使用计数
            tag_registry = project_data.get("tag_registry", {})
            for tag in tags or []:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1

            # 更新项目更新时间
            self.storage.update_timestamp(project_data["info"])

            # 保存
            if self.storage.save_project_data(project_id, project_data):
                # 保存 content 到独立文件
                if group in CONTENT_SEPARATE_GROUPS:
                    self.storage.save_item_content(project_id, group, item_id, content)

                return {
                    "success": True,
                    "project_id": project_id,
                    "group": group,
                    "item_id": item_id,
                    "message": f"条目 '{item_id}' 已添加到 '{group}' 分组"
                }

            return {"success": False, "error": "保存数据失败"}

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
        tags: Optional[List[str]] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """更新项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            item_id: 条目ID
            content: 内容更新（可选）
            summary: 摘要更新（可选）
            status: 状态更新（可选）
            severity: 严重程度更新（可选）
            related: 关联更新（可选）
            tags: 标签更新（可选）
            expected_version: 期望的版本号（可选，用于乐观锁）

        Returns:
            操作结果
        """
        # 使用条目级锁
        with self.storage.lock_manager.acquire_item(project_id, group, item_id) as lock_result:
            if not lock_result.acquired:
                return {
                    "success": False,
                    "error": "concurrent_update",
                    "retryable": True,
                    "message": f"条目 '{item_id}' 正在被修改，请稍后重试"
                }

            # 准备更新字段（不要先调用 get_project_data，避免死锁！）
            updates = {}
            if content is not None:
                updates["content"] = content
            if summary is not None:
                updates["summary"] = summary
            if status is not None:
                updates["status"] = status
            if severity is not None:
                updates["severity"] = severity
            if related is not None:
                updates["related"] = related
            if tags is not None:
                updates["tags"] = tags

            # 更新时间戳
            timestamps = self.storage.generate_timestamps()
            updates["updated_at"] = timestamps["updated_at"]

            # 直接调用 CAS 方法，让它返回旧数据（避免死锁）
            result = self.storage.update_item_with_version_check(
                project_id=project_id,
                group=group,
                item_id=item_id,
                expected_version=expected_version,
                updates=updates
            )

            if not result.get("success"):
                # 检查是否是版本冲突
                if result.get("error") == "version_mismatch":
                    return {
                        "success": False,
                        "error": "version_conflict",
                        "retryable": True,
                        "current_version": result.get("current_version"),
                        "expected_version": result.get("expected_version"),
                        "message": f"条目已被其他请求修改，当前版本: {result.get('current_version')}"
                    }
                return result

            # CAS 成功后，处理非原子操作（在锁内）
            # 这些操作即使失败也不影响数据一致性
            old_item = result.get("old_item", {})
            old_tags = old_item.get("tags", [])

            # 更新成功后，处理标签计数和独立 content 文件
            # 注意：这里需要重新加载 project_data 来获取最新的 tag_registry
            project_data = self.storage.get_project_data(project_id)
            if project_data is not None:
                tag_registry = project_data.get("tag_registry", {})
                removed_tags = set(old_tags) - set(tags or [])
                added_tags = set(tags or []) - set(old_tags)

                for tag in removed_tags:
                    if tag in tag_registry:
                        tag_registry[tag]["usage_count"] = max(0, tag_registry[tag].get("usage_count", 0) - 1)

                for tag in added_tags:
                    if tag in tag_registry:
                        tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1

                # 更新项目更新时间
                self.storage.update_timestamp(project_data["info"])

                # 保存标签计数更新
                self.storage.save_project_data(project_id, project_data)

            # 更新独立 content 文件
            if group in CONTENT_SEPARATE_GROUPS and content is not None:
                self.storage.save_item_content(project_id, group, item_id, content)

            return {
                "success": True,
                "project_id": project_id,
                "group": group,
                "item_id": item_id,
                "item": result.get("item") or {},
                "version": result.get("version") or 1,
                "message": f"条目 '{item_id}' 已更新"
            }

    def delete_item(
        self,
        project_id: str,
        group: str,
        item_id: str
    ) -> Dict[str, Any]:
        """删除项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            item_id: 条目ID

        Returns:
            操作结果
        """
        # 使用分组级锁
        with self.storage.lock_manager.acquire_group(project_id, group) as lock_result:
            if not lock_result.acquired:
                return {
                    "success": False,
                    "error": "concurrent_update",
                    "retryable": True,
                    "message": f"分组 '{group}' 正在被修改，请稍后重试"
                }

            project_data = self.storage.get_project_data(project_id)
            if project_data is None:
                return {"success": False, "error": f"项目 '{project_id}' 不存在"}

            items = project_data.get(group, [])
            item_index = None
            deleted_item = None

            for i, item in enumerate(items):
                if item.get("id") == item_id:
                    item_index = i
                    deleted_item = item
                    break

            if item_index is None:
                return {"success": False, "error": f"在分组 '{group}' 中找不到条目 '{item_id}'"}

            # 减少标签使用计数
            tag_registry = project_data.get("tag_registry", {})
            # deleted_item 此时保证不为 None（因为找到了 item_index）
            for tag in (deleted_item or {}).get("tags", []):
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = max(0, tag_registry[tag].get("usage_count", 0) - 1)

            # 删除条目
            del items[item_index]

            # 更新项目更新时间
            self.storage.update_timestamp(project_data["info"])

            # 保存
            if self.storage.save_project_data(project_id, project_data):
                # 删除独立的内容文件
                if group in CONTENT_SEPARATE_GROUPS:
                    self.storage.delete_item_content(project_id, group, item_id)

                # 清理条目锁
                self.storage.lock_manager.cleanup_item_lock(project_id, group, item_id)

                return {
                    "success": True,
                    "project_id": project_id,
                    "group": group,
                    "item_id": item_id,
                    "message": f"条目 '{item_id}' 已删除"
                }

            return {"success": False, "error": "保存数据失败"}

    # ==================== 项目归档/删除 ====================

    def remove_project(self, project_id: str, mode: str = "archive") -> Dict[str, Any]:
        """归档或永久删除项目.

        Args:
            project_id: 项目ID
            mode: 操作模式 - "archive"(归档) 或 "delete"(永久删除)

        Returns:
            操作结果
        """
        project_data = self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if mode == "delete":
            # 永久删除项目目录
            project_dir = self.storage._get_project_dir(project_id)
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)

            # 清理项目锁，防止内存泄漏
            self.storage._cleanup_project_lock(project_id)

            # 从缓存移除
            self.storage.refresh_projects_cache()

            return {
                "success": True,
                "message": f"项目 '{project_id}' 已永久删除"
            }

        # 归档模式
        result = self.storage.archive_project(project_id)
        if result.get("success"):
            self.storage.refresh_projects_cache()

        return result

    # ==================== 分组管理 ====================

    def list_groups(self, project_id: str) -> Dict[str, Any]:
        """列出项目的所有分组.

        Args:
            project_id: 项目ID

        Returns:
            分组列表及统计信息
        """
        project_data = self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        group_configs = self.storage.get_group_configs(project_id)

        groups = []
        for group_name in all_group_names():
            items = project_data.get(group_name, [])
            groups.append({
                "name": group_name,
                "count": len(items)
            })

        # 添加自定义组
        custom_groups = group_configs.get("groups", {})
        for group_name in custom_groups.keys():
            if group_name not in all_group_names():
                items = project_data.get(group_name, [])
                groups.append({
                    "name": group_name,
                    "count": len(items),
                    "is_custom": True
                })

        return {
            "success": True,
            "groups": groups
        }
