"""统计数据模型"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ToolStats(BaseModel):
    """工具统计数据

    跟踪单个工具的调用统计信息，包括总调用次数、按项目/客户端/IP的分布等。
    """
    total: int = Field(default=0, description="总调用次数")
    by_project: Dict[str, int] = Field(default_factory=dict, description="按项目分组的调用次数")
    by_client: Dict[str, int] = Field(default_factory=dict, description="按客户端分组的调用次数")
    by_ip: Dict[str, int] = Field(default_factory=dict, description="按IP分组的调用次数")
    first_called: Optional[str] = Field(default=None, description="首次调用时间 (ISO格式)")
    last_called: Optional[str] = Field(default=None, description="最后调用时间 (ISO格式)")

    def record_call(
        self,
        project_id: str,
        client_id: str,
        ip: str,
        timestamp: Optional[str] = None
    ) -> None:
        """记录一次调用

        Args:
            project_id: 项目ID
            client_id: 客户端ID
            ip: 客户端IP
            timestamp: 调用时间戳 (ISO格式)，默认为当前时间
        """
        self.total += 1

        # 更新分组统计
        self.by_project[project_id] = self.by_project.get(project_id, 0) + 1
        self.by_client[client_id] = self.by_client.get(client_id, 0) + 1
        self.by_ip[ip] = self.by_ip.get(ip, 0) + 1

        # 更新时间戳
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        if self.first_called is None:
            self.first_called = timestamp
        self.last_called = timestamp


class DailyStats(BaseModel):
    """每日统计数据

    跟踪单日内的工具调用统计。
    """
    total_calls: int = Field(default=0, description="当日总调用次数")
    tools: Dict[str, int] = Field(default_factory=dict, description="按工具分组的调用次数")

    def record_call(self, tool_name: str) -> None:
        """记录一次工具调用

        Args:
            tool_name: 工具名称
        """
        self.total_calls += 1
        self.tools[tool_name] = self.tools.get(tool_name, 0) + 1


class CallStatsData(BaseModel):
    """调用统计数据容器

    存储所有工具的调用统计和每日统计数据。
    """
    version: str = Field(default="1.0", description="数据格式版本")
    created_at: str = Field(description="创建时间 (ISO格式)")
    tool_calls: Dict[str, ToolStats] = Field(
        default_factory=dict,
        description="按工具名称索引的调用统计"
    )
    daily_stats: Dict[str, DailyStats] = Field(
        default_factory=dict,
        description="按日期索引的每日统计 (格式: YYYY-MM-DD)"
    )

    def get_or_create_tool_stats(self, tool_name: str) -> ToolStats:
        """获取或创建工具统计数据

        Args:
            tool_name: 工具名称

        Returns:
            ToolStats: 工具统计对象
        """
        if tool_name not in self.tool_calls:
            self.tool_calls[tool_name] = ToolStats()
        return self.tool_calls[tool_name]

    def get_or_create_daily_stats(self, date: str) -> DailyStats:
        """获取或创建每日统计数据

        Args:
            date: 日期字符串 (格式: YYYY-MM-DD)

        Returns:
            DailyStats: 每日统计对象
        """
        if date not in self.daily_stats:
            self.daily_stats[date] = DailyStats()
        return self.daily_stats[date]
