#!/usr/bin/env python
"""Call Statistics Module - 接口调用统计模块.

从 features/stats.py 移动到此模块，实现业务层自包含。
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Union
import threading

from cachetools import TTLCache

# ===================
# 配置参数
# ===================

# 统计数据保留配置
STATS_RETENTION_DAYS = 30          # 保留最近 30 天的日统计
CLEANUP_INTERVAL_SECONDS = 3600    # 每小时清理一次
MIN_USAGE_THRESHOLD = 10           # 使用次数低于 10 次的条目可清理
ENABLE_AUTO_CLEANUP = True         # 是否启用自动清理

# TTL 缓存配置
CACHE_TTL_SECONDS = 300            # 缓存过期时间（秒）
CACHE_MAX_SIZE = 50                # 最大缓存条目数


class CallStats:
    """接口调用统计类."""

    def __init__(self, storage_dir: Union[str, Path, None] = None):
        """初始化调用统计管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        if storage_dir is None:
            # 优先使用环境变量，否则使用 Path.home()
            storage_dir = os.environ.get("MCP_STORAGE_DIR", Path.home() / ".project_memory_ai")
        storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.stats_path = self.storage_dir / "_stats.json"
        self._lock = threading.RLock()  # 使用可重入锁
        self.data = self._load_stats()
        self._last_cleanup_time = time.time()  # 上次清理时间

    def _load_stats(self) -> Dict[str, Any]:
        """加载统计数据."""
        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "tool_calls": {},
            "daily_stats": {}
        }

    def _save_stats(self) -> bool:
        """保存统计数据."""
        try:
            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def record_call(self, tool_name: str, project_id: Optional[str] = None,
                    client: str = "unknown", ip: str = "local") -> bool:
        """记录一次接口调用.

        Args:
            tool_name: 工具名称
            project_id: 项目ID（可选）
            client: 客户端标识
            ip: IP地址或"local"

        Returns:
            是否记录成功
        """
        with self._lock:
            try:
                # 自动清理：每隔 CLEANUP_INTERVAL_SECONDS 秒触发一次清理
                if ENABLE_AUTO_CLEANUP:
                    if time.time() - self._last_cleanup_time > CLEANUP_INTERVAL_SECONDS:
                        self._cleanup_old_stats()
                        self._last_cleanup_time = time.time()

                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                timestamp = now.isoformat()

                # 初始化工具统计
                if tool_name not in self.data["tool_calls"]:
                    self.data["tool_calls"][tool_name] = {
                        "total": 0,
                        "by_project": {},
                        "by_client": {},
                        "by_ip": {},
                        "first_called": None,
                        "last_called": None
                    }

                tool_stats = self.data["tool_calls"][tool_name]
                tool_stats["total"] += 1
                tool_stats["last_called"] = timestamp
                if tool_stats["first_called"] is None:
                    tool_stats["first_called"] = timestamp

                # 按项目统计
                if project_id:
                    tool_stats["by_project"][project_id] = tool_stats["by_project"].get(project_id, 0) + 1

                # 按客户端统计
                tool_stats["by_client"][client] = tool_stats["by_client"].get(client, 0) + 1

                # 按IP统计
                tool_stats["by_ip"][ip] = tool_stats["by_ip"].get(ip, 0) + 1

                # 每日统计
                if date_str not in self.data["daily_stats"]:
                    self.data["daily_stats"][date_str] = {
                        "total_calls": 0,
                        "tools": {}
                    }

                self.data["daily_stats"][date_str]["total_calls"] += 1
                self.data["daily_stats"][date_str]["tools"][tool_name] = \
                    self.data["daily_stats"][date_str]["tools"].get(tool_name, 0) + 1

                return self._save_stats()
            except Exception:
                return False

    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计.

        Args:
            tool_name: 工具名称，为None时返回所有工具统计

        Returns:
            统计数据
        """
        with self._lock:
            if tool_name:
                if tool_name in self.data["tool_calls"]:
                    return {
                        "success": True,
                        "tool": tool_name,
                        **self.data["tool_calls"][tool_name]
                    }
                return {"success": False, "error": f"工具 '{tool_name}' 无统计记录"}

            # 返回所有工具统计摘要
            summary = []
            for name, stats in self.data["tool_calls"].items():
                summary.append({
                    "tool": name,
                    "total": stats["total"],
                    "last_called": stats["last_called"]
                })

            return {
                "success": True,
                "tools": sorted(summary, key=lambda x: x["total"], reverse=True)
            }

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计.

        Args:
            project_id: 项目ID

        Returns:
            项目统计数据
        """
        with self._lock:
            tools_called = {}
            total_calls = 0

            for tool_name, tool_stats in self.data["tool_calls"].items():
                if project_id in tool_stats["by_project"]:
                    count = tool_stats["by_project"][project_id]
                    tools_called[tool_name] = count
                    total_calls += count

            if not tools_called:
                return {"success": False, "error": f"项目 '{project_id}' 无调用记录"}

            return {
                "success": True,
                "project_id": project_id,
                "total_calls": total_calls,
                "tools_called": tools_called
            }

    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计.

        Returns:
            客户端统计数据
        """
        with self._lock:
            client_stats = {}

            for tool_name, tool_stats in self.data["tool_calls"].items():
                for client, count in tool_stats["by_client"].items():
                    client_stats[client] = client_stats.get(client, 0) + count

            return {
                "success": True,
                "clients": sorted(client_stats.items(), key=lambda x: x[1], reverse=True)
            }

    def get_ip_stats(self) -> Dict[str, Any]:
        """获取IP地址统计.

        Returns:
            IP地址统计数据
        """
        with self._lock:
            ip_stats = {}

            for tool_name, tool_stats in self.data["tool_calls"].items():
                for ip, count in tool_stats["by_ip"].items():
                    ip_stats[ip] = ip_stats.get(ip, 0) + count

            return {
                "success": True,
                "ips": sorted(ip_stats.items(), key=lambda x: x[1], reverse=True)
            }

    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取每日统计.

        Args:
            date: 日期字符串 (YYYY-MM-DD)，为None时返回最近7天

        Returns:
            每日统计数据
        """
        with self._lock:
            if date:
                if date in self.data["daily_stats"]:
                    return {
                        "success": True,
                        "date": date,
                        **self.data["daily_stats"][date]
                    }
                return {"success": False, "error": f"日期 '{date}' 无统计记录"}

            # 返回最近7天
            from collections import OrderedDict
            sorted_dates = sorted(self.data["daily_stats"].keys(), reverse=True)[:7]
            recent_stats = OrderedDict()
            for d in sorted_dates:
                recent_stats[d] = self.data["daily_stats"][d]

            return {
                "success": True,
                "recent_days": list(recent_stats.keys()),
                "stats": recent_stats
            }

    def get_full_summary(self) -> Dict[str, Any]:
        """获取完整统计摘要（所有维度）.

        Returns:
            完整统计数据
        """
        with self._lock:
            total_calls = sum(ts["total"] for ts in self.data["tool_calls"].values())

            return {
                "success": True,
                "metadata": {
                    "version": self.data["version"],
                    "created_at": self.data["created_at"],
                    "total_calls": total_calls,
                    "total_tools": len(self.data["tool_calls"]),
                    "total_days": len(self.data["daily_stats"])
                },
                "tool_stats": self.get_tool_stats(),
                "client_stats": self.get_client_stats(),
                "ip_stats": self.get_ip_stats(),
                "daily_stats": self.get_daily_stats()
            }

    def _cleanup_daily_data(self, cutoff_date: str) -> int:
        """清理过期的每日统计数据.

        Args:
            cutoff_date: 截止日期 (YYYY-MM-DD)，此日期之前的数据将被删除

        Returns:
            删除的条目数
        """
        removed_count = 0
        dates_to_remove = []

        for date_str in self.data["daily_stats"].keys():
            if date_str < cutoff_date:
                dates_to_remove.append(date_str)

        for date_str in dates_to_remove:
            del self.data["daily_stats"][date_str]
            removed_count += 1

        return removed_count

    def _cleanup_old_stats(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """清理过期的统计数据.

        Args:
            retention_days: 保留天数，默认使用 STATS_RETENTION_DAYS

        Returns:
            清理结果统计
        """
        if retention_days is None:
            retention_days = STATS_RETENTION_DAYS

        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")

        # 清理每日统计
        daily_removed = self._cleanup_daily_data(cutoff_date)

        # 清理工具调用统计中的低使用率和过期条目
        tools_removed = 0
        projects_cleaned = 0
        clients_cleaned = 0
        ips_cleaned = 0

        tools_to_remove = []

        for tool_name, tool_stats in self.data["tool_calls"].items():
            # 检查工具是否长期未使用（超过保留期且使用次数低）
            last_called = tool_stats.get("last_called", "")
            total_calls = tool_stats.get("total", 0)

            if last_called:
                try:
                    last_called_date = datetime.fromisoformat(last_called).strftime("%Y-%m-%d")
                    if last_called_date < cutoff_date and total_calls < MIN_USAGE_THRESHOLD:
                        tools_to_remove.append(tool_name)
                        continue
                except (ValueError, TypeError):
                    pass

            # 清理工具统计中的过期项目、客户端和IP
            if "by_project" in tool_stats:
                projects_to_remove = [
                    proj_id for proj_id in tool_stats["by_project"]
                    if len(proj_id) > 0  # 可以添加更复杂的逻辑
                ][:10]  # 限制每次清理数量
                for proj_id in projects_to_remove:
                    if tool_stats["by_project"].get(proj_id, 0) < MIN_USAGE_THRESHOLD:
                        del tool_stats["by_project"][proj_id]
                        projects_cleaned += 1

            if "by_client" in tool_stats:
                clients_to_remove = [
                    client for client, count in tool_stats["by_client"].items()
                    if count < MIN_USAGE_THRESHOLD
                ][:10]
                for client in clients_to_remove:
                    del tool_stats["by_client"][client]
                    clients_cleaned += 1

            if "by_ip" in tool_stats:
                ips_to_remove = [
                    ip for ip, count in tool_stats["by_ip"].items()
                    if count < MIN_USAGE_THRESHOLD
                ][:10]
                for ip in ips_to_remove:
                    del tool_stats["by_ip"][ip]
                    ips_cleaned += 1

        for tool_name in tools_to_remove:
            del self.data["tool_calls"][tool_name]
            tools_removed += 1

        # 保存清理后的数据
        self._save_stats()

        return {
            "daily_stats_removed": daily_removed,
            "tools_removed": tools_removed,
            "projects_cleaned": projects_cleaned,
            "clients_cleaned": clients_cleaned,
            "ips_cleaned": ips_cleaned,
            "cutoff_date": cutoff_date
        }

    def cleanup_stats(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """手动清理统计数据（MCP工具接口）.

        Args:
            retention_days: 保留天数，默认使用 STATS_RETENTION_DAYS

        Returns:
            清理结果
        """
        with self._lock:
            before_size = {
                "daily_stats": len(self.data["daily_stats"]),
                "tool_calls": len(self.data["tool_calls"])
            }

            result = self._cleanup_old_stats(retention_days)

            after_size = {
                "daily_stats": len(self.data["daily_stats"]),
                "tool_calls": len(self.data["tool_calls"])
            }

            return {
                "success": True,
                "cleanup_result": result,
                "before": before_size,
                "after": after_size
            }