"""
Pydantic models for project-related operations.

仅保留核心模型 ProjectMetadata（项目元数据）和 ProjectInitialData（项目初始化）。
删除未使用的 ProjectCreate 和 ProjectResponse（已被 ApiResponse 替代）。
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ProjectMetadata(BaseModel):
    """
    项目元数据模型。

    作为项目中唯一的项目信息模型，贯穿存储层/缓存层/业务层。
    """

    id: str = Field(
        ...,
        description="Unique project identifier (UUID format)",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Project name (1-100 characters)"
    )
    path: Optional[str] = Field(
        default=None,
        description="File system path to the project"
    )
    summary: str = Field(
        default="",
        max_length=500,
        description="Brief project description (max 500 characters)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags associated with the project"
    )
    status: Literal["active", "archived"] = Field(
        default="active",
        description="Project status"
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 timestamp of project creation"
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of last update"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that project name contains only allowed characters."""
        import re
        pattern = re.compile(r"^[\w\u4e00-\u9fff-]+$")
        if not pattern.match(v):
            raise ValueError(
                "Project name must contain only letters, numbers, underscores, Chinese characters, and hyphens"
            )
        return v

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate that ID matches UUID format."""
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE
        )
        if not uuid_pattern.match(v):
            raise ValueError("Project ID must be a valid UUID")
        return v.lower()

    model_config = {"populate_by_name": True}


class ProjectInitialData(BaseModel):
    """
    项目初始化数据结构，用于注册新项目时生成初始数据。

    创建后通过 to_storage_dict() 转换为存储格式。
    """

    id: str = Field(
        ...,
        description="Unique project identifier (UUID format)"
    )
    name: str = Field(
        ...,
        description="Project name"
    )
    version: int = Field(
        default=1,
        alias="_version",
        description="Project data version"
    )
    versions: Dict[str, int] = Field(
        default_factory=lambda: {
            "project": 1,
            "tag_registry": 1,
        },
        alias="_versions",
        description="Version tracking for each data section"
    )
    info: ProjectMetadata = Field(
        ...,
        description="Project metadata"
    )
    tag_registry: Dict[str, Dict] = Field(
        default_factory=dict,
        description="Tag registry with tag metadata"
    )
    groups: Dict[str, List] = Field(
        default_factory=dict,
        description="Group items indexed by group name"
    )

    model_config = {"populate_by_name": True}

    def to_storage_dict(self) -> Dict:
        """Convert to dictionary format for storage."""
        result = {
            "id": self.id,
            "name": self.name,
            "_version": self.version,
            "_versions": self.versions,
            "info": self.info.model_dump(),
            "tag_registry": self.tag_registry,
        }
        for group_name, items in self.groups.items():
            result[group_name] = items
        return result

    @classmethod
    def create(
        cls,
        project_id: str,
        name: str,
        path: Optional[str] = None,
        summary: str = "",
        tags: Optional[List[str]] = None,
        group_configs: Optional[Dict[str, Dict]] = None,
        default_tags: Optional[List[str]] = None
    ) -> "ProjectInitialData":
        """Create project initial data with dynamic group initialization."""
        from datetime import datetime

        if group_configs is None:
            from business.core.groups import DEFAULT_GROUP_CONFIGS
            group_configs = DEFAULT_GROUP_CONFIGS

        groups = {group_name: [] for group_name in group_configs.keys()}

        # 初始化版本号（包含所有组）
        versions = {"project": 1, "tag_registry": 1}
        for group_name in group_configs.keys():
            versions[group_name] = 1

        tag_registry = {}
        if default_tags:
            for tag in default_tags:
                tag_registry[tag] = {
                    "summary": f"默认标签: {tag}",
                    "created_at": datetime.now().isoformat(),
                    "usage_count": 0,
                    "aliases": []
                }

        if tags:
            for tag in tags:
                if tag not in tag_registry:
                    tag_registry[tag] = {
                        "summary": f"项目标签: {tag}",
                        "created_at": datetime.now().isoformat(),
                        "usage_count": 0,
                        "aliases": []
                    }

        now = datetime.now().isoformat()
        info = ProjectMetadata(
            id=project_id,
            name=name,
            path=path,
            summary=summary,
            tags=tags or [],
            status="active",
            created_at=now,
            updated_at=now
        )

        return cls(
            id=project_id,
            name=name,
            info=info,
            tag_registry=tag_registry,
            groups=groups
        )
