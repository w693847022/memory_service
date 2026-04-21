"""统计请求模型."""

from pydantic import BaseModel, Field


class StatsSummaryRequest(BaseModel):
    """统计摘要请求."""

    type: str = Field(
        default="",
        description="统计类型 (tool/project/client/ip/daily/full)",
    )
    tool_name: str = Field(
        default="",
        description="工具名称 (type=tool 时)",
    )
    project_id: str = Field(
        default="",
        description="项目 ID (type=project 时)",
    )
    date: str = Field(
        default="",
        description="日期 YYYY-MM-DD (type=daily 时)",
    )


class StatsCleanupRequest(BaseModel):
    """清理统计数据请求."""

    retention_days: int = Field(
        default=30,
        ge=1,
        description="保留天数",
    )
