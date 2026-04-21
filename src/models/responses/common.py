"""通用响应模型."""

from typing import Any, List

from pydantic import BaseModel, Field


class PagedData(BaseModel):
    """分页数据结构."""

    items: List[Any] = Field(
        default_factory=list,
        description="数据列表",
    )
    total: int = Field(
        default=0,
        ge=0,
        description="总数",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="当前页码",
    )
    size: int = Field(
        default=0,
        ge=0,
        description="每页条数",
    )
