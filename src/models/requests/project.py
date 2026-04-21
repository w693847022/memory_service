"""项目管理请求模型."""

from typing import Optional

from pydantic import BaseModel, Field


class ProjectRegisterRequest(BaseModel):
    """注册新项目请求."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="项目名称",
    )
    path: str = Field(
        default="",
        description="项目路径",
    )
    summary: str = Field(
        default="",
        description="项目摘要",
    )
    tags: str = Field(
        default="",
        description="项目标签（逗号分隔）",
    )


class ProjectRenameRequest(BaseModel):
    """重命名项目请求."""

    new_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="新项目名称",
    )
