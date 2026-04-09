"""
Pydantic models for project-related operations.

These models define the structure and validation for projects and their metadata.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ProjectMetadata(BaseModel):
    """
    Complete project metadata model.

    Represents a project with all its metadata including ID, name, path,
    and other configuration details.
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
        """
        Validate that project name contains only allowed characters.

        Allowed: letters, numbers, underscores, Chinese characters, hyphens
        """
        import re
        # Allow letters, numbers, underscores, Chinese characters, and hyphens
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

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "ai_memory_mcp",
                "path": "/home/user/projects/ai_memory_mcp",
                "summary": "AI memory MCP server project",
                "tags": ["mcp", "memory", "python"],
                "status": "active",
                "created_at": "2026-04-09T10:00:00Z",
                "updated_at": "2026-04-09T10:00:00Z"
            }
        }


class ProjectCreate(BaseModel):
    """
    Model for creating a new project.

    Contains all required and optional fields for project creation.
    """

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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate that project name contains only allowed characters.

        Allowed: letters, numbers, underscores, Chinese characters, hyphens
        """
        import re
        pattern = re.compile(r"^[\w\u4e00-\u9fff-]+$")
        if not pattern.match(v):
            raise ValueError(
                "Project name must contain only letters, numbers, underscores, Chinese characters, and hyphens"
            )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "my_new_project",
                "path": "/home/user/projects/my_new_project",
                "summary": "A new project for testing",
                "tags": ["test", "experimental"]
            }
        }


class ProjectResponse(BaseModel):
    """
    Response model for project operations.

    Used as the standard response format for API endpoints returning project data.
    """

    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable message about the operation"
    )
    data: Optional[ProjectMetadata] = Field(
        default=None,
        description="Project metadata if successful"
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
                "message": "Project created successfully",
                "data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "my_new_project",
                    "path": "/home/user/projects/my_new_project",
                    "summary": "A new project for testing",
                    "tags": ["test", "experimental"],
                    "status": "active",
                    "created_at": "2026-04-09T10:00:00Z",
                    "updated_at": "2026-04-09T10:00:00Z"
                },
                "error": None
            }
        }
