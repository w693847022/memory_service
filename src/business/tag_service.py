"""Tag Service Module - 标签管理业务逻辑服务.

提供标签注册、更新、删除、合并等业务逻辑。
所有涉及 IO 的方法均为 async，使用 barrier_manager 进行并发控制。
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.models import TagInfo
from src.models.storage import ProjectData
from src.models.enums import GroupType
from business.core.barrier_decorator import barrier
from business.core.barrier_constants import OperationLevel
from src.common.consts import (
    FieldNames,
    ErrorMessages,
    SuccessMessages,
    StatusValues,
    SeverityValues
)
from src.models.response import ResponseBuilder


class TagService:
    """标签管理业务逻辑服务类."""

    def __init__(self, storage):
        self.storage = storage

    # ==================== 同步验证方法 ====================

    def _validate_tag_name(self, tag_name: str) -> bool:
        pattern = r'^[a-zA-Z0-9_-]{1,30}$'
        return bool(re.match(pattern, tag_name))

    def _validate_description(self, description: str) -> bool:
        return 4 <= len(description) <= 100

    # ==================== 异步业务方法 ====================

    @barrier(level=OperationLevel.L3, files=["_tags.json"], key="{project_id}")
    async def register_tag(
        self,
        project_id: str,
        tag_name: str,
        summary: str,
        aliases: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not self._validate_tag_name(tag_name):
            return ResponseBuilder.error(
                f"标签名称格式无效：'{tag_name}'。只允许英文字母、数字、下划线、连字符，长度1-30字符"
            ).to_dict()

        if not self._validate_description(summary):
            return ResponseBuilder.error(
                f"摘要长度无效：需要3-200字符，当前为 {len(summary)} 字符"
            ).to_dict()

        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        existing_tag = project_data.get_tag(tag_name)
        if existing_tag:
            return ResponseBuilder.error(
                f"标签 '{tag_name}' 已经注册",
                data={"tag_info": existing_tag.model_dump()}
            ).to_dict()

        tag_info = TagInfo(
            name=tag_name,
            summary=summary,
            aliases=aliases or [],
            usage_count=0
        )

        project_data.register_tag(tag_info)
        project_data.touch()
        project_data.increment_version("tag_registry")

        if await self.storage.save_project_data(project_id, project_data):
            registered_tag = project_data.get_tag(tag_name)
            return ResponseBuilder.success(
                data={"tag_name": tag_name, "tag_info": registered_tag.model_dump()},
                message=SuccessMessages.TAG_REGISTERED.format(tag_name=tag_name)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L3, files=["_tags.json"], key="{project_id}")
    async def update_tag(
        self,
        project_id: str,
        tag_name: str,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        if summary is not None and not self._validate_description(summary):
            return ResponseBuilder.error(
                f"摘要长度无效：需要3-200字符，当前为 {len(summary)} 字符"
            ).to_dict()

        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        tag_info = project_data.get_tag(tag_name)
        if tag_info is None:
            return ResponseBuilder.error(
                ErrorMessages.TAG_NOT_REGISTERED.format(tag_name=tag_name)
            ).to_dict()

        if summary is not None:
            tag_info.summary = summary

        project_data.touch()
        project_data.increment_version("tag_registry")

        if await self.storage.save_project_data(project_id, project_data):
            return ResponseBuilder.success(
                data={"tag_info": tag_info.model_dump()},
                message=SuccessMessages.TAG_UPDATED.format(tag_name=tag_name)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L2, files=["_tags.json"], key="{project_id}")
    async def delete_tag(
        self,
        project_id: str,
        tag_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        tag_info = project_data.get_tag(tag_name)
        if tag_info is None:
            return ResponseBuilder.error(
                ErrorMessages.TAG_NOT_REGISTERED.format(tag_name=tag_name)
            ).to_dict()

        if tag_info.usage_count > 0 and not force:
            return ResponseBuilder.error(
                f"标签 '{tag_name}' 正在被 {tag_info.usage_count} 个条目使用，请使用 force=True 强制删除"
            ).to_dict()

        project_data.remove_tag(tag_name)
        project_data.touch()
        project_data.increment_version("tag_registry")

        if await self.storage.save_project_data(project_id, project_data):
            return ResponseBuilder.success(
                message=SuccessMessages.TAG_DELETED.format(tag_name=tag_name)
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    @barrier(level=OperationLevel.L2, files=["_tags.json"], key="{project_id}")
    async def merge_tags(
        self,
        project_id: str,
        old_tag: str,
        new_tag: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        old_tag_info = project_data.get_tag(old_tag)
        new_tag_info = project_data.get_tag(new_tag)

        if old_tag_info is None:
            return ResponseBuilder.error(f"旧标签 '{old_tag}' 未注册").to_dict()
        if new_tag_info is None:
            return ResponseBuilder.error(f"新标签 '{new_tag}' 未注册").to_dict()
        if old_tag == new_tag:
            return ResponseBuilder.error("旧标签和新标签不能相同").to_dict()

        migrated_count = 0
        affected_groups = []
        all_groups = GroupType.values()

        for group_name in all_groups:
            items = project_data.get_items(group_name)
            group_affected = False
            for item in items:
                if old_tag in item.tags:
                    item.tags.remove(old_tag)
                    if new_tag not in item.tags:
                        item.tags.append(new_tag)
                    migrated_count += 1
                    group_affected = True
            if group_affected:
                affected_groups.append(group_name)

        new_tag_info.usage_count += old_tag_info.usage_count
        project_data.remove_tag(old_tag)
        project_data.touch()
        project_data.increment_version("tag_registry")

        for group_name in affected_groups:
            project_data.increment_version(group_name)

        if await self.storage.save_project_data(project_id, project_data):
            return ResponseBuilder.success(
                data={"migrated_count": migrated_count},
                message=f"已将标签 '{old_tag}' 合并到 '{new_tag}'，迁移了 {migrated_count} 个条目"
            ).to_dict()

        return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

    async def list_all_registered_tags(self, project_id: str) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        groups = GroupType.values()
        tags_list = []

        for tag_name, tag_info in project_data.tag_registry.items():
            tag_groups = []
            group_counts = {}
            for group in groups:
                items = project_data.get_items(group)
                count = sum(1 for item in items if tag_name in item.tags)
                if count > 0:
                    tag_groups.append(group)
                    group_counts[group] = count

            tags_list.append({
                "tag": tag_name,
                "summary": tag_info.summary,
                "usage_count": tag_info.usage_count,
                "created_at": tag_info.model_fields_set and "" or "",
                "aliases": tag_info.aliases,
                "groups": tag_groups,
                "group_counts": group_counts
            })

        tags_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "success": True,
            "project_id": project_id,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    async def list_group_tags(
        self,
        project_id: str,
        group_name: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in GroupType.values():
            return ResponseBuilder.error(
                ErrorMessages.GROUP_NOT_FOUND.format(group_name=group_name)
            ).to_dict()

        items = project_data.get_items(group_name)

        tag_counts = {}
        for tag_name, tag_info in project_data.tag_registry.items():
            count = sum(1 for item in items if tag_name in item.tags)
            if count > 0:
                tag_counts[tag_name] = count

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = []
        for tag, count in sorted_tags:
            tag_info = project_data.get_tag(tag)
            tags_list.append({
                "tag": tag,
                "count": count,
                "summary": tag_info.summary if tag_info else "未注册",
                "usage_count": tag_info.usage_count if tag_info else 0,
                "created_at": "",
                "is_registered": tag_info is not None
            })

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    async def list_unregistered_tags(
        self,
        project_id: str,
        group_name: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in GroupType.values():
            return ResponseBuilder.error(
                ErrorMessages.GROUP_NOT_FOUND.format(group_name=group_name)
            ).to_dict()

        items = project_data.get_items(group_name)

        used_tags = set()
        for item in items:
            used_tags.update(item.tags)

        unregistered_tags = used_tags - set(project_data.tag_registry.keys())

        unregistered_tag_counts = {}
        for tag in unregistered_tags:
            count = sum(1 for item in items if tag in item.tags)
            unregistered_tag_counts[tag] = count

        sorted_tags = sorted(unregistered_tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = [{"tag": tag, "count": count, "suggestion": "建议使用 tag_register 注册此标签"} for tag, count in sorted_tags]

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    async def query_by_tag(
        self,
        project_id: str,
        group_name: str,
        tag: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in GroupType.values():
            return ResponseBuilder.error(
                ErrorMessages.GROUP_NOT_FOUND.format(group_name=group_name)
            ).to_dict()

        items = project_data.get_items(group_name)
        matched_items = [item for item in items if tag in item.tags]

        tag_info = project_data.get_tag(tag)
        is_registered = tag_info is not None

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tag": tag,
            "total": len(matched_items),
            "items": [item.model_dump() for item in matched_items],
            "tag_info": {
                "summary": tag_info.summary,
                "usage_count": tag_info.usage_count,
                "created_at": "",
                "is_registered": is_registered
            } if is_registered else None
        }

    @barrier(level=OperationLevel.L5, files=["{group_name}/{item_id}.json"], key="{project_id}:{group_name}:{item_id}")
    async def add_item_tag(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        tag: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in GroupType.values():
            return ResponseBuilder.error(
                ErrorMessages.GROUP_NOT_FOUND.format(group_name=group_name)
            ).to_dict()

        tag_info = project_data.get_tag(tag)
        if tag_info is None:
            return ResponseBuilder.error(
                f"标签 '{tag}' 未注册，请先使用 tag_register 注册该标签"
            ).to_dict()

        item = project_data.get_item(group_name, item_id)
        if item is None:
            return ResponseBuilder.error(
                ErrorMessages.ITEM_ID_NOT_EXISTS.format(item_id=item_id)
            ).to_dict()

        if tag not in item.tags:
            item.tags.append(tag)
            item.version += 1
            tag_info.usage_count += 1
            project_data.touch()
            project_data.increment_version("project")

            if await self.storage.save_project_data(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已为条目 '{item_id}' 添加标签 '{tag}'",
                    "tags": item.tags
                }
            return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

        return {"success": True, "message": f"标签 '{tag}' 已存在", "tags": item.tags}

    @barrier(level=OperationLevel.L5, files=["{group_name}/{item_id}.json"], key="{project_id}:{group_name}:{item_id}")
    async def remove_item_tag(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        tag: str
    ) -> Dict[str, Any]:
        project_data = await self.storage.get_project_data(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in GroupType.values():
            return ResponseBuilder.error(
                ErrorMessages.GROUP_NOT_FOUND.format(group_name=group_name)
            ).to_dict()

        item = project_data.get_item(group_name, item_id)
        if item is None:
            return ResponseBuilder.error(
                ErrorMessages.ITEM_ID_NOT_EXISTS.format(item_id=item_id)
            ).to_dict()

        if tag in item.tags:
            item.tags.remove(tag)
            item.version += 1

            tag_info = project_data.get_tag(tag)
            if tag_info:
                tag_info.usage_count = max(0, tag_info.usage_count - 1)

            project_data.touch()
            project_data.increment_version("project")

            if await self.storage.save_project_data(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已从条目 '{item_id}' 移除标签 '{tag}'",
                    "tags": item.tags
                }
            return ResponseBuilder.error(ErrorMessages.SAVE_FAILED).to_dict()

        return {"success": True, "message": f"标签 '{tag}' 不存在", "tags": item.tags}
