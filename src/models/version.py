"""版本控制模型

支持动态自定义组的版本追踪，不再硬编码内置组字段。
"""

from typing import Dict
from pydantic import BaseModel, Field


class ProjectVersions(BaseModel):
    """项目版本控制模型

    跟踪项目中各个组件的版本号，用于并发控制。
    使用动态字典支持内置组和自定义组。
    """

    versions: Dict[str, int] = Field(
        default_factory=lambda: {
            "project": 1,
            "tag_registry": 1,
        },
        description="各组件版本号映射（支持动态自定义组）"
    )

    def increment(self, field: str) -> int:
        """递增指定字段的版本号

        Args:
            field: 要递增的字段名（如 'project', 'tag_registry', 'features', 自定义组名等）

        Returns:
            int: 递增后的版本号
        """
        current = self.versions.get(field, 1)
        new_value = current + 1
        self.versions[field] = new_value
        return new_value

    def get_version(self, field: str) -> int:
        """获取指定字段的版本号

        Args:
            field: 字段名

        Returns:
            int: 版本号，如果字段不存在则返回 1
        """
        return self.versions.get(field, 1)

    def ensure_group(self, group_name: str) -> None:
        """确保指定组有版本号

        Args:
            group_name: 组名称
        """
        if group_name not in self.versions:
            self.versions[group_name] = 1

    def to_dict(self) -> dict:
        """转换为字典格式

        Returns:
            dict: 包含所有版本号的字典
        """
        return dict(self.versions)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "ProjectVersions":
        """从字典创建

        Args:
            data: 版本号字典

        Returns:
            ProjectVersions 实例
        """
        return cls(versions=dict(data) if data else {})
