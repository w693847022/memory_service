"""
Pydantic models for storage-related operations.

These models define the structure and validation for project data storage
and group indexing.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from .item import Item


class GroupIndex(BaseModel):
    """
    Index of items within a group.

    Maintains a list of item IDs belonging to a specific group.
    """

    items: List[str] = Field(
        default_factory=list,
        description="List of item IDs in this group"
    )

    def add_item(self, item_id: str) -> None:
        """
        Add an item ID to the index.

        Args:
            item_id: Item ID to add
        """
        if item_id not in self.items:
            self.items.append(item_id)

    def remove_item(self, item_id: str) -> bool:
        """
        Remove an item ID from the index.

        Args:
            item_id: Item ID to remove

        Returns:
            True if item was removed, False if it wasn't in the index
        """
        try:
            self.items.remove(item_id)
            return True
        except ValueError:
            return False

    def has_item(self, item_id: str) -> bool:
        """
        Check if an item ID exists in the index.

        Args:
            item_id: Item ID to check

        Returns:
            True if item exists in index, False otherwise
        """
        return item_id in self.items

    @field_validator("items")
    @classmethod
    def validate_item_ids(cls, v: List[str]) -> List[str]:
        """Validate that all item IDs follow the correct format."""
        import re
        pattern = re.compile(r"^[a-z]+_[0-9]{8}_[0-9]+$")
        for item_id in v:
            if not pattern.match(item_id):
                raise ValueError(
                    f"Invalid item ID format: '{item_id}'. "
                    "Expected format: {{group}}_YYYYMMDD_sequence"
                )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "items": [
                    "feat_20260409_1",
                    "feat_20260409_2",
                    "feat_20260408_5"
                ]
            }
        }


class ProjectData(BaseModel):
    """
    Complete project data storage model.

    Aggregates all project data including metadata, groups, tags,
    and configuration.
    """

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project metadata (id, name, path, summary, etc.)"
    )
    groups: Dict[str, GroupIndex] = Field(
        default_factory=dict,
        description="Group indexes mapping group names to item ID lists"
    )
    items: Dict[str, Item] = Field(
        default_factory=dict,
        description="All items indexed by their ID"
    )
    tags: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Tag registry with tag metadata"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project-specific configuration"
    )

    def get_group_items(self, group_name: str) -> List[str]:
        """
        Get all item IDs for a specific group.

        Args:
            group_name: Name of the group

        Returns:
            List of item IDs in the group, or empty list if group doesn't exist
        """
        if group_name in self.groups:
            return self.groups[group_name].items
        return []

    def get_item(self, item_id: str) -> Optional[Item]:
        """
        Retrieve an item by its ID.

        Args:
            item_id: Item ID to retrieve

        Returns:
            Item if found, None otherwise
        """
        return self.items.get(item_id)

    def add_item(self, item: Item, group_name: str) -> None:
        """
        Add an item to the project data.

        Args:
            item: Item to add
            group_name: Name of the group to add the item to
        """
        # Add to items dictionary
        self.items[item.id] = item

        # Add to group index
        if group_name not in self.groups:
            self.groups[group_name] = GroupIndex()
        self.groups[group_name].add_item(item.id)

    def remove_item(self, item_id: str, group_name: str) -> bool:
        """
        Remove an item from the project data.

        Args:
            item_id: Item ID to remove
            group_name: Name of the group containing the item

        Returns:
            True if item was removed, False if it wasn't found
        """
        # Remove from items dictionary
        if item_id in self.items:
            del self.items[item_id]

        # Remove from group index
        if group_name in self.groups:
            return self.groups[group_name].remove_item(item_id)

        return False

    @field_validator("groups")
    @classmethod
    def validate_groups(cls, v: Dict[str, GroupIndex]) -> Dict[str, GroupIndex]:
        """Validate that group names are valid."""
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for group_name in v.keys():
            if not pattern.match(group_name):
                raise ValueError(
                    f"Invalid group name: '{group_name}'. "
                    "Group names must start with a lowercase letter and contain only lowercase letters, numbers, and underscores"
                )
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "metadata": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "ai_memory_mcp",
                    "path": "/home/user/projects/ai_memory_mcp",
                    "summary": "AI memory MCP server project",
                    "status": "active"
                },
                "groups": {
                    "features": {
                        "items": ["feat_20260409_1", "feat_20260409_2"]
                    },
                    "fixes": {
                        "items": ["fix_20260409_1"]
                    }
                },
                "items": {
                    "feat_20260409_1": {
                        "id": "feat_20260409_1",
                        "summary": "Add user authentication",
                        "content": "Implement OAuth2 authentication flow",
                        "tags": ["feature", "auth"],
                        "status": "in_progress",
                        "severity": None,
                        "related": None,
                        "created_at": "2026-04-09T10:30:00Z",
                        "updated_at": "2026-04-09T14:20:00Z",
                        "version": 3
                    }
                },
                "tags": {
                    "feature": {
                        "name": "feature",
                        "summary": "New functionality or enhancement",
                        "aliases": ["feat", "enhancement"],
                        "usage_count": 42
                    }
                },
                "config": {
                    "enable_versioning": True,
                    "max_items_per_group": 1000
                }
            }
        }
