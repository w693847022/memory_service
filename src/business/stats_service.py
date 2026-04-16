"""Stats Service Module - 统计业务逻辑服务.

提供接口调用统计、项目统计、客户端统计等业务逻辑。
"""

from typing import Optional, Dict, Any


class StatsService:
    """统计业务逻辑服务类."""

    def __init__(self, storage):
        """初始化统计服务.

        Args:
            storage: 存储层实例（需要实现 _load_project, _save_project 方法）
        """
        self.storage = storage

    def record_call(
        self,
        tool_name: str,
        project_id: Optional[str] = None,
        client: str = "unknown",
        ip: str = "local"
    ) -> bool:
        """记录一次接口调用.

        Args:
            tool_name: 工具名称
            project_id: 项目ID（可选）
            client: 客户端标识
            ip: IP地址或"local"

        Returns:
            是否记录成功
        """
        return self.storage._record_call(tool_name, project_id, client, ip)

    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计.

        Args:
            tool_name: 工具名称，为None时返回所有工具统计

        Returns:
            统计数据
        """
        return self.storage._get_tool_stats(tool_name)

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计.

        Args:
            project_id: 项目ID

        Returns:
            项目统计数据
        """
        return self.storage._get_project_stats(project_id)

    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计.

        Returns:
            客户端统计数据
        """
        return self.storage._get_client_stats()

    def get_ip_stats(self) -> Dict[str, Any]:
        """获取IP地址统计.

        Returns:
            IP地址统计数据
        """
        return self.storage._get_ip_stats()

    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取每日统计.

        Args:
            date: 日期字符串 (YYYY-MM-DD)，为None时返回最近7天

        Returns:
            每日统计数据
        """
        return self.storage._get_daily_stats(date)

    def get_full_summary(self) -> Dict[str, Any]:
        """获取完整统计摘要（所有维度）.

        Returns:
            完整统计数据
        """
        return self.storage._get_full_summary()

    def cleanup_stats(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """手动清理统计数据.

        Args:
            retention_days: 保留天数

        Returns:
            清理结果
        """
        return self.storage._cleanup_stats(retention_days)
