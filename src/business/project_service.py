"""Project Service Module - 项目管理业务逻辑服务.

提供项目注册、查询、管理等业务逻辑。
所有涉及 IO 的方法均为异步，使用 barrier_manager 进行并发控制。
"""

from datetime import datetime
from typing import Optional, Dict, List, Any, Union

from src.models import Item, ItemCreate, ItemUpdate
from src.models.storage import ProjectData
from business.core.groups import (
    all_group_names, DEFAULT_TAGS,
    validate_group_name, validate_status, validate_severity,
    validate_content_length, validate_summary_length,
    get_group_config, validate_related,
    UnifiedGroupConfig,
    CONTENT_SEPARATE_GROUPS,
    DEFAULT_GROUP_CONFIGS,
)
from business.core.barrier_decorator import barrier
from business.core.barrier_constants import OperationLevel
from src.common.consts import (
    FieldNames,
    ErrorMessages,
    SuccessMessages,
    StatusValues,
    SeverityValues,
    Defaults
)
from src.models.version import ProjectVersions
from src.models.response import ResponseBuilder


class ProjectService:
    """项目管理业务逻辑服务类."""

    def __init__(self, storage):
        self.storage = storage

    # ==================== 验证辅助方法 ====================

    def _validate_tag_name(self, tag_name: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9_-]{1,30}$'
        return bool(re.match(pattern, tag_name))

    def _validate_tag_length(self, tag: str, max_tokens: int = 10) -> tuple[bool, str]:
        if not tag:
            return False, "标签不能为空"
        estimated_tokens = len(tag) / 3
        if estimated_tokens > max_tokens:
            return False, f"标签 '{tag}' 过长：预估 {int(estimated_tokens)} tokens，最大允许 {max_tokens} tokens（约 {max_tokens * 3} 字符）"
        return True, ""

    # ==================== 项目注册 ====================

    @barrier(level=OperationLevel.L1, files=["_index.json"])
    async def register_project(
        self,
        name: str,
        path: Optional[str] = None,
        summary: str = "",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        from src.models.project import ProjectInitialData
        from business.core.groups import DEFAULT_GROUP_CONFIGS

        project_id = self.storage._generate_id(name)

        initial_data = ProjectInitialData.create(
            project_id=project_id,
            name=name,
            path=path,
            summary=summary,
            tags=tags,
            group_configs=DEFAULT_GROUP_CONFIGS,
            default_tags=DEFAULT_TAGS
        )

        # 转换为存储格式 dict，然后构建 ProjectData
        storage_dict = initial_data.to_storage_dict()
        project_data = ProjectData.from_storage(storage_dict)

        if await self.storage.save_project_data(project_id, project_data):
            return ResponseBuilder.success(
                data={"project_id": project_id},
                message=SuccessMessages.PROJECT_REGISTERED.format(name=name, project_id=project_id)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L2, files=["_project.json"], key="{project_id}")
    async def project_rename(self, project_id: str, new_name: str) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        old_name = project_data.metadata.name

        existing_projects = await self.storage.list_all_projects()
        for pid, pname in existing_projects.items():
            if pname == new_name and pid != project_id:
                return ResponseBuilder.error(f"项目名称 '{new_name}' 已存在").to_dict()

        if await self.storage.is_archived(project_id):
            return ResponseBuilder.error("已归档的项目不能重命名").to_dict()

        project_dir = self.storage._get_project_dir(project_id)
        new_dir = self.storage.storage_dir / new_name

        if project_dir.exists() and project_dir.name != new_name:
            result = self.storage.safe_migrate_project_dir(project_dir, new_dir, new_name)
            if not result["success"]:
                return ResponseBuilder.error(result.get("error", "重命名失败")).to_dict()
            self.storage.delete_archive_file(result.get("archived_path"))

        # 操作模型
        project_data.metadata.name = new_name
        project_data.name = new_name
        project_data.touch()
        project_data.increment_version("project")

        if await self.storage.save_project_data(project_id, project_data):
            await self.storage.refresh_projects_cache()
            return ResponseBuilder.success(
                data={"old_name": old_name, "new_name": new_name},
                message=f"项目已从 '{old_name}' 重命名为 '{new_name}'"
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    # ==================== 项目查询 ====================

    async def list_projects(self, include_archived: bool = False) -> Dict[str, Any]:
        await self.storage.refresh_projects_cache()
        projects = []

        all_projects = await self.storage.list_all_projects()
        for project_id, name in all_projects.items():
            project_data = await self.storage.get_project_data(project_id)
            if project_data:
                projects.append({
                    "id": project_id,
                    "name": name,
                    "summary": project_data.metadata.summary,
                    "tags": project_data.metadata.tags,
                    "status": "archived" if await self.storage.is_archived(project_id) else "active"
                })

        if include_archived:
            for archived in await self.storage.get_archived_projects():
                projects.append({
                    "id": archived.get("id", ""),
                    "name": archived.get("name", ""),
                    "summary": archived.get("summary", ""),
                    "tags": archived.get("tags", []),
                    "status": "archived",
                    "archived_at": archived.get("archived_at", "")
                })

        return {"success": True, "projects": projects, "total": len(projects)}

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        # 使用 to_storage() 转换为 dict 用于响应
        data_dict = project_data.to_storage()
        result = ResponseBuilder.success(data=data_dict).to_dict()
        result[FieldNames.VERSION] = project_data.version
        result[FieldNames.VERSIONS] = project_data.versions
        return result

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
        is_valid, error_msg = validate_group_name(group, custom_groups)
        if not is_valid:
            return {"success": False, "error": error_msg}

        custom_config = custom_groups.get(group) if custom_groups else None

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

        if severity is not None:
            is_valid, error_msg = validate_severity(severity, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        if not content:
            return {"success": False, "error": "content 参数不能为空"}

        is_valid, error_msg, _ = validate_content_length(content, group, custom_config)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not summary or not summary.strip():
            return {"success": False, "error": "summary 参数不能为空"}

        is_valid, error_msg, _ = validate_summary_length(summary, group, custom_config)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not tag_list:
            return {"success": False, "error": "tags 参数不能为空"}

        for tag in tag_list:
            is_valid, error_msg = self._validate_tag_length(tag, max_tokens=10)
            if not is_valid:
                return {"success": False, "error": error_msg}

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
        is_valid, error_msg = validate_group_name(group, custom_groups)
        if not is_valid:
            return {"success": False, "error": error_msg}

        custom_config = custom_groups.get(group) if custom_groups else None

        if content is not None:
            if not content:
                return {"success": False, "error": "content 不能为空"}
            is_valid, error_msg, _ = validate_content_length(content, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        if summary is not None:
            if not summary.strip():
                return {"success": False, "error": "summary 不能为空"}
            is_valid, error_msg, _ = validate_summary_length(summary, group, custom_config)
            if not is_valid:
                return {"success": False, "error": error_msg}

        related_dict = None
        if related is not None:
            is_valid, error_msg, related_dict = validate_related(related, group, custom_config, default_rules)
            if not is_valid:
                return {"success": False, "error": error_msg}

        return {"success": True, "related_dict": related_dict}

    @barrier(level=OperationLevel.L4, files=["{group}/"], key="{project_id}:{group}")
    async def add_item(
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
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        prefix_map = {"features": "feat", "notes": "note", "fixes": "fix", "standards": "std"}
        prefix = prefix_map.get(group, "feat")

        item_id = self.storage.generate_item_id(prefix, project_id, project_data)

        timestamps = self.storage.generate_timestamps()

        item_create = ItemCreate(
            summary=summary,
            content=content,
            tags=tags or [],
            status=status,
            severity=severity,
            related=related
        )

        new_item = Item(
            id=item_id,
            summary=item_create.summary,
            content=item_create.content,
            tags=item_create.tags,
            status=item_create.status,
            severity=item_create.severity,
            related=item_create.related,
            created_at=timestamps["created_at"],
            updated_at=timestamps["updated_at"],
            version=1
        )

        # 使用模型方法添加条目
        project_data.add_item(group, new_item)
        project_data.increment_version(group)

        # 更新标签使用计数
        for tag in tags or []:
            tag_info = project_data.get_tag(tag)
            if tag_info:
                tag_info.usage_count += 1

        project_data.touch()

        if await self.storage.save_project_data(project_id, project_data):
            if group in CONTENT_SEPARATE_GROUPS:
                await self.storage.save_item_content(project_id, group, item_id, content)

            return ResponseBuilder.success(
                data={
                    "project_id": project_id,
                    "group": group,
                    "item_id": item_id,
                    "item": new_item.model_dump()
                },
                message=SuccessMessages.ITEM_ADDED.format(item_id=item_id, group=group)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L5, files=["{group}/{item_id}.json"], key="{project_id}:{group}:{item_id}")
    async def update_item(
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
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        item = project_data.get_item(group, item_id)
        if item is None:
            return ResponseBuilder.error(
                ErrorMessages.ITEM_NOT_FOUND.format(group=group, item_id=item_id)
            ).to_dict()

        # 版本检测
        current_version = item.version
        if expected_version is not None and current_version != expected_version:
            return {
                "success": False,
                "error": "version_conflict",
                "retryable": True,
                "current_version": current_version,
                "expected_version": expected_version,
                "message": f"条目已被其他请求修改，当前版本: {current_version}"
            }

        old_tags = item.tags

        # 使用 ItemUpdate 验证
        item_update = ItemUpdate(
            summary=summary,
            content=content,
            tags=tags,
            status=status,
            severity=severity,
            related=related,
            version=current_version
        )

        # 直接修改模型属性
        update_data = item_update.model_dump(exclude_none=True)
        for field, value in update_data.items():
            if field != "version" and value is not None:
                setattr(item, field, value)

        item.updated_at = datetime.now().isoformat()
        item.version = current_version + 1

        project_data.increment_version("project")

        # 更新标签计数
        removed_tags = set(old_tags) - set(tags or old_tags)
        added_tags = set(tags or old_tags) - set(old_tags)

        for tag in removed_tags:
            tag_info = project_data.get_tag(tag)
            if tag_info:
                tag_info.usage_count = max(0, tag_info.usage_count - 1)

        for tag in added_tags:
            tag_info = project_data.get_tag(tag)
            if tag_info:
                tag_info.usage_count += 1

        project_data.touch()

        if await self.storage.save_project_data(project_id, project_data):
            if group in CONTENT_SEPARATE_GROUPS and content is not None:
                await self.storage.save_item_content(project_id, group, item_id, content)

            item_data = item.model_dump(exclude={"content"} if group in CONTENT_SEPARATE_GROUPS else set())
            result = ResponseBuilder.success(
                data={"project_id": project_id, "group": group, "item_id": item_id},
                message=SuccessMessages.ITEM_UPDATED.format(item_id=item_id)
            ).to_dict()
            result["item"] = item_data
            result["version"] = item.version
            return result

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L4, files=["{group}/"], key="{project_id}:{group}")
    async def delete_item(
        self,
        project_id: str,
        group: str,
        item_id: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        deleted_item = project_data.remove_item(group, item_id)
        if deleted_item is None:
            return ResponseBuilder.error(
                ErrorMessages.ITEM_NOT_FOUND.format(group=group, item_id=item_id)
            ).to_dict()

        # 减少标签使用计数
        for tag in deleted_item.tags:
            tag_info = project_data.get_tag(tag)
            if tag_info:
                tag_info.usage_count = max(0, tag_info.usage_count - 1)

        project_data.increment_version(group)
        project_data.touch()

        if await self.storage.save_project_data(project_id, project_data):
            if group in CONTENT_SEPARATE_GROUPS:
                self.storage.delete_item_content(project_id, group, item_id)

            return ResponseBuilder.success(
                data={"project_id": project_id, "group": group, "item_id": item_id},
                message=SuccessMessages.ITEM_DELETED.format(item_id=item_id)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    # ==================== 项目归档/删除 ====================

    @barrier(level=OperationLevel.L1, files=["_index.json"])
    async def remove_project(self, project_id: str, mode: str = "archive") -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        from src.common.consts import OperationModes

        if mode == OperationModes.DELETE:
            project_dir = self.storage._get_project_dir(project_id)
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)
            await self.storage.refresh_projects_cache()
            return ResponseBuilder.success(message=f"项目 '{project_id}' 已永久删除").to_dict()

        result = await self.storage.archive_project(project_id)
        if result.get("success"):
            await self.storage.refresh_projects_cache()
        return result

    # ==================== 分组管理 ====================

    async def list_groups(self, project_id: str) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        group_configs = await self.storage.get_group_configs(project_id)
        custom_groups = group_configs.get("groups", {})

        groups = []

        for group_name in all_group_names():
            items = project_data.get_items(group_name)
            config = UnifiedGroupConfig.from_dict(DEFAULT_GROUP_CONFIGS.get(group_name, {}))
            if group_name in custom_groups:
                config = UnifiedGroupConfig.from_dict(custom_groups[group_name])

            groups.append({
                "name": group_name,
                "count": len(items),
                "is_builtin": True,
                **config.to_dict()
            })

        for group_name, config_dict in custom_groups.items():
            if group_name not in all_group_names():
                items = project_data.get_items(group_name)
                config = UnifiedGroupConfig.from_dict(config_dict)
                groups.append({
                    "name": group_name,
                    "count": len(items),
                    "is_builtin": False,
                    **config.to_dict()
                })

        return {
            "success": True,
            "groups": groups,
            "settings": group_configs.get("group_settings", {})
        }

    async def get_group_config(self, project_id: str, group: str) -> Dict[str, Any]:
        group_configs = await self.storage.get_group_configs(project_id)
        custom_groups = group_configs.get("groups", {})
        if group in custom_groups:
            return {"success": True, "config": UnifiedGroupConfig.from_dict(custom_groups[group]).to_dict()}
        if group in DEFAULT_GROUP_CONFIGS:
            return {"success": True, "config": DEFAULT_GROUP_CONFIGS[group]}
        return {"success": False, "error": f"组 '{group}' 不存在"}

    @barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
    async def update_group_config(
        self,
        project_id: str,
        group: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        group_configs = await self.storage.get_group_configs(project_id)

        is_valid, error_msg = validate_group_name(group, group_configs.get("groups", {}))
        if not is_valid:
            return {"success": False, "error": error_msg}

        try:
            unified_config = UnifiedGroupConfig.from_dict(config)
        except Exception as e:
            return {"success": False, "error": f"配置格式错误: {e}"}

        if "groups" not in group_configs:
            group_configs["groups"] = {}
        group_configs["groups"][group] = unified_config.to_dict()

        if await self.storage.save_group_configs(project_id, group_configs):
            return {"success": True, "message": f"组 '{group}' 配置已更新"}
        return ResponseBuilder.error(ErrorMessages.SAVE_CONFIG_FAILED).to_dict()
