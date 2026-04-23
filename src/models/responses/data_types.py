"""API 响应 data 字段的具体类型定义."""

from typing import List, Dict, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field


# ==================== 项目操作结果 ====================

class ProjectRegisterResult(BaseModel):
    """项目注册结果."""
    project_id: str = Field(..., description="新生成的项目ID")


class ProjectRenameResult(BaseModel):
    """项目重命名结果."""
    old_name: str = Field(..., description="原项目名称")
    new_name: str = Field(..., description="新项目名称")


class ProjectDeleteResult(BaseModel):
    """项目删除结果."""
    project_id: str = Field(..., description="被删除的项目ID")
    mode: str = Field(..., description="操作模式: archive 或 delete")


class ProjectDetailData(BaseModel):
    """项目详情数据."""
    id: str = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    version: int = Field(alias="_version", description="版本号")
    versions: Dict[str, int] = Field(alias="_versions", description="各组件版本号")
    info: Dict[str, Any] = Field(..., description="项目元数据")
    tag_count: int = Field(..., description="标签数量")
    group_configs: Optional[Any] = Field(alias="_group_configs", default=None, description="分组配置")

    model_config = {"populate_by_name": True}


class ProjectListData(BaseModel):
    """项目列表数据（分页）."""
    total: int = Field(..., description="总项目数")
    filtered_total: int = Field(..., description="过滤后项目数")
    projects: List[Dict[str, Any]] = Field(..., description="项目列表")
    page: Optional[int] = Field(None, description="当前页码")
    size: Optional[int] = Field(None, description="每页条数")
    total_pages: Optional[int] = Field(None, description="总页数")
    has_next: Optional[bool] = Field(None, description="是否有下一页")
    has_prev: Optional[bool] = Field(None, description="是否有上一页")
    filters: Optional[Dict[str, Any]] = Field(None, description="应用的过滤条件")


# ==================== 条目操作结果 ====================

class ItemCreateResult(BaseModel):
    """条目创建结果."""
    project_id: str = Field(..., description="项目ID")
    group: str = Field(..., description="分组名称")
    item_id: str = Field(..., description="新生成的条目ID")
    item: Optional[Dict[str, Any]] = Field(None, description="创建的条目完整信息")


class ItemDetailData(BaseModel):
    """条目详情数据（用于 GET /api/projects/{project_id}/items?item_id=xxx）."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(..., description="分组名称")
    item_id: str = Field(..., description="条目ID")
    item: Dict[str, Any] = Field(..., description="条目完整信息")


class ItemUpdateResult(BaseModel):
    """条目更新结果."""
    project_id: str = Field(..., description="项目ID")
    group: str = Field(..., description="分组名称")
    item_id: str = Field(..., description="条目ID")
    version: int = Field(..., description="新版本号")


class ItemDeleteResult(BaseModel):
    """条目删除结果."""
    project_id: str = Field(..., description="项目ID")
    group: str = Field(..., description="分组名称")
    item_id: str = Field(..., description="被删除的条目ID")
    deleted: bool = Field(..., description="是否删除成功")


class ItemTagsManageResult(BaseModel):
    """条目标签管理结果."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(..., description="分组名称")
    item_id: str = Field(..., description="条目ID")
    operation: str = Field(..., description="执行的操作: set/add/remove")
    tags: List[str] = Field(..., description="操作后的标签列表")


# ==================== 分组操作结果 ====================

class GroupCreateResult(BaseModel):
    """分组创建结果."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(..., description="创建的分组名称")


class GroupUpdateResult(BaseModel):
    """分组更新结果."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(..., description="更新的分组名称")
    updated: bool = Field(..., description="是否更新成功")


class GroupDeleteResult(BaseModel):
    """分组删除结果."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(..., description="被删除的分组名称")
    deleted: bool = Field(..., description="是否删除成功")


# ==================== 标签操作结果 ====================

class TagRegisterResult(BaseModel):
    """标签注册结果."""
    project_id: str = Field(..., description="项目ID")
    tag_name: str = Field(..., description="注册的标签名称")
    tag_info: Dict[str, Any] = Field(..., description="标签信息")


class TagUpdateResult(BaseModel):
    """标签更新结果."""
    project_id: str = Field(..., description="项目ID")
    tag_name: str = Field(..., description="更新的标签名称")
    updated: bool = Field(..., description="是否更新成功")


class TagDeleteResult(BaseModel):
    """标签删除结果."""
    project_id: str = Field(..., description="项目ID")
    tag_name: str = Field(..., description="被删除的标签名称")
    force: bool = Field(..., description="是否强制删除")
    deleted: bool = Field(..., description="是否删除成功")


class TagMergeResult(BaseModel):
    """标签合并结果."""
    project_id: str = Field(..., description="项目ID")
    old_tag: str = Field(..., description="被合并的旧标签")
    new_tag: str = Field(..., description="合并到的新标签")
    merged: bool = Field(..., description="是否合并成功")


# ==================== 标签信息 ====================

class TagDetailInfo(BaseModel):
    """标签详细信息."""
    tag: str = Field(..., description="标签名称")
    summary: str = Field(..., description="标签摘要")
    usage_count: int = Field(..., description="使用次数")
    created_at: str = Field(..., description="创建时间")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    groups: List[str] = Field(default_factory=list, description="使用的分组")
    group_counts: Dict[str, int] = Field(default_factory=dict, description="各分组的数量")
    is_registered: bool = Field(default=True, description="是否已注册")


class TagListItem(BaseModel):
    """标签列表项."""
    tag: str = Field(..., description="标签名称")
    count: int = Field(..., description="使用次数")
    summary: Optional[str] = Field(None, description="标签摘要")
    is_registered: bool = Field(default=True, description="是否已注册")


class TagListData(BaseModel):
    """标签列表数据."""
    project_id: str = Field(..., description="项目ID")
    group_name: str = Field(default="", description="分组名称（可选）")
    total_tags: int = Field(..., description="总标签数")
    filtered_total: int = Field(..., description="过滤后标签数")
    tags: List[TagListItem] = Field(..., description="标签列表")
    page: Optional[int] = Field(None, description="当前页码")
    page_size: Optional[int] = Field(None, description="每页条数")


class ProjectTagListData(BaseModel):
    """项目标签列表数据（用于 GET /api/projects/{project_id}/tags）."""
    project_id: str = Field(..., description="项目ID")
    total_tags: int = Field(..., description="总标签数")
    filtered_total: int = Field(..., description="过滤后标签数")
    tags: List[Dict[str, Any]] = Field(..., description="标签列表")
    page: Optional[int] = Field(None, description="当前页码")
    size: Optional[int] = Field(None, description="每页条数")
    total_pages: Optional[int] = Field(None, description="总页数")
    has_next: Optional[bool] = Field(None, description="是否有下一页")
    has_prev: Optional[bool] = Field(None, description="是否有上一页")


# ==================== 统计数据 ====================

class FeatureStatusStats(BaseModel):
    """功能状态统计."""
    pending: int = Field(..., description="待处理数量")
    in_progress: int = Field(..., description="进行中数量")
    completed: int = Field(..., description="已完成数量")


class GlobalStatsData(BaseModel):
    """全局统计数据."""
    total_projects: int = Field(..., description="总项目数")
    total_features: int = Field(..., description="总功能数")
    total_notes: int = Field(..., description="总笔记数")
    feature_status: FeatureStatusStats = Field(..., description="功能状态统计")
    top_project_tags: List[Tuple[str, int]] = Field(default_factory=list, description="最常用项目标签")
    top_feature_tags: List[Tuple[str, int]] = Field(default_factory=list, description="最常用功能标签")
    top_note_tags: List[Tuple[str, int]] = Field(default_factory=list, description="最常用笔记标签")


class ToolStatsData(BaseModel):
    """工具统计数据."""
    type: str = Field(..., description="统计类型: tool")
    tool_name: str = Field(..., description="工具名称")
    total: int = Field(..., description="总调用次数")
    first_called: str = Field(..., description="首次调用时间")
    last_called: str = Field(..., description="最后调用时间")
    by_project: Dict[str, int] = Field(default_factory=dict, description="按项目统计")
    by_client: Dict[str, int] = Field(default_factory=dict, description="按客户端统计")
    by_ip: Dict[str, int] = Field(default_factory=dict, description="按IP统计")


class ProjectStatsData(BaseModel):
    """项目统计数据."""
    type: str = Field(..., description="统计类型: project")
    project_id: str = Field(..., description="项目ID")
    total_calls: int = Field(..., description="总调用次数")
    tools_called: List[str] = Field(default_factory=list, description="使用的工具列表")


class DailyStatsData(BaseModel):
    """每日统计数据."""
    type: str = Field(..., description="统计类型: daily")
    date: str = Field(..., description="日期")
    total_calls: int = Field(..., description="总调用次数")
    tools: Dict[str, int] = Field(default_factory=dict, description="各工具调用次数")


class StatsCleanupResult(BaseModel):
    """统计清理结果."""
    retention_days: int = Field(..., description="保留天数")
    cutoff_date: str = Field(..., description="截止日期")
    daily_stats_removed: int = Field(..., description="删除的每日统计数")
    storage_before: int = Field(..., description="清理前存储大小")
    storage_after: int = Field(..., description="清理后存储大小")


class StatsSummaryData(BaseModel):
    """统计摘要数据（默认返回类型）."""
    type: str = Field(..., description="统计类型: summary")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    tool_stats: Dict[str, Any] = Field(..., description="工具统计")
    client_stats: Dict[str, Any] = Field(..., description="客户端统计")
    daily_stats: Dict[str, Any] = Field(..., description="每日统计")


class ToolListData(BaseModel):
    """工具列表数据（所有工具调用统计）."""
    type: str = Field(..., description="统计类型: tool")
    tools: List[Dict[str, Any]] = Field(..., description="工具列表")


class ClientListData(BaseModel):
    """客户端列表数据."""
    type: str = Field(..., description="统计类型: client")
    clients: List[Dict[str, Any]] = Field(..., description="客户端列表")


class IpListData(BaseModel):
    """IP地址列表数据."""
    type: str = Field(..., description="统计类型: ip")
    ips: List[Dict[str, Any]] = Field(..., description="IP地址列表")


class DailyListData(BaseModel):
    """每日统计列表数据（最近7天）."""
    type: str = Field(..., description="统计类型: daily")
    recent_days: int = Field(..., description="最近天数")
    stats: List[Dict[str, Any]] = Field(..., description="每日统计列表")


# ==================== 分组信息 ====================

class GroupConfigDetail(BaseModel):
    """分组配置详情."""
    name: str = Field(..., description="分组名称")
    count: int = Field(default=0, description="条目数量")
    is_builtin: bool = Field(..., description="是否为内置分组")
    content_max_bytes: int = Field(..., description="内容最大字节数")
    summary_max_bytes: int = Field(..., description="摘要最大字节数")
    allow_related: bool = Field(..., description="是否允许关联")
    allowed_related_to: List[str] = Field(default_factory=list, description="允许关联的分组")
    enable_status: bool = Field(..., description="是否启用状态")
    enable_severity: bool = Field(..., description="是否启用严重程度")
    max_tags: int = Field(..., description="最大标签数")
    status_values: List[str] = Field(default_factory=list, description="状态值列表")
    severity_values: List[str] = Field(default_factory=list, description="严重程度值列表")
    required_fields: List[str] = Field(default_factory=list, description="必填字段")
    description: str = Field(default="", description="分组描述")
    mcp_access: Literal["writable", "readable", "disabled"] = Field(default="writable", description="MCP访问控制: writable(可读写)/readable(只读)/disabled(不可访问)")


class GroupListData(BaseModel):
    """分组列表数据."""
    groups: List[GroupConfigDetail] = Field(..., description="分组配置列表")
    settings: Dict[str, Any] = Field(default_factory=dict, description="全局设置")


# ==================== 健康检查 ====================

class HealthCheckData(BaseModel):
    """健康检查数据."""
    status: str = Field(..., description="服务状态: healthy")


class RootInfoData(BaseModel):
    """根路径信息数据."""
    name: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    docs: str = Field(..., description="文档地址")
    health: str = Field(..., description="健康检查地址")
