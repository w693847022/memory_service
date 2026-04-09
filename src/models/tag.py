"""
Pydantic models for tag-related operations.

These models define the structure and validation for tags and tag registries.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TagInfo(BaseModel):
    """
    Information about a registered tag.

    Contains metadata about a tag including its name, description,
    aliases, and usage statistics.
    """

    name: str = Field(
        ...,
        description="Tag name (lowercase, alphanumeric with underscores and hyphens)",
        pattern=r"^[a-z0-9_-]+$"
    )
    summary: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="Tag semantic summary (4-100 characters)"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names or aliases for this tag"
    )
    usage_count: int = Field(
        default=0,
        ge=0,
        description="Number of items using this tag"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate that tag name contains only lowercase letters, numbers, underscores, and hyphens.
        """
        import re
        pattern = re.compile(r"^[a-z0-9_-]+$")
        if not pattern.match(v):
            raise ValueError(
                "Tag name must contain only lowercase letters, numbers, underscores, and hyphens"
            )
        return v

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, v: List[str]) -> List[str]:
        """Validate that all aliases are non-empty strings."""
        for alias in v:
            if not alias or not alias.strip():
                raise ValueError("Tag aliases cannot be empty strings")
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "feature",
                "summary": "New functionality or enhancement",
                "aliases": ["feat", "enhancement", "new"],
                "usage_count": 42
            }
        }


class TagRegistry(BaseModel):
    """
    Registry of all tags in a project.

    Contains a mapping of tag names to their metadata.
    """

    tags: Dict[str, TagInfo] = Field(
        default_factory=dict,
        description="Dictionary mapping tag names to their information"
    )

    def get_tag(self, name: str) -> Optional[TagInfo]:
        """
        Retrieve tag information by name.

        Args:
            name: Tag name to look up

        Returns:
            TagInfo if found, None otherwise
        """
        return self.tags.get(name)

    def add_tag(self, tag_info: TagInfo) -> None:
        """
        Add or update a tag in the registry.

        Args:
            tag_info: Tag information to add or update
        """
        self.tags[tag_info.name] = tag_info

    def remove_tag(self, name: str) -> bool:
        """
        Remove a tag from the registry.

        Args:
            name: Tag name to remove

        Returns:
            True if tag was removed, False if it didn't exist
        """
        if name in self.tags:
            del self.tags[name]
            return True
        return False

    def list_tags(self) -> List[str]:
        """
        Get a list of all registered tag names.

        Returns:
            List of tag names
        """
        return list(self.tags.keys())

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "tags": {
                    "feature": {
                        "name": "feature",
                        "summary": "New functionality or enhancement",
                        "aliases": ["feat", "enhancement"],
                        "usage_count": 42
                    },
                    "bug": {
                        "name": "bug",
                        "summary": "Software defect or error",
                        "aliases": ["fix", "defect"],
                        "usage_count": 15
                    }
                }
            }
        }
