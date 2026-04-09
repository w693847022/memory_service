"""
Unit tests for Pydantic models.

This module tests validation rules, serialization, and error handling
for all Pydantic models used in the ai_memory_mcp application.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from src.models.item import Item, ItemCreate, ItemUpdate, ItemResponse
from src.models.project import ProjectMetadata, ProjectCreate, ProjectResponse
from src.models.tag import TagInfo, TagRegistry
from src.models.response import ApiResponse


class TestItemModel:
    """Test cases for Item model validation."""

    def test_valid_item(self):
        """Test creating a valid item with all fields."""
        item = Item(
            id="feat_20260409_1",
            summary="Add user authentication",
            content="Implement OAuth2 authentication flow",
            tags=["feature", "auth", "security"],
            status="in_progress",
            severity=None,
            related={"fixes": ["fix_20260409_2"]},
            created_at="2026-04-09T10:30:00Z",
            updated_at="2026-04-09T14:20:00Z",
            version=3
        )
        assert item.id == "feat_20260409_1"
        assert item.summary == "Add user authentication"
        assert item.tags == ["feature", "auth", "security"]
        assert item.status == "in_progress"
        assert item.version == 3

    def test_invalid_tag_format(self):
        """Test that invalid tag format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Item(
                id="feat_20260409_1",
                summary="Test feature",
                content="Test content",
                tags=["valid-tag", "InvalidTag", "another_valid"],
                created_at="2026-04-09T10:30:00Z",
                updated_at="2026-04-09T10:30:00Z",
                version=1
            )
        assert "tag" in str(exc_info.value).lower()

    def test_item_to_dict(self):
        """Test item serialization to dictionary."""
        item = Item(
            id="feat_20260409_1",
            summary="Test feature",
            content="Test content",
            tags=["feature"],
            created_at="2026-04-09T10:30:00Z",
            updated_at="2026-04-09T10:30:00Z",
            version=1
        )
        item_dict = item.model_dump()
        assert item_dict["id"] == "feat_20260409_1"
        assert item_dict["summary"] == "Test feature"
        assert item_dict["tags"] == ["feature"]

    def test_item_with_empty_tags(self):
        """Test that item with empty tags list is valid."""
        item = Item(
            id="feat_20260409_1",
            summary="Test feature",
            content="Test content",
            tags=[],
            created_at="2026-04-09T10:30:00Z",
            updated_at="2026-04-09T10:30:00Z",
            version=1
        )
        assert item.tags == []

    def test_item_with_tag_containing_spaces(self):
        """Test that tag with spaces raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Item(
                id="feat_20260409_1",
                summary="Test feature",
                content="Test content",
                tags=["invalid tag"],
                created_at="2026-04-09T10:30:00Z",
                updated_at="2026-04-09T10:30:00Z",
                version=1
            )
        assert "tag" in str(exc_info.value).lower()

    def test_item_with_tag_containing_special_chars(self):
        """Test that tag with special characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Item(
                id="feat_20260409_1",
                summary="Test feature",
                content="Test content",
                tags=["tag@123"],
                created_at="2026-04-09T10:30:00Z",
                updated_at="2026-04-09T10:30:00Z",
                version=1
            )
        assert "tag" in str(exc_info.value).lower()

    def test_item_with_invalid_id_format(self):
        """Test that invalid ID format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Item(
                id="invalid_id_format",
                summary="Test feature",
                content="Test content",
                tags=[],
                created_at="2026-04-09T10:30:00Z",
                updated_at="2026-04-09T10:30:00Z",
                version=1
            )
        assert "id" in str(exc_info.value).lower()

    def test_item_with_version_zero(self):
        """Test that version less than 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Item(
                id="feat_20260409_1",
                summary="Test feature",
                content="Test content",
                tags=[],
                created_at="2026-04-09T10:30:00Z",
                updated_at="2026-04-09T10:30:00Z",
                version=0
            )
        assert "version" in str(exc_info.value).lower()


class TestProjectMetadata:
    """Test cases for ProjectMetadata model validation."""

    def test_valid_project(self):
        """Test creating a valid project with all fields."""
        project = ProjectMetadata(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="ai_memory_mcp",
            path="/home/user/projects/ai_memory_mcp",
            summary="AI memory MCP server project",
            tags=["mcp", "memory", "python"],
            status="active",
            created_at="2026-04-09T10:00:00Z",
            updated_at="2026-04-09T10:00:00Z"
        )
        assert project.id == "550e8400-e29b-41d4-a716-446655440000"
        assert project.name == "ai_memory_mcp"
        assert project.status == "active"

    def test_invalid_project_name(self):
        """Test that invalid project name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="project@invalid",  # Invalid character @
                path="/path/to/project",
                created_at="2026-04-09T10:00:00Z",
                updated_at="2026-04-09T10:00:00Z"
            )
        assert "name" in str(exc_info.value).lower()

    def test_invalid_uuid(self):
        """Test that invalid UUID format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                id="not-a-valid-uuid",
                name="test_project",
                path="/path/to/project",
                created_at="2026-04-09T10:00:00Z",
                updated_at="2026-04-09T10:00:00Z"
            )
        assert "id" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()

    def test_project_with_chinese_characters(self):
        """Test that project name with Chinese characters is valid."""
        project = ProjectMetadata(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="项目名称",
            path="/path/to/project",
            created_at="2026-04-09T10:00:00Z",
            updated_at="2026-04-09T10:00:00Z"
        )
        assert project.name == "项目名称"

    def test_project_with_underscores_and_hyphens(self):
        """Test that project name with underscores and hyphens is valid."""
        project = ProjectMetadata(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="my-test_project",
            path="/path/to/project",
            created_at="2026-04-09T10:00:00Z",
            updated_at="2026-04-09T10:00:00Z"
        )
        assert project.name == "my-test_project"

    def test_project_name_too_long(self):
        """Test that project name exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="a" * 101,  # Max is 100
                path="/path/to/project",
                created_at="2026-04-09T10:00:00Z",
                updated_at="2026-04-09T10:00:00Z"
            )
        assert "name" in str(exc_info.value).lower()

    def test_project_summary_too_long(self):
        """Test that project summary exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="test_project",
                path="/path/to/project",
                summary="a" * 501,  # Max is 500
                created_at="2026-04-09T10:00:00Z",
                updated_at="2026-04-09T10:00:00Z"
            )
        assert "summary" in str(exc_info.value).lower()

    def test_project_with_invalid_status(self):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="test_project",
                path="/path/to/project",
                status="invalid_status",
                created_at="2026-04-09T10:00:00Z",
                updated_at="2026-04-09T10:00:00Z"
            )
        assert "status" in str(exc_info.value).lower()


class TestTagInfo:
    """Test cases for TagInfo model validation."""

    def test_valid_tag(self):
        """Test creating a valid tag with all fields."""
        tag = TagInfo(
            name="feature",
            summary="New functionality or enhancement",
            aliases=["feat", "enhancement", "new"],
            usage_count=42
        )
        assert tag.name == "feature"
        assert tag.summary == "New functionality or enhancement"
        assert tag.aliases == ["feat", "enhancement", "new"]
        assert tag.usage_count == 42

    def test_invalid_tag_name(self):
        """Test that invalid tag name with uppercase raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="InvalidTag",
                summary="Test summary for validation"
            )
        assert "name" in str(exc_info.value).lower()

    def test_summary_too_short(self):
        """Test that summary shorter than min length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="feature",
                summary="短"  # Min is 4
            )
        assert "summary" in str(exc_info.value).lower()

    def test_summary_too_long(self):
        """Test that summary exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="feature",
                summary="a" * 101  # Max is 100
            )
        assert "summary" in str(exc_info.value).lower()

    def test_tag_with_special_characters(self):
        """Test that tag name with special characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="tag@123",
                summary="Test summary for validation"
            )
        assert "name" in str(exc_info.value).lower()

    def test_tag_with_valid_underscores_and_hyphens(self):
        """Test that tag name with underscores and hyphens is valid."""
        tag = TagInfo(
            name="test_tag-123",
            summary="Test summary for validation"
        )
        assert tag.name == "test_tag-123"

    def test_tag_with_empty_alias(self):
        """Test that empty alias string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="feature",
                summary="Test summary for validation",
                aliases=["valid", ""]
            )
        assert "aliases" in str(exc_info.value).lower() or "alias" in str(exc_info.value).lower()

    def test_tag_with_negative_usage_count(self):
        """Test that negative usage count raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TagInfo(
                name="feature",
                summary="Test summary for validation",
                usage_count=-1
            )
        assert "usage_count" in str(exc_info.value).lower()

    def test_tag_minimal_required_fields(self):
        """Test creating tag with only required fields."""
        tag = TagInfo(
            name="bug",
            summary="Software defect or error"
        )
        assert tag.name == "bug"
        assert tag.summary == "Software defect or error"
        assert tag.aliases == []
        assert tag.usage_count == 0


class TestApiResponse:
    """Test cases for ApiResponse model validation."""

    def test_success_response(self):
        """Test creating a successful response with data."""
        response = ApiResponse(
            success=True,
            data={"id": "123", "name": "example"},
            message="Operation completed successfully"
        )
        assert response.success is True
        assert response.data == {"id": "123", "name": "example"}
        assert response.message == "Operation completed successfully"
        assert response.error is None

    def test_error_response(self):
        """Test creating an error response."""
        response = ApiResponse(
            success=False,
            error="Resource not found",
            data=None
        )
        assert response.success is False
        assert response.error == "Resource not found"
        assert response.data is None
        assert response.message is None

    def test_response_to_dict(self):
        """Test response serialization to dictionary."""
        response = ApiResponse(
            success=True,
            data={"key": "value"},
            message="Success"
        )
        response_dict = response.to_dict()
        assert response_dict["success"] is True
        assert response_dict["data"] == {"key": "value"}
        assert response_dict["message"] == "Success"

    def test_success_response_factory(self):
        """Test success_response factory method."""
        response = ApiResponse.success_response(
            data={"result": "success"},
            message="Data created"
        )
        assert response.success is True
        assert response.data == {"result": "success"}
        assert response.message == "Data created"

    def test_error_response_factory(self):
        """Test error_response factory method."""
        response = ApiResponse.error_response(
            error="Validation failed",
            data={"field": "email"}
        )
        assert response.success is False
        assert response.error == "Validation failed"
        assert response.data == {"field": "email"}

    def test_response_with_none_data(self):
        """Test response with None data is valid."""
        response = ApiResponse(
            success=True,
            message="Operation completed"
        )
        assert response.success is True
        assert response.data is None
        assert response.message == "Operation completed"

    def test_response_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        response = ApiResponse(
            success=True,
            data={"key": "value"},
            error=None,
            message=None
        )
        response_dict = response.to_dict()
        assert "data" in response_dict
        assert "error" not in response_dict
        assert "message" not in response_dict

    def test_generic_response_with_different_types(self):
        """Test ApiResponse with different data types."""
        # Test with string data
        response_str = ApiResponse(success=True, data="simple string")
        assert response_str.data == "simple string"

        # Test with list data
        response_list = ApiResponse(success=True, data=[1, 2, 3])
        assert response_list.data == [1, 2, 3]

        # Test with dict data
        response_dict = ApiResponse(success=True, data={"key": "value"})
        assert response_dict.data == {"key": "value"}


class TestItemCreate:
    """Test cases for ItemCreate model validation."""

    def test_valid_item_create(self):
        """Test creating a valid ItemCreate instance."""
        item_create = ItemCreate(
            summary="New feature",
            content="Feature description",
            tags=["feature", "new"]
        )
        assert item_create.summary == "New feature"
        assert item_create.tags == ["feature", "new"]

    def test_item_create_with_defaults(self):
        """Test ItemCreate with default values."""
        item_create = ItemCreate(summary="New feature")
        assert item_create.content == ""
        assert item_create.tags == []
        assert item_create.status is None
        assert item_create.severity is None


class TestItemUpdate:
    """Test cases for ItemUpdate model validation."""

    def test_valid_item_update(self):
        """Test creating a valid ItemUpdate instance."""
        item_update = ItemUpdate(
            summary="Updated summary",
            status="completed"
        )
        assert item_update.summary == "Updated summary"
        assert item_update.status == "completed"
        assert item_update.content is None

    def test_item_update_all_none(self):
        """Test ItemUpdate with all None values."""
        item_update = ItemUpdate()
        assert item_update.summary is None
        assert item_update.content is None
        assert item_update.tags is None
        assert item_update.status is None

    def test_item_update_with_version(self):
        """Test ItemUpdate with version for optimistic locking."""
        item_update = ItemUpdate(
            summary="Updated summary",
            version=5
        )
        assert item_update.version == 5


class TestProjectCreate:
    """Test cases for ProjectCreate model validation."""

    def test_valid_project_create(self):
        """Test creating a valid ProjectCreate instance."""
        project_create = ProjectCreate(
            name="new_project",
            path="/path/to/project",
            summary="A new project",
            tags=["new", "test"]
        )
        assert project_create.name == "new_project"
        assert project_create.tags == ["new", "test"]

    def test_project_create_with_defaults(self):
        """Test ProjectCreate with default values."""
        project_create = ProjectCreate(name="new_project")
        assert project_create.path is None
        assert project_create.summary == ""
        assert project_create.tags == []


class TestTagRegistry:
    """Test cases for TagRegistry model functionality."""

    def test_tag_registry_operations(self):
        """Test adding, retrieving, and removing tags."""
        registry = TagRegistry()

        # Add tag
        tag_info = TagInfo(
            name="feature",
            summary="New functionality"
        )
        registry.add_tag(tag_info)

        # Get tag
        retrieved = registry.get_tag("feature")
        assert retrieved is not None
        assert retrieved.name == "feature"

        # List tags
        tags = registry.list_tags()
        assert "feature" in tags

        # Remove tag
        removed = registry.remove_tag("feature")
        assert removed is True

        # Verify removal
        retrieved = registry.get_tag("feature")
        assert retrieved is None

    def test_tag_registry_update_existing(self):
        """Test updating an existing tag."""
        registry = TagRegistry()

        tag_info1 = TagInfo(
            name="feature",
            summary="Original summary"
        )
        registry.add_tag(tag_info1)

        tag_info2 = TagInfo(
            name="feature",
            summary="Updated summary",
            usage_count=10
        )
        registry.add_tag(tag_info2)

        retrieved = registry.get_tag("feature")
        assert retrieved.summary == "Updated summary"
        assert retrieved.usage_count == 10

    def test_tag_registry_remove_nonexistent(self):
        """Test removing a non-existent tag returns False."""
        registry = TagRegistry()
        removed = registry.remove_tag("nonexistent")
        assert removed is False

    def test_tag_registry_empty(self):
        """Test operations on empty registry."""
        registry = TagRegistry()

        assert registry.get_tag("nonexistent") is None
        assert registry.list_tags() == []
