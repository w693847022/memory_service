"""Groups Service Module - 组配置管理业务逻辑服务.

提供组配置的读取、验证、创建、更新、删除等业务逻辑。
所有涉及 IO 的方法均为 async，使用 barrier_manager 进行并发控制。
"""

import json
from typing import Optional, List, Dict, Any, Tuple, Union

from src.models.group import (
    UnifiedGroupConfig,
    RESERVED_FIELDS,
)
from src.models.enums import GroupType
from business.core.barrier_decorator import barrier
from business.core.barrier_constants import OperationLevel
from src.common.consts import ErrorMessages
from src.models.response import ResponseBuilder


class GroupsService:
    """组配置管理业务逻辑服务类."""

    def __init__(self, storage):
        self.storage = storage

    # ==================== 同步验证方法（静态，无IO）====================

    @staticmethod
    def is_reserved_field(field_name: str) -> bool:
        """检测字段名是否为系统保留字段."""
        return field_name in RESERVED_FIELDS

    @staticmethod
    def validate_group_name(
        group_name: str,
        all_configs: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """验证组名是否合法.

        Args:
            group_name: 组名称
            all_configs: 所有组配置（从存储加载）

        Returns:
            (是否有效, 错误信息)
        """
        if group_name in RESERVED_FIELDS:
            return False, f"组名 '{group_name}' 与系统配置字段冲突"

        if group_name in all_configs:
            return True, None

        valid_groups = ", ".join(sorted(all_configs.keys()))
        return False, f"无效的分组类型: {group_name} (支持: {valid_groups})"

    @staticmethod
    def validate_status(
        status: str,
        config: Optional[UnifiedGroupConfig] = None,
    ) -> Tuple[bool, Optional[str]]:
        """验证状态值是否合法."""
        if config is None:
            config = UnifiedGroupConfig()

        if not config.enable_status:
            return True, None

        status_values = config.status_values if config.status_values else ["pending", "in_progress", "completed"]
        if status in status_values:
            return True, None
        valid_values = ", ".join(status_values)
        return False, f"无效的 status 值: {status} (有效值: {valid_values})"

    @staticmethod
    def validate_severity(
        severity: str,
        config: Optional[UnifiedGroupConfig] = None,
    ) -> Tuple[bool, Optional[str]]:
        """验证严重程度值是否合法."""
        if config is None:
            config = UnifiedGroupConfig(enable_severity=True)

        if not config.enable_severity:
            return True, None

        severity_values = config.severity_values if config.severity_values else ["critical", "high", "medium", "low"]
        if severity in severity_values:
            return True, None
        return False, f"无效的 severity 值: {severity} (有效值: {', '.join(severity_values)})"

    @staticmethod
    def validate_content_length(
        content: str,
        config: Optional[UnifiedGroupConfig] = None,
        min_bytes: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """验证内容长度（字节验证）."""
        content_bytes = len(content.encode('utf-8'))
        effective_min_bytes = min_bytes or 1

        if config is not None:
            max_bytes = config.content_max_bytes
            if content_bytes < effective_min_bytes:
                return False, f"内容过短：至少需要 {effective_min_bytes} 字节", content_bytes
            if content_bytes > max_bytes:
                return False, f"内容过长：{content_bytes} 字节，最大允许 {max_bytes} 字节", content_bytes
            return True, None, content_bytes

        return True, None, content_bytes

    @staticmethod
    def validate_summary_length(
        summary: str,
        config: Optional[UnifiedGroupConfig] = None,
        min_bytes: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """验证摘要长度（字节验证）."""
        summary_bytes = len(summary.encode('utf-8'))
        effective_min_bytes = min_bytes or 1

        if config is not None:
            max_bytes = config.summary_max_bytes
            if summary_bytes < effective_min_bytes:
                return False, f"摘要过短：至少需要 {effective_min_bytes} 字节", summary_bytes
            if summary_bytes > max_bytes:
                return False, f"摘要过长：{summary_bytes} 字节，最大允许 {max_bytes} 字节", summary_bytes
            return True, None, summary_bytes

        return True, None, summary_bytes

    @staticmethod
    def validate_related(
        related: Optional[Union[str, Dict[str, List[str]]]],
        group_name: str,
        config: Optional[UnifiedGroupConfig] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, List[str]]]]:
        """解析并验证 related 参数."""
        if related is None or related == "":
            return True, "", None

        if config is None:
            return True, "", None

        if not config.allow_related:
            return False, f"分组 '{group_name}' 不支持关联功能", None

        allowed_related_to = config.allowed_related_to
        if not allowed_related_to:
            return True, "", None

        if isinstance(related, dict):
            related_dict = related
        else:
            try:
                related_dict = json.loads(related)
            except json.JSONDecodeError:
                return False, "related 参数 JSON 格式无效", None

        for rel_group in related_dict.keys():
            if rel_group not in allowed_related_to:
                return False, f"分组 '{group_name}' 只能关联 {', '.join(allowed_related_to)}，不能关联 '{rel_group}'", None

        return True, "", related_dict

    @staticmethod
    def validate_tags_count(
        tag_list: List[str],
        config: Optional[UnifiedGroupConfig] = None,
    ) -> Tuple[bool, Optional[str]]:
        """验证标签数量是否超过配置限制.

        Args:
            tag_list: 标签列表
            config: 组配置对象

        Returns:
            (is_valid, error_message) 二元组
        """
        if not tag_list:
            return True, None

        if config is None:
            config = UnifiedGroupConfig()

        count = len(tag_list)
        max_allowed = config.max_tags

        if count > max_allowed:
            return False, f"标签数量超限：当前 {count} 个，最大允许 {max_allowed} 个"

        return True, None

    # ==================== 异步配置读取 ====================

    async def get_all_configs(self, project_id: str) -> Dict[str, UnifiedGroupConfig]:
        """从 _groups.json 加载全部组配置（内置+自定义合并后）.

        Returns:
            Dict[str, UnifiedGroupConfig] 组名到配置的映射
        """
        group_configs = await self.storage.get_group_configs(project_id)
        return group_configs.get("groups", {})

    async def get_group_config(self, project_id: str, group_name: str) -> Optional[UnifiedGroupConfig]:
        """获取单个组配置."""
        all_configs = await self.get_all_configs(project_id)
        return all_configs.get(group_name)

    async def get_all_group_names(self, project_id: str) -> List[str]:
        """获取所有组名称."""
        all_configs = await self.get_all_configs(project_id)
        return list(all_configs.keys())

    # ==================== 异步配置写入 ====================

    @barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
    async def create_custom_group(
        self,
        project_id: str,
        group_name: str,
        content_max_bytes: int = 240,
        summary_max_bytes: int = 90,
        allow_related: bool = False,
        allowed_related_to: Optional[List[str]] = None,
        enable_status: bool = True,
        enable_severity: bool = False,
        max_tags: int = 2,
        description: str = "",
    ) -> Dict[str, Any]:
        """创建自定义组."""
        group_configs = await self.storage.get_group_configs(project_id)
        groups = group_configs.get("groups", {})

        if group_name in groups:
            return ResponseBuilder.error(f"自定义组 '{group_name}' 已存在").to_dict()

        new_group = UnifiedGroupConfig(
            content_max_bytes=content_max_bytes,
            summary_max_bytes=summary_max_bytes,
            allow_related=allow_related,
            allowed_related_to=allowed_related_to or [],
            enable_status=enable_status,
            enable_severity=enable_severity,
            max_tags=max_tags,
            description=description,
        )

        groups[group_name] = new_group
        group_configs["groups"] = groups

        if await self.storage.save_group_configs(project_id, group_configs):
            return ResponseBuilder.success(message=f"自定义组 '{group_name}' 创建成功").to_dict()
        return ResponseBuilder.error("保存配置失败").to_dict()

    @barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
    async def update_group_config(
        self,
        project_id: str,
        group: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新组配置（支持部分更新，只更新传入的字段，未传入的字段保持原值）."""
        group_configs = await self.storage.get_group_configs(project_id)
        groups = group_configs.get("groups", {})

        is_valid, error_msg = self.validate_group_name(group, groups)
        if not is_valid:
            return ResponseBuilder.error(error_msg or "无效的组名").to_dict()

        # 获取现有配置
        existing_config = groups.get(group)
        if existing_config is None:
            return ResponseBuilder.error(f"组 '{group}' 不存在").to_dict()

        # 将现有配置转换为字典
        if isinstance(existing_config, UnifiedGroupConfig):
            existing_dict = existing_config.to_dict()
        else:
            existing_dict = dict(existing_config)

        # 合并配置：新配置覆盖现有配置的对应字段
        merged_dict = {**existing_dict, **config}

        try:
            unified_config = UnifiedGroupConfig.from_dict(merged_dict)
        except Exception as e:
            return ResponseBuilder.error(f"配置格式错误: {e}").to_dict()

        groups[group] = unified_config
        group_configs["groups"] = groups

        if await self.storage.save_group_configs(project_id, group_configs):
            return ResponseBuilder.success(message=f"组 '{group}' 配置已更新").to_dict()
        return ResponseBuilder.error(ErrorMessages.SAVE_CONFIG_FAILED).to_dict()

    @barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
    async def delete_custom_group(self, project_id: str, group_name: str) -> Dict[str, Any]:
        """删除自定义组."""
        group_configs = await self.storage.get_group_configs(project_id)
        groups = group_configs.get("groups", {})

        if group_name not in groups:
            return ResponseBuilder.error(f"自定义组 '{group_name}' 不存在").to_dict()

        # 不能删除内置组
        config = groups[group_name]
        is_builtin = config.is_builtin if isinstance(config, UnifiedGroupConfig) else config.get("is_builtin", False)
        if is_builtin:
            return ResponseBuilder.error(f"内置组 '{group_name}' 不允许删除").to_dict()

        del groups[group_name]
        group_configs["groups"] = groups

        if await self.storage.save_group_configs(project_id, group_configs):
            return ResponseBuilder.success(message=f"自定义组 '{group_name}' 已删除，组内历史记录条目已保留").to_dict()
        return ResponseBuilder.error("保存配置失败").to_dict()

    @barrier(level=OperationLevel.L3, files=["_groups.json"], key="{project_id}")
    async def update_group_settings(
        self,
        project_id: str,
        default_related_rules: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """更新组全局设置."""
        group_configs = await self.storage.get_group_configs(project_id)

        if default_related_rules is not None:
            if "group_settings" not in group_configs:
                group_configs["group_settings"] = {}
            group_configs["group_settings"]["default_related_rules"] = default_related_rules

        if await self.storage.save_group_configs(project_id, group_configs):
            return ResponseBuilder.success(message="组设置更新成功").to_dict()
        return ResponseBuilder.error("保存配置失败").to_dict()

    # ==================== 异步查询 ====================

    async def list_groups(self, project_id: str) -> Dict[str, Any]:
        """返回所有组完整配置+条目计数."""
        from src.models.storage import ProjectData

        project_data: Optional[ProjectData] = await self.storage.get_project_data(project_id)
        if project_data is None:
            return ResponseBuilder.error(
                ErrorMessages.PROJECT_NOT_FOUND.format(project_id=project_id)
            ).to_dict()

        group_configs = await self.storage.get_group_configs(project_id)
        all_configs: Dict[str, UnifiedGroupConfig] = group_configs.get("groups", {})

        builtin_names = GroupType.values()
        groups = []

        for group_name in builtin_names:
            items = project_data.get_items(group_name)
            config = all_configs.get(group_name, UnifiedGroupConfig())
            groups.append({
                "name": group_name,
                "count": len(items),
                "is_builtin": True,
                **config.to_dict()
            })

        for group_name, config in all_configs.items():
            if group_name not in builtin_names:
                items = project_data.get_items(group_name)
                groups.append({
                    "name": group_name,
                    "count": len(items),
                    "is_builtin": False,
                    **(config.to_dict() if isinstance(config, UnifiedGroupConfig) else config)
                })

        return {
            "success": True,
            "groups": groups,
            "settings": group_configs.get("group_settings", {})
        }

    async def get_group_config_for_api(self, project_id: str, group: str) -> Dict[str, Any]:
        """获取单个组配置（API格式）."""
        group_configs = await self.storage.get_group_configs(project_id)
        all_configs: Dict[str, UnifiedGroupConfig] = group_configs.get("groups", {})

        if group in all_configs:
            config = all_configs[group]
            return {"success": True, "config": config.to_dict() if isinstance(config, UnifiedGroupConfig) else config}
        return {"success": False, "error": f"组 '{group}' 不存在"}
