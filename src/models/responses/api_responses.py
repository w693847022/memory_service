"""API 响应模型 - 为 OpenAPI 文档提供完整类型定义."""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

from src.models.project import ProjectMetadata
from src.models.item import Item
from src.models.group import UnifiedGroupConfig, GroupSettings
from src.models.responses.common import PagedData
from src.models.responses.data_types import (
    ProjectRegisterResult,
    ProjectRenameResult,
    ProjectDeleteResult,
    ProjectListData,
    ProjectDetailData,
    ItemDetailData,
    ItemCreateResult,
    ItemUpdateResult,
    ItemDeleteResult,
    ItemTagsManageResult,
    GroupCreateResult,
    GroupUpdateResult,
    GroupDeleteResult,
    TagRegisterResult,
    TagUpdateResult,
    TagDeleteResult,
    TagMergeResult,
    TagDetailInfo,
    TagListItem,
    TagListData,
    ProjectTagListData,
    GlobalStatsData,
    ToolStatsData,
    ProjectStatsData,
    DailyStatsData,
    StatsCleanupResult,
    StatsSummaryData,
    ToolListData,
    ClientListData,
    IpListData,
    DailyListData,
    GroupConfigDetail,
    GroupListData,
    HealthCheckData,
    RootInfoData,
)


# ==================== 项目相关响应 ====================

class ProjectListResponse(BaseModel):
    """项目列表响应."""
    success: bool = Field(..., description="操作是否成功")
    data: ProjectListData = Field(..., description="项目列表数据")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class ProjectDetailResponse(BaseModel):
    """项目详情响应."""
    success: bool = Field(..., description="操作是否成功")
    data: ProjectDetailData = Field(..., description="项目详情")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class ProjectOperationResponse(BaseModel):
    """项目操作响应（注册/删除/重命名）."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[ProjectRegisterResult, ProjectRenameResult, ProjectDeleteResult] = Field(..., description="操作结果")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 分组相关响应 ====================

class GroupListResponse(BaseModel):
    """分组列表响应."""
    success: bool = Field(..., description="操作是否成功")
    data: GroupListData = Field(..., description="分组配置列表")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class GroupSettingsResponse(BaseModel):
    """分组设置响应."""
    success: bool = Field(..., description="操作是否成功")
    data: GroupSettings = Field(..., description="分组设置")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class GroupOperationResponse(BaseModel):
    """分组操作响应."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[GroupCreateResult, GroupUpdateResult, GroupDeleteResult] = Field(..., description="操作结果")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 条目相关响应 ====================

class ItemListResponse(BaseModel):
    """条目列表响应（分页）."""
    success: bool = Field(..., description="操作是否成功")
    data: PagedData = Field(..., description="分页条目数据")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class ItemDetailResponse(BaseModel):
    """条目详情响应."""
    success: bool = Field(..., description="操作是否成功")
    data: ItemDetailData = Field(..., description="条目详情数据")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class ItemOperationResponse(BaseModel):
    """条目操作响应（创建/更新/删除）."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[ItemCreateResult, ItemUpdateResult, ItemDeleteResult, ItemTagsManageResult] = Field(..., description="操作结果")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 标签相关响应 ====================

class TagInfoResponse(BaseModel):
    """标签信息响应."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[TagListData, TagDetailInfo, ProjectTagListData] = Field(..., description="标签信息")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


class TagOperationResponse(BaseModel):
    """标签操作响应."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[TagRegisterResult, TagUpdateResult, TagDeleteResult, TagMergeResult] = Field(..., description="操作结果")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 统计相关响应 ====================

class StatsResponse(BaseModel):
    """统计信息响应."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[
        GlobalStatsData,
        ToolStatsData,
        ProjectStatsData,
        DailyStatsData,
        StatsCleanupResult,
        StatsSummaryData,
        ToolListData,
        ClientListData,
        IpListData,
        DailyListData,
    ] = Field(..., description="统计数据")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 通用操作响应 ====================

class MessageResponse(BaseModel):
    """通用消息响应（用于返回简单确认）."""
    success: bool = Field(..., description="操作是否成功")
    data: Union[HealthCheckData, RootInfoData] = Field(..., description="操作结果")
    message: Optional[str] = Field(None, description="操作消息")
    error: Optional[str] = Field(None, description="错误信息")
