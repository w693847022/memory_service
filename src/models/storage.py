"""
核心项目数据聚合模型 - ProjectData。

作为唯一的项目数据模型贯穿存储层/缓存层/业务层，
提供 from_storage()/to_storage() 序列化方法和 Item/Tag/Version CRUD 方法。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .item import Item
from .project import ProjectMetadata
from .tag import TagInfo

# 存储格式中的保留键（不属于分组的顶层键）
_STORAGE_RESERVED_KEYS = {
    "id", "name", "_version", "_versions", "info",
    "tag_registry", "_group_configs"
}


class ProjectData(BaseModel):
    """
    核心项目数据聚合模型。

    从存储层加载后以模型形式存在内存中，
    业务层直接操作模型，缓存层缓存模型实例。

    存储格式通过 from_storage()/to_storage() 双向转换保持兼容。
    """

    id: str = Field(description="项目 UUID")
    name: str = Field(description="项目名称")
    version: int = Field(default=1, description="项目数据版本（对应存储 _version）")
    versions: Dict[str, int] = Field(
        default_factory=dict,
        description="各组件版本号映射（动态支持自定义组）"
    )
    metadata: ProjectMetadata = Field(description="项目元数据")
    tag_registry: Dict[str, TagInfo] = Field(
        default_factory=dict,
        description="标签注册表（tag_name → TagInfo 模型）"
    )
    groups: Dict[str, List[Item]] = Field(
        default_factory=dict,
        description="各分组条目（group_name → List[Item]）"
    )
    group_configs: Optional[Any] = Field(
        default=None,
        description="分组配置（原始 dict，由 groups 模块管理）"
    )

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}

    # ==================== 序列化 ====================

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> "ProjectData":
        """从存储格式的 dict 反序列化为 ProjectData 模型。

        Args:
            data: 存储层加载的合并 dict

        Returns:
            ProjectData 模型实例
        """
        # 构建元数据
        info = data.get("info", {})
        metadata = ProjectMetadata(
            id=data.get("id") or info.get("id", ""),
            name=data.get("name") or info.get("name", ""),
            path=info.get("path"),
            summary=info.get("summary", ""),
            tags=info.get("tags", []),
            status=info.get("status", "active"),
            created_at=info.get("created_at", ""),
            updated_at=info.get("updated_at", "")
        )

        # 构建标签注册表
        tag_registry = {}
        for tag_name, tag_data in data.get("tag_registry", {}).items():
            if isinstance(tag_data, TagInfo):
                tag_registry[tag_name] = tag_data
            else:
                tag_registry[tag_name] = TagInfo(
                    name=tag_name,
                    summary=tag_data.get("summary", ""),
                    aliases=tag_data.get("aliases", []),
                    usage_count=tag_data.get("usage_count", 0)
                )

        # 构建各分组数据
        groups = {}
        for key, value in data.items():
            if key in _STORAGE_RESERVED_KEYS:
                continue
            if isinstance(value, list):
                items = []
                for item_dict in value:
                    if isinstance(item_dict, Item):
                        items.append(item_dict)
                    elif isinstance(item_dict, dict):
                        # 兼容 _v 和 version 字段
                        if "_v" in item_dict and "version" not in item_dict:
                            item_dict["version"] = item_dict["_v"]
                        try:
                            items.append(Item.model_validate(item_dict))
                        except Exception:
                            # 验证失败的条目保留为原始 dict 的情况跳过
                            pass
                if items:
                    groups[key] = items

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("_version", 1),
            versions=data.get("_versions", {}),
            metadata=metadata,
            tag_registry=tag_registry,
            groups=groups,
            group_configs=data.get("_group_configs")
        )

    def to_storage(self) -> Dict[str, Any]:
        """序列化为存储格式的 dict。

        Returns:
            存储层可用的合并 dict
        """
        result: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "_version": self.version,
            "_versions": dict(self.versions),
            "info": self.metadata.model_dump(),
            "tag_registry": {
                name: tag.model_dump()
                for name, tag in self.tag_registry.items()
            },
        }
        if self.group_configs is not None:
            result["_group_configs"] = self.group_configs

        # 展开各分组条目
        for group_name, items in self.groups.items():
            result[group_name] = [item.model_dump() for item in items]

        return result

    # ==================== Item CRUD ====================

    def get_items(self, group: str) -> List[Item]:
        """获取指定分组的所有条目。"""
        return self.groups.get(group, [])

    def get_item(self, group: str, item_id: str) -> Optional[Item]:
        """获取指定分组中的单个条目。"""
        for item in self.groups.get(group, []):
            if item.id == item_id:
                return item
        return None

    def get_item_index(self, group: str, item_id: str) -> Optional[int]:
        """获取条目在分组中的索引位置。"""
        for i, item in enumerate(self.groups.get(group, [])):
            if item.id == item_id:
                return i
        return None

    def add_item(self, group: str, item: Item) -> None:
        """添加条目到指定分组。"""
        if group not in self.groups:
            self.groups[group] = []
        self.groups[group].append(item)

    def remove_item(self, group: str, item_id: str) -> Optional[Item]:
        """从指定分组中移除条目。

        Returns:
            被移除的 Item，如果未找到则返回 None
        """
        items = self.groups.get(group, [])
        for i, item in enumerate(items):
            if item.id == item_id:
                return items.pop(i)
        return None

    # ==================== Tag CRUD ====================

    def register_tag(self, tag: TagInfo) -> None:
        """注册标签。"""
        self.tag_registry[tag.name] = tag

    def get_tag(self, tag_name: str) -> Optional[TagInfo]:
        """获取标签信息。"""
        return self.tag_registry.get(tag_name)

    def remove_tag(self, tag_name: str) -> Optional[TagInfo]:
        """移除标签。

        Returns:
            被移除的 TagInfo，如果未找到则返回 None
        """
        return self.tag_registry.pop(tag_name, None)

    # ==================== Version ====================

    def increment_version(self, field: str) -> int:
        """递增指定组件的版本号。"""
        current = self.versions.get(field, 1)
        new_value = current + 1
        self.versions[field] = new_value
        self.version += 1
        return new_value

    def get_version(self, field: str) -> int:
        """获取指定组件的版本号。"""
        return self.versions.get(field, 1)

    # ==================== 元数据操作 ====================

    def touch(self) -> None:
        """更新项目的 updated_at 时间戳。"""
        self.metadata.updated_at = datetime.now().isoformat()
