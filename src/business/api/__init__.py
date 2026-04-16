"""Business API Routes - 路由模块."""

from .projects import router as projects_router, init_services as init_projects_services
from .tags import router as tags_router, init_services as init_tags_services
from .stats import router as stats_router, init_services as init_stats_services
from .groups import router as groups_router, init_services as init_groups_services

__all__ = [
    "projects_router", "init_projects_services",
    "tags_router", "init_tags_services",
    "stats_router", "init_stats_services",
    "groups_router", "init_groups_services",
]
