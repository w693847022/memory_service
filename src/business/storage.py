"""Storage Module - 存储抽象层.

提供统一的数据存储接口，整合项目存储和统计存储功能。
"""

from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from business.core.storage_base import ProjectStorage
from business.call_stats import CallStats
from src.models.storage import ProjectData


# ===================
# 配置参数
# ===================

STATS_RETENTION_DAYS = 30
CLEANUP_INTERVAL_SECONDS = 3600
MIN_USAGE_THRESHOLD = 10
ENABLE_AUTO_CLEANUP = True
CACHE_TTL_SECONDS = 300
CACHE_MAX_SIZE = 50


class Storage(ProjectStorage):
    """存储抽象层 - 整合项目存储和统计存储.

    继承自 ProjectStorage，提供统一的数据访问接口。
    """

    def __init__(self, storage_dir: Union[str, Path, None] = None):
        """初始化存储抽象层.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        super().__init__(storage_dir)

        # 初始化统计模块
        self._stats = CallStats(storage_dir)

    # ==================== 统计相关方法（委托给 CallStats）====================

    def _record_call(
        self,
        tool_name: str,
        project_id: Optional[str] = None,
        client: str = "unknown",
        ip: str = "local"
    ) -> bool:
        """记录接口调用."""
        return self._stats.record_call(tool_name, project_id, client, ip)

    def _get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计."""
        return self._stats.get_tool_stats(tool_name)

    def _get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计."""
        return self._stats.get_project_stats(project_id)

    def _get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计."""
        return self._stats.get_client_stats()

    def _get_ip_stats(self) -> Dict[str, Any]:
        """获取IP统计."""
        return self._stats.get_ip_stats()

    def _get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取每日统计."""
        return self._stats.get_daily_stats(date)

    def _get_full_summary(self) -> Dict[str, Any]:
        """获取完整统计摘要."""
        return self._stats.get_full_summary()

    def _cleanup_stats(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """清理统计数据."""
        return self._stats.cleanup_stats(retention_days)

    # ==================== 项目数据访问方法（异步）====================

    async def get_project_data(self, project_id: str) -> Optional[ProjectData]:
        """获取项目数据（返回 ProjectData 模型）."""
        return await self._load_project(project_id)

    async def save_project_data(self, project_id: str, project_data: ProjectData) -> bool:
        """保存项目数据（接受 ProjectData 模型）."""
        return await self._save_project(project_id, project_data)

    async def get_group_configs(self, project_id: str) -> Dict[str, Any]:
        """获取组配置."""
        return await self._load_group_configs(project_id)

    async def save_group_configs(self, project_id: str, configs: Dict[str, Any]) -> bool:
        """保存组配置."""
        return await self._save_group_configs(project_id, configs)

    async def get_item_content(self, project_id: str, group_name: str, item_id: str) -> Optional[str]:
        """获取条目内容."""
        return await self._load_item_content(project_id, group_name, item_id)

    async def save_item_content(self, project_id: str, group_name: str, item_id: str, content: str) -> bool:
        """保存条目内容."""
        return await self._save_item_content(project_id, group_name, item_id, content)

    def delete_item_content(self, project_id: str, group_name: str, item_id: str) -> bool:
        """删除条目内容文件."""
        return self._delete_item_content(project_id, group_name, item_id)

    def generate_item_id(self, prefix: str, project_id: Optional[str] = None, project_data: Optional[Dict] = None) -> str:
        """生成条目ID."""
        return self._generate_item_id(prefix, project_id, project_data)

    def generate_timestamps(self) -> Dict[str, str]:
        """生成时间戳."""
        return self._generate_timestamps()

    def update_timestamp(self, item: Dict[str, Any]) -> None:
        """更新条目时间戳."""
        self._update_timestamp(item)

    def is_valid_uuid(self, id_str: str) -> bool:
        """验证UUID."""
        return self._is_valid_uuid(id_str)

    # ==================== 项目列表和搜索（异步）====================

    async def list_all_projects(self) -> Dict[str, str]:
        """获取所有项目缓存."""
        await self._refresh_projects_cache()
        return self._projects_cache.copy()

    async def refresh_projects_cache(self) -> None:
        """刷新项目缓存."""
        await self._refresh_projects_cache()

    # ==================== 归档相关（异步）====================

    async def archive_project(self, project_id: str) -> Dict[str, Any]:
        """归档项目."""
        result = await self._compress_and_archive_project(project_id)
        if result.get("success"):
            self._barrier.remove_project_barriers(project_id)
        return result

    async def is_archived(self, project_id: str) -> bool:
        """检查项目是否已归档."""
        return await self._is_project_archived(project_id)

    async def get_archived_projects(self) -> List[Dict[str, Any]]:
        """获取归档项目列表."""
        return await self._get_archived_projects()

    async def delete_archived_project(self, project_id: str) -> bool:
        """删除归档项目."""
        return await self._delete_archived_project(project_id)

    # ==================== 目录迁移 ====================

    def safe_migrate_project_dir(
        self,
        old_path: Path,
        new_path: Path,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """安全迁移项目目录."""
        return self._safe_migrate_project_dir(old_path, new_path, project_name)

    def delete_archive_file(self, archived_path: Optional[str]) -> bool:
        """删除归档文件."""
        return self._delete_archive_file(archived_path)
