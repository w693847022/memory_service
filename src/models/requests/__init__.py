"""REST API 请求模型."""

from .project import (
    ProjectRegisterRequest,
    ProjectRenameRequest,
)
from .group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupSettingsUpdateRequest,
    ItemCreateRequest,
    ItemUpdateRequest,
    ItemTagManageRequest,
)
from .tag import (
    TagRegisterRequest,
    TagUpdateRequest,
    TagDeleteRequest,
    TagMergeRequest,
)
from .stats import (
    StatsSummaryRequest,
    StatsCleanupRequest,
)

__all__ = [
    # Project requests
    "ProjectRegisterRequest",
    "ProjectRenameRequest",
    # Group requests
    "GroupCreateRequest",
    "GroupUpdateRequest",
    "GroupSettingsUpdateRequest",
    "ItemCreateRequest",
    "ItemUpdateRequest",
    "ItemTagManageRequest",
    # Tag requests
    "TagRegisterRequest",
    "TagUpdateRequest",
    "TagDeleteRequest",
    "TagMergeRequest",
    # Stats requests
    "StatsSummaryRequest",
    "StatsCleanupRequest",
]
