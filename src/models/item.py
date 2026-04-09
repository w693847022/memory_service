"""
Pydantic models for item-related operations.

These models define the structure and validation for items within project groups.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Item(BaseModel):
    """
    Complete item model with all fields.

    Represents a single item within a project group, such as a feature,
    fix, note, or standard.
    """

    id: str = Field(
        ...,
        description="Unique identifier in format {group}_{timestamp}_{sequence}",
        pattern=r"^[a-z]+_[0-9]{8}_[0-9]+$"
    )
    summary: str = Field(
        ...,
        description="Brief summary of the item (length validated by group config)"
    )
    content: str = Field(
        default="",
        description="Detailed content in Markdown format (length validated by group config)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags associated with this item",
        min_length=0
    )
    status: Optional[str] = Field(
        default=None,
        description="Current status of the item (e.g., pending, in_progress, completed)"
    )
    severity: Optional[str] = Field(
        default=None,
        description="Severity level for fixes (e.g., critical, high, medium, low)"
    )
    related: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Related items grouped by group name"
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 timestamp of item creation"
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of last update"
    )
    version: int = Field(
        ...,
        ge=1,
        description="Version number for optimistic locking (starts at 1)"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate that all tags match the required format."""
        if not v:
            return v
        import re
        pattern = re.compile(r"^[a-z0-9_-]+$")
        for tag in v:
            if not pattern.match(tag):
                raise ValueError(
                    f"Tag '{tag}' must contain only lowercase letters, numbers, underscores, and hyphens"
                )
        return v

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate that ID matches the expected format."""
        import re
        pattern = re.compile(r"^([a-z]+)_([0-9]{8})_([0-9]+)$")
        if not pattern.match(v):
            raise ValueError(
                f"ID must be in format {{group}}_YYYYMMDD_sequence (e.g., 'feat_20260409_1')"
            )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "feat_20260409_1",
                "summary": "Add user authentication",
                "content": "Implement OAuth2 authentication flow",
                "tags": ["feature", "auth", "security"],
                "status": "in_progress",
                "severity": None,
                "related": {"fixes": ["fix_20260409_2"]},
                "created_at": "2026-04-09T10:30:00Z",
                "updated_at": "2026-04-09T14:20:00Z",
                "version": 3
            }
        }


class ItemCreate(BaseModel):
    """
    Model for creating a new item.

    All required fields for item creation are included here.
    """

    summary: str = Field(
        ...,
        description="Brief summary of the item (length validated by group config)"
    )
    content: str = Field(
        default="",
        description="Detailed content in Markdown format (length validated by group config)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags associated with this item"
    )
    status: Optional[str] = Field(
        default=None,
        description="Current status of the item"
    )
    severity: Optional[str] = Field(
        default=None,
        description="Severity level for fixes"
    )
    related: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Related items grouped by group name"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate that all tags match the required format."""
        if not v:
            return v
        import re
        pattern = re.compile(r"^[a-z0-9_-]+$")
        for tag in v:
            if not pattern.match(tag):
                raise ValueError(
                    f"Tag '{tag}' must contain only lowercase letters, numbers, underscores, and hyphens"
                )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class ItemUpdate(BaseModel):
    """
    Model for updating an existing item.

    All fields are optional to allow partial updates.
    """

    summary: Optional[str] = Field(
        default=None,
        description="Brief summary of the item (length validated by group config)"
    )
    content: Optional[str] = Field(
        default=None,
        description="Detailed content in Markdown format (length validated by group config)"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags associated with this item"
    )
    status: Optional[str] = Field(
        default=None,
        description="Current status of the item"
    )
    severity: Optional[str] = Field(
        default=None,
        description="Severity level for fixes"
    )
    related: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Related items grouped by group name"
    )
    version: Optional[int] = Field(
        default=None,
        ge=1,
        description="Version number for optimistic locking"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all tags match the required format."""
        if v is None:
            return v
        if not v:
            return v
        import re
        pattern = re.compile(r"^[a-z0-9_-]+$")
        for tag in v:
            if not pattern.match(tag):
                raise ValueError(
                    f"Tag '{tag}' must contain only lowercase letters, numbers, underscores, and hyphens"
                )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class ItemResponse(BaseModel):
    """
    Response model for item operations.

    Used as the standard response format for API endpoints returning item data.
    """

    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable message about the operation"
    )
    data: Optional[Item] = Field(
        default=None,
        description="Item data if successful"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if unsuccessful"
    )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Item created successfully",
                "data": {
                    "id": "feat_20260409_1",
                    "summary": "Add user authentication",
                    "content": "Implement OAuth2 authentication flow",
                    "tags": ["feature", "auth"],
                    "status": "pending",
                    "severity": None,
                    "related": None,
                    "created_at": "2026-04-09T10:30:00Z",
                    "updated_at": "2026-04-09T10:30:00Z",
                    "version": 1
                },
                "error": None
            }
        }
