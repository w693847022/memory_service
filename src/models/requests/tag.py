"""标签管理请求模型."""

from typing import Optional

from pydantic import BaseModel, Field


class TagRegisterRequest(BaseModel):
    """注册项目标签请求."""

    project_id: str = Field(
        ...,
        description="项目 ID",
    )
    tag_name: str = Field(
        ...,
        description="标签名称",
    )
    summary: str = Field(
        ...,
        description="标签语义摘要",
    )
    aliases: str = Field(
        default="",
        description="别名（逗号分隔）",
    )


class TagUpdateRequest(BaseModel):
    """更新标签请求."""

    project_id: str = Field(
        ...,
        description="项目 ID",
    )
    tag_name: str = Field(
        ...,
        description="标签名称",
    )
    summary: str = Field(
        ...,
        description="新摘要",
    )


class TagDeleteRequest(BaseModel):
    """删除标签请求."""

    project_id: str = Field(
        ...,
        description="项目 ID",
    )
    tag_name: str = Field(
        ...,
        description="标签名称",
    )
    force: str = Field(
        default="false",
        description="是否强制删除",
    )


class TagMergeRequest(BaseModel):
    """合并标签请求."""

    project_id: str = Field(
        ...,
        description="项目 ID",
    )
    old_tag: str = Field(
        ...,
        description="旧标签名称",
    )
    new_tag: str = Field(
        ...,
        description="新标签名称",
    )
