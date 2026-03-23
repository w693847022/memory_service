#!/usr/bin/env python
"""Project Memory Module - 项目记忆功能模块."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
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

    def __init__(self, storage_dir: str = None):
        """初始化调用统计管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        if storage_dir is None:
            home = Path.home()
            storage_dir = home / ".project_memory_ai"

        self.storage_dir = Path(storage_dir)
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

    def record_call(self, tool_name: str, project_id: str = None,
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

    def get_tool_stats(self, tool_name: str = None) -> Dict[str, Any]:
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

    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
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

    def _cleanup_old_stats(self, retention_days: int = None) -> Dict[str, Any]:
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

    def cleanup_stats(self, retention_days: int = None) -> Dict[str, Any]:
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


# ===================
# Git and Config Helper Functions
# ===================

def get_git_info(path: str) -> Dict[str, Any]:
    """读取 Git 仓库信息.

    Args:
        path: 项目路径

    Returns:
        {
            "is_git_repo": bool,
            "git_remote": str,  # 完整 URL（带 .git）
            "git_remote_url": str,  # URL（不带 .git）
            "branch": str,
            "repo_name": str,  # 从 remote 提取的仓库名
            "root_path": str
        }
    """
    import subprocess

    result = {
        "is_git_repo": False,
        "git_remote": "",
        "git_remote_url": "",
        "branch": "",
        "repo_name": "",
        "root_path": path
    }

    try:
        # 检查是否为 Git 仓库
        git_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if git_dir.returncode != 0:
            return result

        result["is_git_repo"] = True

        # 获取 Git root 路径
        root_path = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if root_path.returncode == 0:
            result["root_path"] = root_path.stdout.strip()

        # 获取 remote URL (优先 origin)
        remote_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if remote_url.returncode == 0:
            git_remote = remote_url.stdout.strip()
            result["git_remote"] = git_remote

            # 移除 .git 后缀用于展示（使用切片而非 rstrip）
            if git_remote.endswith(".git"):
                git_remote_url = git_remote[:-4]
            else:
                git_remote_url = git_remote
            result["git_remote_url"] = git_remote_url

            # 从 URL 提取仓库名
            # 处理多种格式：
            # - https://github.com/user/repo.git
            # - git@github.com:user/repo.git
            # - https://gitlab.com/user/repo.git
            repo_name = ""

            if git_remote.endswith(".git"):
                # 提取最后一部分作为仓库名
                # 先移除 .git 后缀
                url_without_git = git_remote[:-4]
                parts = url_without_git.rstrip("/").split("/")
                repo_name = parts[-1].lower()
                # 清理仓库名（移除用户名前缀，处理 SSH 格式）
                if ":" in repo_name:
                    repo_name = repo_name.split(":")[-1]
            else:
                # 没有 .git 后缀
                parts = git_remote.rstrip("/").split("/")
                repo_name = parts[-1].lower()
                if ":" in repo_name:
                    repo_name = repo_name.split(":")[-1]

            result["repo_name"] = repo_name

        # 获取当前分支
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if branch.returncode == 0:
            result["branch"] = branch.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return result


def get_config_file_name(path: str) -> Optional[str]:
    """从配置文件读取项目名称.

    Args:
        path: 项目路径

    Returns:
        项目名称，如果未找到返回 None
    """
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # fallback for older Python versions

    # 检查 package.json
    package_json = Path(path) / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data:
                    return data["name"]
        except (json.JSONDecodeError, IOError):
            pass

    # 检查 pyproject.toml
    pyproject_toml = Path(path) / "pyproject.toml"
    if pyproject_toml.exists():
        try:
            with open(pyproject_toml, "rb") as f:  # tomllib requires binary mode
                data = tomllib.load(f)
                # 尝试多个可能的路径
                if "project" in data and "name" in data["project"]:
                    return data["project"]["name"]
                elif "tool" in data and "poetry" in data["tool"] and "name" in data["tool"]["poetry"]:
                    return data["tool"]["poetry"]["name"]
        except (Exception):
            pass

    # 检查 setup.py
    setup_py = Path(path) / "setup.py"
    if setup_py.exists():
        try:
            with open(setup_py, "r", encoding="utf-8") as f:
                content = f.read()
                # 简单的 name= 提取
                import re
                match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except (IOError, Exception):
            pass

    # 检查 go.mod
    go_mod = Path(path) / "go.mod"
    if go_mod.exists():
        try:
            with open(go_mod, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("module "):
                        module_name = line.split()[1].strip()
                        # 返回模块名的最后一部分
                        return module_name.split("/")[-1]
        except (IOError, Exception):
            pass

    # 检查 Cargo.toml
    cargo_toml = Path(path) / "Cargo.toml"
    if cargo_toml.exists():
        try:
            with open(cargo_toml, "r", encoding="utf-8") as f:
                data = toml.load(f)
                if "package" in data and "name" in data["package"]:
                    return data["package"]["name"]
        except (Exception):
            pass

    return None


class ProjectMemory:
    """项目记忆管理类 - 每个项目单独存储一个文件."""

    def __init__(self, storage_dir: str = None):
        """初始化项目记忆管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        if storage_dir is None:
            home = Path.home()
            storage_dir = home / ".project_memory_ai"

        self.storage_dir = Path(storage_dir)
        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self.metadata_path = self.storage_dir / "_metadata.json"
        self.metadata = self._load_metadata()

        # 项目列表缓存 (ID -> Name)
        self._projects_cache: Dict[str, str] = {}

        # 项目数据缓存 (ID -> Full Project Data) with TTL
        self._project_data_cache = TTLCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL_SECONDS,
            timer=time.time
        )

        # UUID -> 项目名称映射缓存 (用于反向查找)
        self._uuid_to_name_cache = TTLCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL_SECONDS,
            timer=time.time
        )

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据文件."""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_projects": 0
        }

    def _save_metadata(self) -> bool:
        """保存元数据文件."""
        try:
            self.metadata["total_projects"] = len(self._projects_cache)
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def _get_project_path(self, project_id: str) -> Path:
        """获取项目文件路径（向后兼容旧格式）."""
        return self.storage_dir / f"{project_id}.json"

    def _get_project_dir(self, project_id: str) -> Path:
        """获取项目目录路径（新格式）。

        支持两种查找方式：
        1. 如果 project_id 是项目名称（目录名），直接使用
        2. 如果 project_id 是 UUID，扫描查找对应的项目名称
        """
        # 检查是否为 UUID 格式（简单判断：包含连字符且长度较长）
        if "-" in project_id and len(project_id) > 20:
            # 可能是 UUID，尝试查找对应的项目名称
            project_name = self._find_project_name_by_uuid(project_id)
            if project_name:
                return self.storage_dir / project_name

        # 默认：直接使用 project_id 作为目录名（向后兼容）
        return self.storage_dir / project_id

    def _get_project_json_path(self, project_id: str) -> Path:
        """获取 project.json 文件路径（新格式）."""
        return self._get_project_dir(project_id) / "project.json"

    def _get_notes_dir(self, project_id: str) -> Path:
        """获取 notes 目录路径."""
        notes_dir = self._get_project_dir(project_id) / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        return notes_dir

    def _get_note_content_path(self, project_id: str, note_id: str) -> Path:
        """获取单个 note 的 .md 文件路径."""
        return self._get_notes_dir(project_id) / f"{note_id}.md"

    def _load_note_content(self, project_id: str, note_id: str) -> Optional[str]:
        """加载单个 note 的 content.

        Args:
            project_id: 项目ID
            note_id: 笔记ID

        Returns:
            content 字符串，如果文件不存在则返回 None
        """
        content_path = self._get_note_content_path(project_id, note_id)
        if content_path.exists():
            try:
                return content_path.read_text(encoding="utf-8")
            except IOError:
                return None
        return None

    def _save_note_content(self, project_id: str, note_id: str, content: str) -> bool:
        """保存单个 note 的 content.

        Args:
            project_id: 项目ID
            note_id: 笔记ID
            content: 内容字符串

        Returns:
            是否保存成功
        """
        try:
            content_path = self._get_note_content_path(project_id, note_id)
            content_path.parent.mkdir(parents=True, exist_ok=True)
            content_path.write_text(content, encoding="utf-8")
            return True
        except IOError:
            return False

    def _migrate_project_storage(self, project_id: str) -> bool:
        """迁移单个项目的存储结构（旧格式 -> 新格式）.

        旧格式: ~/.project_memory_ai/{project_id}.json
        新格式: ~/.project_memory_ai/{project_id}/project.json + notes/*.md

        使用安全迁移流程：新建目录→拷贝数据→归档原文件

        Args:
            project_id: 项目ID

        Returns:
            是否迁移成功
        """
        from datetime import datetime

        old_path = self.storage_dir / f"{project_id}.json"

        # 检查是否需要迁移（旧文件存在且新目录不存在）
        if not old_path.exists():
            return True  # 已迁移或不存在

        new_dir = self._get_project_dir(project_id)
        new_json_path = self._get_project_json_path(project_id)

        if new_json_path.exists():
            return True  # 已迁移

        # 临时目录路径（用于拷贝）
        temp_dir = self.storage_dir / f".temp_{project_id}"

        try:
            # 1. 读取旧数据
            with open(old_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 2. 迁移 notes content 到独立 .md 文件
            notes = data.get("notes", [])
            migrated_count = 0
            for note in notes:
                if "content" in note and note["content"]:
                    if self._save_note_content(project_id, note["id"], note["content"]):
                        del note["content"]
                        migrated_count += 1

            # 3. 创建临时目录并保存新的 project.json
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_json_path = temp_dir / "project.json"
            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 4. 拷贝 notes 目录（如果存在）
            temp_notes_dir = temp_dir / "notes"
            new_notes_dir = new_dir / "notes"
            if new_notes_dir.exists():
                import shutil
                shutil.copytree(new_notes_dir, temp_notes_dir, copy_function=shutil.copy2)

            # 5. 将临时目录移动到最终位置
            temp_dir.rename(new_dir)

            # 6. 归档原文件到 .archived 目录
            archive_dir = self.storage_dir / ".archived"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{timestamp}_{project_id}.json"
            archived_path = archive_dir / archive_name

            old_path.rename(archived_path)

            return True

        except (json.JSONDecodeError, IOError, OSError) as e:
            # 失败清理：删除临时目录，保留原文件
            if temp_dir.exists():
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except OSError:
                    pass
            return False

    def _load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载单个项目数据（带向后兼容和缓存）."""
        # 1. 先尝试从缓存获取
        cached_data = self._project_data_cache.get(project_id)
        if cached_data is not None:
            return cached_data

        # 2. 缓存未命中，从磁盘加载
        # 优先尝试新格式（目录结构）
        new_json_path = self._get_project_json_path(project_id)
        old_path = self._get_project_path(project_id)

        project_path = None
        if new_json_path.exists():
            # 新格式存在，直接使用
            project_path = new_json_path
        elif old_path.exists():
            # 旧格式存在，先迁移再加载
            if self._migrate_project_storage(project_id):
                project_path = new_json_path
            else:
                project_path = old_path

        if project_path and project_path.exists():
            try:
                with open(project_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 向后兼容：为没有description字段的笔记添加空description
                for note in data.get("notes", []):
                    if "description" not in note:
                        note["description"] = ""
                    # 新格式不包含 content 字段，确保不存在
                    if "content" in note:
                        del note["content"]

                # 向后兼容：为没有 tag_registry 的项目添加空注册表
                if "tag_registry" not in data:
                    data["tag_registry"] = {}

                # 向后兼容：为没有 fixes 分组的项目添加空修复列表
                if "fixes" not in data:
                    data["fixes"] = []

                # 3. 存入缓存 - TTLCache 使用字典接口
                self._project_data_cache[project_id] = data

                return data
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """保存单个项目数据（使用 write-through 缓存策略）.

        注意：notes 的 content 字段不写入 JSON，而是单独保存为 .md 文件
        """
        try:
            # 确保项目目录存在
            project_dir = self._get_project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)

            # 确保新格式的 notes 目录存在
            self._get_notes_dir(project_id)

            # 复制数据，移除 notes 中的 content 字段
            save_data = project_data.copy()
            if "notes" in save_data:
                save_data["notes"] = [
                    {k: v for k, v in note.items() if k != "content"}
                    for note in save_data["notes"]
                ]

            # 保存 project.json
            project_json_path = self._get_project_json_path(project_id)
            with open(project_json_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            # 更新缓存 (write-through) - TTLCache 使用字典接口
            self._project_data_cache[project_id] = project_data

            return True
        except IOError:
            return False

    def _refresh_projects_cache(self):
        """刷新项目缓存（支持新旧格式）."""
        self._projects_cache = {}
        self._uuid_to_name_cache = {}

        # 检查旧格式：*.json 文件
        for file_path in self.storage_dir.glob("*.json"):
            if file_path.name not in ["_metadata.json", "_stats.json"]:
                project_id = file_path.stem  # 文件名不含扩展名
                project_data = self._load_project(project_id)
                if project_data and "info" in project_data:
                    name = project_data["info"].get("name", project_id)
                    self._projects_cache[project_id] = name
                    # 同时填充 UUID 缓存（如果有 id 字段）
                    uuid_val = project_data.get("id") or project_data["info"].get("id")
                    if uuid_val:
                        self._uuid_to_name_cache[uuid_val] = name

        # 检查新格式：目录下的 project.json
        for project_dir in self.storage_dir.iterdir():
            if project_dir.is_dir():
                project_json = project_dir / "project.json"
                if project_json.exists():
                    project_name = project_dir.name  # 目录名就是项目名称
                    project_data = self._load_project(project_name)
                    if project_data:
                        # 获取 uuid 和 name
                        uuid_val = project_data.get("id") or project_data.get("info", {}).get("id")
                        name = project_data.get("name") or project_data.get("info", {}).get("name", project_name)

                        # 更新缓存
                        if uuid_val:
                            self._projects_cache[uuid_val] = name
                            self._uuid_to_name_cache[uuid_val] = name
                        else:
                            # 向后兼容：没有 uuid 的项目
                            self._projects_cache[project_name] = name

    def _generate_timestamps(self) -> Dict[str, str]:
        """生成创建和更新时间戳字典.

        Returns:
            包含 created_at 和 updated_at 的字典，两者值相同
        """
        now = datetime.now().isoformat()
        return {"created_at": now, "updated_at": now}

    def _update_timestamp(self, item: Dict[str, Any]) -> None:
        """更新条目的 updated_at 字段.

        Args:
            item: 条目字典（直接修改）
        """
        item["updated_at"] = datetime.now().isoformat()

    # ==================== UUID 验证 ====================

    def _is_valid_uuid(self, id_str: str) -> bool:
        """验证字符串是否为有效的 UUID v4 格式.

        UUID v4 格式: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        其中 x 是任意十六进制数字，y 是 8, 9, a, 或 b

        Args:
            id_str: 待验证的字符串

        Returns:
            是否为有效的 UUID v4
        """
        import re
        UUID_V4_PATTERN = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(UUID_V4_PATTERN.match(id_str))

    # ==================== 项目ID生成 ====================

    def _generate_id(self, name: str) -> str:
        """生成项目ID - 使用 UUID，与名称无关."""
        import uuid
        return str(uuid.uuid4())

    # ==================== 安全目录迁移 ====================

    def _safe_migrate_project_dir(
        self,
        old_path: Path,
        new_path: Path,
        project_name: str = None
    ) -> Dict[str, Any]:
        """安全迁移项目目录：新建→拷贝→归档。

        流程：
        1. 检查目标目录是否存在（存在则报错）
        2. 创建目标目录
        3. 递归拷贝数据（保留元数据）
        4. 拷贝成功后归档原目录
        5. 失败时回滚：删除临时目录 + 保留原目录

        Args:
            old_path: 原项目目录路径
            new_path: 新项目目录路径
            project_name: 项目名称（用于归档命名）

        Returns:
            操作结果 {"success": bool, "message": str, "archived_path": str}
        """
        import shutil
        from datetime import datetime

        # 1. 检查目标目录是否已存在
        if new_path.exists():
            return {
                "success": False,
                "error": f"目标目录已存在: {new_path}"
            }

        # 2. 检查原目录是否存在
        if not old_path.exists():
            return {
                "success": False,
                "error": f"原目录不存在: {old_path}"
            }

        temp_new_path = None
        archived_path = None

        try:
            # 3. 创建目标目录并拷贝数据
            shutil.copytree(old_path, new_path, copy_function=shutil.copy2)
            temp_new_path = new_path

            # 4. 拷贝成功，归档原目录
            archive_dir = self.storage_dir / ".archived"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{timestamp}_{project_name or old_path.name}"
            archived_path = archive_dir / archive_name

            shutil.move(str(old_path), str(archived_path))

            return {
                "success": True,
                "message": "目录迁移成功",
                "archived_path": str(archived_path)
            }

        except (OSError, shutil.Error) as e:
            # 5. 失败回滚：删除临时目录
            if temp_new_path and temp_new_path.exists():
                try:
                    shutil.rmtree(temp_new_path)
                except OSError:
                    pass

            return {
                "success": False,
                "error": f"目录迁移失败: {str(e)}"
            }

    def _delete_archive_file(self, archived_path: str) -> bool:
        """删除归档文件（不阻塞）。

        重命名成功后自动删除归档文件，删除失败不影响重命名结果。

        Args:
            archived_path: 归档文件完整路径

        Returns:
            是否删除成功
        """
        import shutil
        import logging

        if not archived_path:
            return False

        archive_path = Path(archived_path)
        if not archive_path.exists():
            return True  # 不存在视为成功

        try:
            if archive_path.is_dir():
                shutil.rmtree(archive_path)
            else:
                archive_path.unlink()
            return True
        except OSError as e:
            logging.warning(f"删除归档文件失败: {archived_path}, 错误: {e}")
            return False

    def _find_project_name_by_uuid(self, uuid_str: str) -> Optional[str]:
        """通过 UUID 查找项目名称（目录名）。

        Args:
            uuid_str: UUID 字符串

        Returns:
            项目名称（目录名），如果未找到则返回 None
        """
        # 先查缓存
        if uuid_str in self._uuid_to_name_cache:
            return self._uuid_to_name_cache[uuid_str]

        # 缓存未命中，扫描所有目录
        for project_dir in self.storage_dir.iterdir():
            if project_dir.is_dir():
                project_json = project_dir / "project.json"
                if project_json.exists():
                    try:
                        with open(project_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # 检查 id 字段（新格式）或使用目录名（向后兼容）
                            project_id = data.get("id") or data.get("info", {}).get("id")
                            if project_id == uuid_str:
                                project_name = data.get("name") or data.get("info", {}).get("name", project_dir.name)
                                # 更新缓存
                                self._uuid_to_name_cache[uuid_str] = project_name
                                return project_name
                    except (json.JSONDecodeError, IOError):
                        continue

        return None

    def _generate_item_id(self, prefix: str, project_id: str = None, project_data: Dict = None) -> str:
        """生成条目唯一ID.

        Args:
            prefix: ID前缀 (feat/note/fix)
            project_id: 项目ID
            project_data: 已加载的项目数据（避免重复加载）

        Returns:
            唯一ID，格式: prefix_YYYYMMDD_序号
        """
        date_str = datetime.now().strftime("%Y%m%d")
        max_counter = 0

        if project_id:
            # 优先使用传入的 project_data
            if project_data is None:
                project_data = self._load_project(project_id)

            if project_data:
                # 根据前缀确定检查哪个列表
                prefix_to_list = {
                    "feat": "features",
                    "note": "notes",
                    "fix": "fixes",
                    "std": "standards"
                }
                items_list = prefix_to_list.get(prefix, "features")

                # 找到当天最大的序号
                prefix_with_date = f"{prefix}_{date_str}_"
                for item in project_data.get(items_list, []):
                    item_id = item.get("id", "")
                    if item_id.startswith(prefix_with_date):
                        try:
                            # 提取序号部分（支持任意位数）
                            counter_str = item_id[len(prefix_with_date):]
                            counter = int(counter_str)
                            max_counter = max(max_counter, counter)
                        except (ValueError, IndexError):
                            continue

        # 新 ID = 最大序号 + 1（不格式化，支持任意数量）
        return f"{prefix}_{date_str}_{max_counter + 1}"

    # ==================== 项目注册 ====================

    def register_project(
        self,
        name: str,
        path: str = None,
        description: str = "",
        tags: List[str] = None,
        git_remote: str = None,
        git_remote_url: str = None
    ) -> Dict[str, Any]:
        """注册新项目.

        Args:
            name: 项目名称
            path: 项目路径（可选）
            description: 项目描述（可选）
            tags: 项目标签列表（可选）
            git_remote: Git remote URL（完整，带 .git）（可选）
            git_remote_url: Git remote URL（不带 .git）（可选）

        Returns:
            操作结果，包含项目ID
        """
        project_id = self._generate_id(name)

        project_data = {
            "id": project_id,
            "info": {
                "name": name,
                "path": path or "",
                "git_remote": git_remote or "",
                "git_remote_url": git_remote_url or "",
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": tags or []
            },
            "features": [],
            "notes": [],
            "fixes": [],  # NEW: bug修复记录
            "standards": [],  # NEW: 项目规范记录
            "tag_registry": {}  # NEW: 标签注册表
        }

        # 自动注册项目标签（如果提供）
        if tags:
            tag_registry = {}
            for tag in tags:
                if self._validate_tag_name(tag):
                    tag_registry[tag] = {
                        "description": f"项目标签: {tag}",
                        "created_at": datetime.now().isoformat(),
                        "usage_count": 0,
                        "aliases": []
                    }
            project_data["tag_registry"] = tag_registry

        # 保存项目：使用 name 作为目录名，project_id 作为 UUID
        try:
            # 确保项目目录存在（使用 name 作为目录名）
            project_dir = self.storage_dir / name
            project_dir.mkdir(parents=True, exist_ok=True)

            # 保存 project.json
            project_json_path = project_dir / "project.json"
            with open(project_json_path, "w", encoding="utf-8") as f:
                # 移除 notes 中的 content 字段（如果有）
                save_data = project_data.copy()
                if "notes" in save_data:
                    save_data["notes"] = [
                        {k: v for k, v in note.items() if k != "content"}
                        for note in save_data["notes"]
                    ]
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            # 更新缓存
            self._projects_cache[project_id] = name
            self._uuid_to_name_cache[project_id] = name
            self._project_data_cache[project_id] = project_data
            self._save_metadata()

            return {
                "success": True,
                "project_id": project_id,
                "message": f"项目 '{name}' 已成功注册，ID: {project_id}"
            }
        except IOError:
            return {
                "success": False,
                "error": "保存数据失败"
            }

    def find_project_by_git_remote(self, git_remote: str) -> Optional[str]:
        """通过 Git remote URL 查找项目ID.

        Args:
            git_remote: Git remote URL（完整，带 .git）

        Returns:
            项目ID，如果未找到返回 None
        """
        if not git_remote:
            return None

        # 刷新缓存以确保获取最新数据
        self._refresh_projects_cache()

        # 遍历所有已注册项目
        for project_id in self._projects_cache.keys():
            try:
                project_data = self._load_project(project_id)
                if project_data and "info" in project_data:
                    project_git_remote = project_data["info"].get("git_remote", "")
                    # 比较 git_remote（处理可能的后缀差异）
                    if project_git_remote == git_remote:
                        return project_id
                    # 也尝试不带 .git 的比较
                    if project_git_remote.rstrip(".git") == git_remote.rstrip(".git"):
                        return project_id
            except Exception:
                continue

        return None

    # ==================== 基本信息设置 ====================

    def set_info(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """设置项目基本信息.

        Args:
            project_id: 项目ID
            **kwargs: 要更新的字段（name, path, description, tags）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        for key, value in kwargs.items():
            if key in ["name", "path", "description", "tags"]:
                project_data["info"][key] = value

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            if "name" in kwargs:
                self._projects_cache[project_id] = kwargs["name"]
            return {
                "success": True,
                "message": f"项目 '{project_id}' 信息已更新"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== 功能记录 ====================

    def add_feature(self, project_id: str, content: str, description: str,
                    status: str = "pending", tags: List[str] = None, note_id: str = None) -> Dict[str, Any]:
        """添加功能记录.

        Args:
            project_id: 项目ID
            content: 功能详细内容
            description: 功能描述（概述）
            status: 功能状态（pending, in_progress, completed）
            tags: 功能标签列表（可选）
            note_id: 关联的笔记ID（可选）

        Returns:
            操作结果，包含功能ID
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 验证note_id存在（如果提供）
        if note_id:
            if not any(n.get("id") == note_id for n in project_data.get("notes", [])):
                return {"success": False, "error": f"笔记 '{note_id}' 不存在"}

        # 生成唯一ID（传入已加载的project_data避免重复加载）
        feature_id = self._generate_item_id("feat", project_id, project_data)

        # 更新标签使用计数
        tag_registry = project_data.get("tag_registry", {})
        if tags:
            for tag in tags:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

        # 生成时间戳
        timestamps = self._generate_timestamps()
        project_data["features"].append({
            "id": feature_id,
            "content": content,
            "description": description,
            "status": status,
            "note_id": note_id or "",
            "tags": tags or [],
            **timestamps
        })

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "feature_id": feature_id,
                "message": f"已添加功能记录到项目 '{project_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== Bug修复记录 ====================

    def add_fix(self, project_id: str, content: str, description: str, status: str = "pending",
                severity: str = "medium", related_feature: str = None,
                note_id: str = None, tags: List[str] = None) -> Dict[str, Any]:
        """添加bug修复记录.

        Args:
            project_id: 项目ID
            content: 修复详细内容
            description: 修复描述（概述）
            status: 修复状态（pending/in_progress/completed）
            severity: 严重程度（critical/high/medium/low）
            related_feature: 关联的功能ID（可选）
            note_id: 关联的笔记ID（可选）
            tags: 修复标签列表（可选）

        Returns:
            操作结果，包含修复ID
        """
        # 验证参数
        if status not in ["pending", "in_progress", "completed"]:
            return {"success": False, "error": "无效的状态值"}
        if severity not in ["critical", "high", "medium", "low"]:
            return {"success": False, "error": "无效的严重程度值"}

        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 验证note_id存在（如果提供）
        if note_id:
            if not any(n.get("id") == note_id for n in project_data.get("notes", [])):
                return {"success": False, "error": f"笔记 '{note_id}' 不存在"}

        # 验证related_feature存在（如果提供）
        if related_feature:
            if not any(f.get("id") == related_feature for f in project_data.get("features", [])):
                return {"success": False, "error": f"功能 '{related_feature}' 不存在"}

        # 生成唯一ID（传入已加载的project_data避免重复加载）
        fix_id = self._generate_item_id("fix", project_id, project_data)

        # 更新标签使用计数
        tag_registry = project_data.get("tag_registry", {})
        if tags:
            for tag in tags:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

        # 生成时间戳
        timestamps = self._generate_timestamps()
        project_data["fixes"].append({
            "id": fix_id,
            "content": content,
            "description": description,
            "status": status,
            "severity": severity,
            "related_feature": related_feature or "",
            "note_id": note_id or "",
            "tags": tags or [],
            **timestamps
        })

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "fix_id": fix_id,
                "message": f"已添加修复记录到项目 '{project_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    def update_fix(self, project_id: str, fix_id: str, content: str = None, description: str = None,
                   status: str = None, severity: str = None, related_feature: str = None,
                   note_id: str = None, tags: List[str] = None) -> Dict[str, Any]:
        """更新bug修复记录.

        Args:
            project_id: 项目ID
            fix_id: 修复ID
            content: 新的修复详细内容（可选）
            description: 新的描述（概述，可选）
            status: 新的状态（可选）
            severity: 新的严重程度（可选）
            related_feature: 新的关联功能ID（可选）
            note_id: 新的关联笔记ID（可选）
            tags: 新的标签列表（可选）

        Returns:
            更新结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找修复记录
        fix_item = None
        for fix in project_data.get("fixes", []):
            if fix.get("id") == fix_id:
                fix_item = fix
                break

        if fix_item is None:
            return {"success": False, "error": f"修复记录 '{fix_id}' 不存在"}

        # 验证note_id存在（如果提供）
        if note_id is not None:
            if not any(n.get("id") == note_id for n in project_data.get("notes", [])):
                return {"success": False, "error": f"笔记 '{note_id}' 不存在"}

        # 验证related_feature存在（如果提供）
        if related_feature is not None:
            if not any(f.get("id") == related_feature for f in project_data.get("features", [])):
                return {"success": False, "error": f"功能 '{related_feature}' 不存在"}

        # 更新字段
        if content is not None:
            fix_item["content"] = content
        if description is not None:
            fix_item["description"] = description
        if status is not None:
            if status not in ["pending", "in_progress", "completed"]:
                return {"success": False, "error": "无效的状态值"}
            fix_item["status"] = status
        if severity is not None:
            if severity not in ["critical", "high", "medium", "low"]:
                return {"success": False, "error": "无效的严重程度值"}
            fix_item["severity"] = severity
        if related_feature is not None:
            fix_item["related_feature"] = related_feature
        if note_id is not None:
            fix_item["note_id"] = note_id
        if tags is not None:
            fix_item["tags"] = tags

        # 更新条目的 updated_at 字段
        self._update_timestamp(fix_item)
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"已更新修复记录 '{fix_id}'",
                "fix": fix_item
            }
        return {"success": False, "error": "保存数据失败"}

    def delete_fix(self, project_id: str, fix_id: str) -> Dict[str, Any]:
        """删除bug修复记录.

        Args:
            project_id: 项目ID
            fix_id: 修复ID

        Returns:
            删除结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找并删除修复记录
        original_count = len(project_data.get("fixes", []))
        project_data["fixes"] = [f for f in project_data.get("fixes", [])
                                if f.get("id") != fix_id]

        if len(project_data["fixes"]) == original_count:
            return {"success": False, "error": f"修复记录 '{fix_id}' 不存在"}

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"已删除修复记录 '{fix_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    def update_feature_status(self, project_id: str, feature_index: int, status: str) -> Dict[str, Any]:
        """更新功能状态.

        Args:
            project_id: 项目ID
            feature_index: 功能索引
            status: 新状态

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if feature_index < 0 or feature_index >= len(project_data["features"]):
            return {"success": False, "error": "功能索引无效"}

        project_data["features"][feature_index]["status"] = status
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"功能状态已更新"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== 开发笔记 ====================

    def add_note(self, project_id: str, note: str, tags: List[str] = None, description: str = "") -> Dict[str, Any]:
        """添加开发笔记.

        Args:
            project_id: 项目ID
            note: 笔记内容（详细内容）
            tags: 笔记标签列表（可选）
            description: 笔记描述（简短描述，可选）

        Returns:
            操作结果，包含笔记ID
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 生成唯一ID（传入已加载的project_data避免重复加载）
        note_id = self._generate_item_id("note", project_id, project_data)

        # 更新标签使用计数
        tag_registry = project_data.get("tag_registry", {})
        if tags:
            for tag in tags:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

        # 生成时间戳
        timestamps = self._generate_timestamps()

        # 添加 note 到列表（不包含 content，content 单独保存）
        note_entry = {
            "id": note_id,
            "description": description,
            "tags": tags or [],
            **timestamps
        }
        project_data["notes"].append(note_entry)

        # 保存 content 到独立 .md 文件
        if not self._save_note_content(project_id, note_id, note):
            return {"success": False, "error": "保存笔记内容失败"}

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "note_id": note_id,
                "message": f"已添加笔记到项目 '{project_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    def add_standard(self, project_id: str, content: str, tags: List[str] = None, description: str = "") -> Dict[str, Any]:
        """添加项目规范.

        Args:
            project_id: 项目ID
            content: 规范内容（详细内容）
            tags: 规范标签列表（可选，用于细分规范类型）
            description: 规范描述（简短描述，可选）

        Returns:
            操作结果，包含规范ID
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 生成唯一ID（传入已加载的project_data避免重复加载）
        standard_id = self._generate_item_id("std", project_id, project_data)

        # 更新标签使用计数
        tag_registry = project_data.get("tag_registry", {})
        if tags:
            for tag in tags:
                if tag in tag_registry:
                    tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

        # 确保 standards 列表存在（向后兼容）
        if "standards" not in project_data:
            project_data["standards"] = []

        # 生成时间戳
        timestamps = self._generate_timestamps()
        project_data["standards"].append({
            "id": standard_id,
            "description": description,
            "content": content,
            "tags": tags or [],
            **timestamps
        })

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "standard_id": standard_id,
                "message": f"已添加规范到项目 '{project_id}'"
            }
        return {"success": False, "error": "保存数据失败"}

    # ==================== 查询功能 ====================

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取项目完整信息.

        Args:
            project_id: 项目ID

        Returns:
            项目信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        return {
            "success": True,
            "project_id": project_id,
            "data": project_data
        }

    def list_projects(self) -> Dict[str, Any]:
        """列出所有项目.

        Returns:
            项目列表
        """
        self._refresh_projects_cache()
        projects = []

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data:
                projects.append({
                    "id": project_id,
                    "name": project_data["info"]["name"],
                    "description": project_data["info"]["description"],
                    "tags": project_data["info"]["tags"],
                    "created_at": project_data["info"]["created_at"]
                })

        return {
            "success": True,
            "total": len(projects),
            "projects": projects
        }

    # ==================== 搜索功能 ====================

    def search(self, keyword: str = "", tags: List[str] = None) -> Dict[str, Any]:
        """搜索项目.

        Args:
            keyword: 关键词（搜索名称、描述、功能、笔记）
            tags: 标签过滤

        Returns:
            搜索结果
        """
        results = []
        self._refresh_projects_cache()

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data is None:
                continue

            # 标签过滤
            if tags:
                project_tags = set(project_data["info"]["tags"])
                if not set(tags).intersection(project_tags):
                    continue

            # 关键词搜索
            if keyword:
                keyword_lower = keyword.lower()
                match = False

                # 搜索名称和描述
                if (keyword_lower in project_data["info"]["name"].lower() or
                    keyword_lower in project_data["info"]["description"].lower()):
                    match = True

                # 搜索功能
                for feature in project_data["features"]:
                    if keyword_lower in feature["description"].lower():
                        match = True
                        break

                # 搜索笔记
                for note in project_data["notes"]:
                    if keyword_lower in note["content"].lower():
                        match = True
                        break

                if not match:
                    continue

            results.append({
                "id": project_id,
                "name": project_data["info"]["name"],
                "description": project_data["info"]["description"],
                "tags": project_data["info"]["tags"]
            })

        return {
            "success": True,
            "total": len(results),
            "results": results
        }

    # ==================== 分层查询功能 ====================

    def list_groups(self, project_id: str) -> Dict[str, Any]:
        """列出项目的所有分组及其统计信息.

        Args:
            project_id: 项目ID

        Returns:
            分组列表及统计信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        groups = [
            {
                "name": "features",
                "count": len(project_data["features"]),
                "description": "功能列表"
            },
            {
                "name": "notes",
                "count": len(project_data["notes"]),
                "description": "开发笔记"
            },
            {
                "name": "fixes",  # NEW
                "count": len(project_data.get("fixes", [])),  # 向后兼容
                "description": "Bug修复记录"
            },
            {
                "name": "standards",  # NEW
                "count": len(project_data.get("standards", [])),  # 向后兼容
                "description": "项目规范"
            }
        ]

        return {
            "success": True,
            "project_id": project_id,
            "groups": groups
        }

    def list_all_registered_tags(self, project_id: str) -> Dict[str, Any]:
        """列出项目中所有已注册的标签.

        Args:
            project_id: 项目ID

        Returns:
            所有已注册标签的列表，包含描述、使用次数、所属分组等信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})
        groups = ["features", "notes", "fixes", "standards"]

        # 构建标签列表
        tags_list = []
        for tag_name, tag_info in tag_registry.items():
            # 统计该标签在哪些分组中被使用
            tag_groups = []
            group_counts = {}
            for group in groups:
                items = project_data.get(group, [])
                count = sum(1 for item in items if tag_name in item.get("tags", []))
                if count > 0:
                    tag_groups.append(group)
                    group_counts[group] = count

            tags_list.append({
                "tag": tag_name,
                "description": tag_info.get("description", ""),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "aliases": tag_info.get("aliases", []),
                "groups": tag_groups,  # 标签被使用的分组列表
                "group_counts": group_counts  # 每个分组中的使用次数
            })

        # 按注册时间排序（最新的在前）
        tags_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "success": True,
            "project_id": project_id,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def list_group_tags(self, project_id: str, group_name: str) -> Dict[str, Any]:
        """列出指定分组下的所有标签及使用次数.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)

        Returns:
            标签列表及每个标签的条目数量，包含标签语义信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 从 tag_registry 获取所有注册标签
        tag_registry = project_data.get("tag_registry", {})
        items = project_data.get(group_name, [])  # 向后兼容，fixes可能不存在

        # 统计每个注册标签的使用次数
        tag_counts = {}
        for tag in tag_registry.keys():
            count = sum(1 for item in items if tag in item.get("tags", []))
            if count > 0:  # 只返回有使用的标签
                tag_counts[tag] = count

        # 按使用次数排序并包含语义信息
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = []
        for tag, count in sorted_tags:
            tag_info = tag_registry.get(tag, {})
            tags_list.append({
                "tag": tag,
                "count": count,
                "description": tag_info.get("description", "未注册"),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "is_registered": tag in tag_registry
            })

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def list_unregistered_tags(self, project_id: str, group_name: str) -> Dict[str, Any]:
        """列出指定分组下所有未注册的标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)

        Returns:
            未注册标签列表，包含每个标签的使用次数和建议
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 获取所有使用的标签
        used_tags = set()
        items = project_data.get(group_name, [])  # 向后兼容，fixes可能不存在

        for item in items:
            item_tags = item.get("tags", [])
            used_tags.update(item_tags)

        # 获取已注册的标签
        tag_registry = project_data.get("tag_registry", {})

        # 找出未注册的标签
        unregistered_tags = used_tags - set(tag_registry.keys())

        # 统计每个未注册标签的使用次数
        unregistered_tag_counts = {}
        for tag in unregistered_tags:
            count = sum(1 for item in items if tag in item.get("tags", []))
            unregistered_tag_counts[tag] = count

        # 按使用次数排序
        sorted_tags = sorted(unregistered_tag_counts.items(), key=lambda x: x[1], reverse=True)

        tags_list = []
        for tag, count in sorted_tags:
            tags_list.append({
                "tag": tag,
                "count": count,
                "suggestion": "建议使用 tag_register 注册此标签"
            })

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tags": tags_list,
            "total_tags": len(tags_list)
        }

    def query_by_tag(self, project_id: str, group_name: str, tag: str) -> Dict[str, Any]:
        """查询指定分组下某标签的所有条目.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/fixes)
            tag: 标签名称

        Returns:
            该标签下的所有条目列表，包含标签语义信息
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "fixes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        items = project_data.get(group_name, [])  # 向后兼容，fixes可能不存在
        matched_items = []

        for item in items:
            item_tags = item.get("tags", [])
            if tag in item_tags:
                matched_items.append(item)

        # 获取标签注册信息
        tag_registry = project_data.get("tag_registry", {})
        tag_info = tag_registry.get(tag, {})
        is_registered = tag in tag_registry

        return {
            "success": True,
            "project_id": project_id,
            "group": group_name,
            "tag": tag,
            "total": len(matched_items),
            "items": matched_items,
            "tag_info": {
                "description": tag_info.get("description", "未注册"),
                "usage_count": tag_info.get("usage_count", 0),
                "created_at": tag_info.get("created_at", ""),
                "is_registered": is_registered
            } if is_registered else None
        }

    # ==================== 标签管理功能 ====================

    def _validate_tag_name(self, tag_name: str) -> bool:
        """验证标签名称格式.

        Args:
            tag_name: 标签名称

        Returns:
            是否有效（只允许字母、数字、下划线、连字符，长度1-30字符）
        """
        import re
        pattern = r'^[a-zA-Z0-9_-]{1,30}$'
        return bool(re.match(pattern, tag_name))

    def _validate_description(self, description: str) -> bool:
        """验证描述长度（10-200字符，约10-50 token）.

        Args:
            description: 描述文本

        Returns:
            是否有效
        """
        return 3 <= len(description) <= 200

    def _check_tags_registered(self, project_data: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
        """检查标签是否已注册.

        Args:
            project_data: 项目数据
            tags: 标签列表

        Returns:
            检查结果，如果所有标签都已注册则返回 {"success": True}，
            否则返回 {"success": False, "error": "...", "unregistered_tags": [...]}
        """
        tag_registry = project_data.get("tag_registry", {})
        unregistered = [tag for tag in tags if tag not in tag_registry]

        if unregistered:
            return {
                "success": False,
                "error": f"标签未注册：{', '.join(unregistered)}。\n建议先使用 project_tags_info 查询已注册标签，确认无合适标签后再使用 tag_register 注册新标签",
                "unregistered_tags": unregistered
            }

        return {"success": True}

    def register_tag(self, project_id: str, tag_name: str,
                     description: str, aliases: List[str] = None) -> Dict[str, Any]:
        """注册新标签到项目标签库.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            description: 标签语义描述（10-200字符）
            aliases: 别名列表（可选）

        Returns:
            操作结果
        """
        # 验证标签名称
        if not self._validate_tag_name(tag_name):
            return {
                "success": False,
                "error": f"标签名称格式无效：'{tag_name}'。只允许英文字母、数字、下划线、连字符，长度1-30字符"
            }

        # 验证描述长度
        if not self._validate_description(description):
            return {
                "success": False,
                "error": f"描述长度无效：需要10-200字符，当前为 {len(description)} 字符"
            }

        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        # 检查标签是否已注册
        if tag_name in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 已经注册",
                "tag_info": tag_registry[tag_name]
            }

        # 注册新标签
        tag_registry[tag_name] = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
            "aliases": aliases or []
        }

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已成功注册",
                "tag_name": tag_name,
                "tag_info": tag_registry[tag_name]
            }

        return {"success": False, "error": "保存数据失败"}

    def update_tag(self, project_id: str, tag_name: str,
                   description: str = None) -> Dict[str, Any]:
        """更新已注册标签的语义信息.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            description: 新的描述（可选）

        Returns:
            操作结果
        """
        if description is not None and not self._validate_description(description):
            return {
                "success": False,
                "error": f"描述长度无效：需要10-200字符，当前为 {len(description)} 字符"
            }

        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        if tag_name not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 未注册"
            }

        # 更新描述
        if description is not None:
            tag_registry[tag_name]["description"] = description

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已更新",
                "tag_info": tag_registry[tag_name]
            }

        return {"success": False, "error": "保存数据失败"}

    def delete_tag(self, project_id: str, tag_name: str,
                   force: bool = False) -> Dict[str, Any]:
        """删除标签注册.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            force: 是否强制删除（即使标签正在使用）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        if tag_name not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 未注册"
            }

        # 检查标签是否正在使用
        usage_count = tag_registry[tag_name].get("usage_count", 0)

        if usage_count > 0 and not force:
            return {
                "success": False,
                "error": f"标签 '{tag_name}' 正在被 {usage_count} 个条目使用，请使用 force=True 强制删除"
            }

        # 删除标签
        del tag_registry[tag_name]

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"标签 '{tag_name}' 已删除"
            }

        return {"success": False, "error": "保存数据失败"}

    def merge_tags(self, project_id: str, old_tag: str,
                   new_tag: str) -> Dict[str, Any]:
        """合并标签：将所有 old_tag 的引用迁移到 new_tag.

        Args:
            project_id: 项目ID
            old_tag: 旧标签名称（将被删除）
            new_tag: 新标签名称（合并目标）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        tag_registry = project_data.get("tag_registry", {})

        # 检查两个标签都已注册
        if old_tag not in tag_registry:
            return {
                "success": False,
                "error": f"旧标签 '{old_tag}' 未注册"
            }

        if new_tag not in tag_registry:
            return {
                "success": False,
                "error": f"新标签 '{new_tag}' 未注册"
            }

        if old_tag == new_tag:
            return {
                "success": False,
                "error": "旧标签和新标签不能相同"
            }

        # 统计需要迁移的条目数量
        migrated_count = 0

        # 在 features 中迁移标签
        for feature in project_data.get("features", []):
            tags = feature.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                feature["tags"] = tags
                migrated_count += 1

        # 在 notes 中迁移标签
        for note in project_data.get("notes", []):
            tags = note.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                note["tags"] = tags
                migrated_count += 1

        # 在 fixes 中迁移标签
        for fix in project_data.get("fixes", []):
            tags = fix.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                fix["tags"] = tags
                migrated_count += 1

        # 在 standards 中迁移标签
        for standard in project_data.get("standards", []):
            tags = standard.get("tags", [])
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:
                    tags.append(new_tag)
                standard["tags"] = tags
                migrated_count += 1

        # 更新使用计数
        old_usage = tag_registry[old_tag].get("usage_count", 0)
        new_usage = tag_registry[new_tag].get("usage_count", 0)
        tag_registry[new_tag]["usage_count"] = new_usage + old_usage

        # 删除旧标签
        del tag_registry[old_tag]

        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"已将标签 '{old_tag}' 合并到 '{new_tag}'，迁移了 {migrated_count} 个条目",
                "migrated_count": migrated_count
            }

        return {"success": False, "error": "保存数据失败"}

    def update_feature_tags(self, project_id: str, feature_id: str, tags: List[str]) -> Dict[str, Any]:
        """更新功能条目的标签.

        Args:
            project_id: 项目ID
            feature_id: 功能ID
            tags: 新的标签列表

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 查找指定ID的功能
        feature_index = None
        for i, feature in enumerate(project_data["features"]):
            if feature.get("id") == feature_id:
                feature_index = i
                break

        if feature_index is None:
            return {"success": False, "error": f"功能ID '{feature_id}' 不存在"}

        # 计算标签使用计数的变化
        old_tags = project_data["features"][feature_index].get("tags", [])
        tag_registry = project_data.get("tag_registry", {})

        # 递减旧标签的使用计数
        for old_tag in old_tags:
            if old_tag in tag_registry:
                current_count = tag_registry[old_tag].get("usage_count", 0)
                tag_registry[old_tag]["usage_count"] = max(0, current_count - 1)

        # 递增新标签的使用计数
        for new_tag in tags:
            if new_tag in tag_registry:
                tag_registry[new_tag]["usage_count"] = tag_registry[new_tag].get("usage_count", 0) + 1

        project_data["features"][feature_index]["tags"] = tags
        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"功能 '{feature_id}' 标签已更新",
                "tags": tags
            }
        return {"success": False, "error": "保存数据失败"}

    def update_feature(self, project_id: str, feature_id: str, content: str = None,
                       description: str = None, status: str = None, tags: List[str] = None, note_id: str = None) -> Dict[str, Any]:
        """更新功能条目（内容、描述、状态、标签、note_id）.

        Args:
            project_id: 项目ID
            feature_id: 功能ID
            content: 新的功能详细内容（可选）
            description: 新的功能描述（概述，可选）
            status: 新的状态（可选）
            tags: 新的标签列表（可选）
            note_id: 新的关联笔记ID（可选）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找指定ID的功能
        feature_index = None
        for i, feature in enumerate(project_data["features"]):
            if feature.get("id") == feature_id:
                feature_index = i
                break

        if feature_index is None:
            return {"success": False, "error": f"功能ID '{feature_id}' 不存在"}

        # 验证note_id存在（如果提供）
        if note_id is not None:
            if not any(n.get("id") == note_id for n in project_data.get("notes", [])):
                return {"success": False, "error": f"笔记 '{note_id}' 不存在"}

        # 更新提供的字段
        if content is not None:
            project_data["features"][feature_index]["content"] = content
        if description is not None:
            project_data["features"][feature_index]["description"] = description
        if status is not None:
            project_data["features"][feature_index]["status"] = status
        if tags is not None:
            project_data["features"][feature_index]["tags"] = tags
        if note_id is not None:
            project_data["features"][feature_index]["note_id"] = note_id

        # 更新条目的 updated_at 字段
        self._update_timestamp(project_data["features"][feature_index])
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"功能 '{feature_id}' 已更新",
                "feature": project_data["features"][feature_index]
            }
        return {"success": False, "error": "保存数据失败"}

    def delete_feature(self, project_id: str, feature_id: str) -> Dict[str, Any]:
        """删除功能条目.

        Args:
            project_id: 项目ID
            feature_id: 功能ID

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找并删除指定ID的功能
        for i, feature in enumerate(project_data["features"]):
            if feature.get("id") == feature_id:
                deleted_feature = project_data["features"].pop(i)
                project_data["info"]["updated_at"] = datetime.now().isoformat()

                if self._save_project(project_id, project_data):
                    return {
                        "success": True,
                        "message": f"功能 '{deleted_feature.get('description', feature_id)}' 已删除"
                    }
                return {"success": False, "error": "保存数据失败"}

        return {"success": False, "error": f"功能ID '{feature_id}' 不存在"}

    def update_note_tags(self, project_id: str, note_id: str, tags: List[str]) -> Dict[str, Any]:
        """更新笔记条目的标签.

        Args:
            project_id: 项目ID
            note_id: 笔记ID
            tags: 新的标签列表

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 强制注册检查：所有标签必须已注册
        if tags:
            check_result = self._check_tags_registered(project_data, tags)
            if not check_result["success"]:
                return check_result

        # 查找指定ID的笔记
        note_index = None
        for i, note in enumerate(project_data["notes"]):
            if note.get("id") == note_id:
                note_index = i
                break

        if note_index is None:
            return {"success": False, "error": f"笔记ID '{note_id}' 不存在"}

        # 计算标签使用计数的变化
        old_tags = project_data["notes"][note_index].get("tags", [])
        tag_registry = project_data.get("tag_registry", {})

        # 递减旧标签的使用计数
        for old_tag in old_tags:
            if old_tag in tag_registry:
                current_count = tag_registry[old_tag].get("usage_count", 0)
                tag_registry[old_tag]["usage_count"] = max(0, current_count - 1)

        # 递增新标签的使用计数
        for new_tag in tags:
            if new_tag in tag_registry:
                tag_registry[new_tag]["usage_count"] = tag_registry[new_tag].get("usage_count", 0) + 1

        project_data["notes"][note_index]["tags"] = tags
        project_data["tag_registry"] = tag_registry
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"笔记 '{note_id}' 标签已更新",
                "tags": tags
            }
        return {"success": False, "error": "保存数据失败"}

    def update_note(self, project_id: str, note_id: str, content: str = None, tags: List[str] = None, description: str = None) -> Dict[str, Any]:
        """更新笔记条目（描述、内容、标签）.

        Args:
            project_id: 项目ID
            note_id: 笔记ID
            description: 新的描述（可选）
            content: 新的笔记内容（可选）
            tags: 新的标签列表（可选）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找指定ID的笔记
        note_index = None
        for i, note in enumerate(project_data["notes"]):
            if note.get("id") == note_id:
                note_index = i
                break

        if note_index is None:
            return {"success": False, "error": f"笔记ID '{note_id}' 不存在"}

        # 更新提供的字段
        if description is not None:
            project_data["notes"][note_index]["description"] = description
        if content is not None:
            # 保存 content 到独立 .md 文件
            if not self._save_note_content(project_id, note_id, content):
                return {"success": False, "error": "保存笔记内容失败"}
        if tags is not None:
            project_data["notes"][note_index]["tags"] = tags

        # 更新条目的 updated_at 字段
        self._update_timestamp(project_data["notes"][note_index])
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"笔记 '{note_id}' 已更新",
                "note": project_data["notes"][note_index]
            }
        return {"success": False, "error": "保存数据失败"}

    def delete_note(self, project_id: str, note_id: str) -> Dict[str, Any]:
        """删除笔记条目.

        Args:
            project_id: 项目ID
            note_id: 笔记ID

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 查找并删除指定ID的笔记
        for i, note in enumerate(project_data["notes"]):
            if note.get("id") == note_id:
                deleted_note = project_data["notes"].pop(i)

                # 删除对应的 .md 文件
                content_path = self._get_note_content_path(project_id, note_id)
                if content_path.exists():
                    try:
                        content_path.unlink()
                    except IOError:
                        pass  # 忽略删除文件失败

                project_data["info"]["updated_at"] = datetime.now().isoformat()

                if self._save_project(project_id, project_data):
                    return {
                        "success": True,
                        "message": f"笔记 '{note_id}' 已删除"
                    }
                return {"success": False, "error": "保存数据失败"}

        return {"success": False, "error": f"笔记ID '{note_id}' 不存在"}

    def update_standard(self, project_id: str, standard_id: str, content: str = None, tags: List[str] = None, description: str = None) -> Dict[str, Any]:
        """更新规范条目（描述、内容、标签）.

        Args:
            project_id: 项目ID
            standard_id: 规范ID
            description: 新的描述（可选）
            content: 新的规范内容（可选）
            tags: 新的标签列表（可选）

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 确保 standards 列表存在（向后兼容）
        if "standards" not in project_data:
            project_data["standards"] = []

        # 查找指定ID的规范
        standard_index = None
        for i, standard in enumerate(project_data["standards"]):
            if standard.get("id") == standard_id:
                standard_index = i
                break

        if standard_index is None:
            return {"success": False, "error": f"规范ID '{standard_id}' 不存在"}

        # 更新提供的字段
        if description is not None:
            project_data["standards"][standard_index]["description"] = description
        if content is not None:
            project_data["standards"][standard_index]["content"] = content
        if tags is not None:
            project_data["standards"][standard_index]["tags"] = tags

        # 更新条目的 updated_at 字段
        self._update_timestamp(project_data["standards"][standard_index])
        project_data["info"]["updated_at"] = datetime.now().isoformat()

        if self._save_project(project_id, project_data):
            return {
                "success": True,
                "message": f"规范 '{standard_id}' 已更新",
                "standard": project_data["standards"][standard_index]
            }
        return {"success": False, "error": "保存数据失败"}

    def delete_standard(self, project_id: str, standard_id: str) -> Dict[str, Any]:
        """删除规范条目.

        Args:
            project_id: 项目ID
            standard_id: 规范ID

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 确保 standards 列表存在（向后兼容）
        if "standards" not in project_data:
            project_data["standards"] = []

        # 查找并删除指定ID的规范
        for i, standard in enumerate(project_data["standards"]):
            if standard.get("id") == standard_id:
                deleted_standard = project_data["standards"].pop(i)
                project_data["info"]["updated_at"] = datetime.now().isoformat()

                if self._save_project(project_id, project_data):
                    # 获取规范摘要用于消息
                    content_preview = deleted_standard.get("content", "")[:50]
                    if len(deleted_standard.get("content", "")) > 50:
                        content_preview += "..."
                    return {
                        "success": True,
                        "message": f"规范 '{content_preview}' 已删除"
                    }
                return {"success": False, "error": "保存数据失败"}

        return {"success": False, "error": f"规范ID '{standard_id}' 不存在"}

    def add_item_tag(self, project_id: str, group_name: str, item_id: str, tag: str) -> Dict[str, Any]:
        """为条目添加单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/standards)
            item_id: 条目ID
            tag: 要添加的标签

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        # 强制注册检查：标签必须先注册才能使用
        tag_registry = project_data.get("tag_registry", {})
        if tag not in tag_registry:
            return {
                "success": False,
                "error": f"标签 '{tag}' 未注册，请先使用 tag_register 注册该标签"
            }

        items = project_data.get(group_name, [])
        item_index = None

        for i, item in enumerate(items):
            if item.get("id") == item_id:
                item_index = i
                break

        if item_index is None:
            return {"success": False, "error": f"条目ID '{item_id}' 不存在"}

        current_tags = items[item_index].get("tags", [])
        if tag not in current_tags:
            current_tags.append(tag)
            items[item_index]["tags"] = current_tags

            # 更新使用计数
            tag_registry[tag]["usage_count"] = tag_registry[tag].get("usage_count", 0) + 1
            project_data["tag_registry"] = tag_registry

            project_data["info"]["updated_at"] = datetime.now().isoformat()

            if self._save_project(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已为条目 '{item_id}' 添加标签 '{tag}'",
                    "tags": current_tags
                }
            return {"success": False, "error": "保存数据失败"}

        return {"success": True, "message": f"标签 '{tag}' 已存在", "tags": current_tags}

    def remove_item_tag(self, project_id: str, group_name: str, item_id: str, tag: str) -> Dict[str, Any]:
        """从条目移除单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称 (features/notes/standards)
            item_id: 条目ID
            tag: 要移除的标签

        Returns:
            操作结果
        """
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        if group_name not in ["features", "notes", "standards"]:
            return {"success": False, "error": f"分组 '{group_name}' 不存在"}

        items = project_data.get(group_name, [])
        item_index = None

        for i, item in enumerate(items):
            if item.get("id") == item_id:
                item_index = i
                break

        if item_index is None:
            return {"success": False, "error": f"条目ID '{item_id}' 不存在"}

        current_tags = items[item_index].get("tags", [])
        if tag in current_tags:
            current_tags.remove(tag)
            items[item_index]["tags"] = current_tags

            # 更新使用计数
            tag_registry = project_data.get("tag_registry", {})
            if tag in tag_registry:
                current_count = tag_registry[tag].get("usage_count", 0)
                tag_registry[tag]["usage_count"] = max(0, current_count - 1)
                project_data["tag_registry"] = tag_registry

            project_data["info"]["updated_at"] = datetime.now().isoformat()

            if self._save_project(project_id, project_data):
                return {
                    "success": True,
                    "message": f"已从条目 '{item_id}' 移除标签 '{tag}'",
                    "tags": current_tags
                }
            return {"success": False, "error": "保存数据失败"}

        return {"success": True, "message": f"标签 '{tag}' 不存在", "tags": current_tags}

    # ==================== 项目管理 ====================

    def project_rename(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """重命名项目（修改 name 字段并重命名目录）。

        使用安全迁移流程：新建目录→拷贝数据→归档原目录

        Args:
            project_id: 项目 UUID
            new_name: 新的项目名称

        Returns:
            操作结果
        """
        # 加载项目数据
        project_data = self._load_project(project_id)
        if not project_data:
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 获取当前项目名称（目录名）
        old_name = project_data.get("name") or project_data.get("info", {}).get("name")
        if not old_name:
            return {"success": False, "error": "无法获取当前项目名称"}

        # 验证新名称
        if not new_name or not new_name.strip():
            return {"success": False, "error": "新名称不能为空"}

        new_name = new_name.strip()

        # 检查新名称是否已存在
        new_dir_path = self.storage_dir / new_name
        if new_dir_path.exists() and new_dir_path != self.storage_dir / old_name:
            return {"success": False, "error": f"项目名称 '{new_name}' 已存在"}

        # 更新项目数据中的 name 字段
        if "info" in project_data:
            project_data["info"]["name"] = new_name
        else:
            project_data["name"] = new_name

        project_data["info"]["updated_at"] = datetime.now().isoformat()

        # 保存更新后的数据到原目录
        old_dir_path = self.storage_dir / old_name
        project_json_path = old_dir_path / "project.json"

        try:
            with open(project_json_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            return {"success": False, "error": f"保存数据失败: {str(e)}"}

        # 使用安全迁移函数移动目录
        migrate_result = self._safe_migrate_project_dir(
            old_path=old_dir_path,
            new_path=new_dir_path,
            project_name=old_name
        )

        if not migrate_result.get("success"):
            return {
                "success": False,
                "error": f"目录迁移失败: {migrate_result.get('error', '未知错误')}"
            }

        # 删除归档文件（不阻塞）
        archived_path = migrate_result.get("archived_path")
        self._delete_archive_file(archived_path)

        # 清除缓存
        if project_id in self._project_data_cache:
            del self._project_data_cache[project_id]
        if project_id in self._uuid_to_name_cache:
            del self._uuid_to_name_cache[project_id]

        # 刷新缓存
        self._refresh_projects_cache()

        return {
            "success": True,
            "message": f"项目已从 '{old_name}' 重命名为 '{new_name}'",
            "old_name": old_name,
            "new_name": new_name,
            "archived_path": migrate_result.get("archived_path")
        }

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """删除项目（同时清理缓存）.

        Args:
            project_id: 项目ID

        Returns:
            操作结果
        """
        project_path = self._get_project_path(project_id)
        if not project_path.exists():
            return {"success": False, "error": f"项目 '{project_id}' 不存在"}

        # 获取项目名称用于返回消息
        project_data = self._load_project(project_id)
        project_name = project_data["info"]["name"] if project_data else project_id

        try:
            project_path.unlink()
            # 清理缓存
            if project_id in self._projects_cache:
                del self._projects_cache[project_id]
            # 清理 TTL 缓存
            self._project_data_cache.pop(project_id, None)
            self._save_metadata()
            return {
                "success": True,
                "message": f"项目 '{project_name}' (ID: {project_id}) 已删除"
            }
        except IOError:
            return {"success": False, "error": "删除文件失败"}

    # ==================== 导入导出 ====================

    def export_data(self, output_path: str = None) -> Dict[str, Any]:
        """导出所有项目数据.

        Args:
            output_path: 输出文件路径（可选，默认导出到当前目录）

        Returns:
            操作结果
        """
        if output_path is None:
            output_path = Path.cwd() / f"project_memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            output_path = Path(output_path)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 收集所有项目数据
            all_projects = {}
            self._refresh_projects_cache()
            for project_id in self._projects_cache.keys():
                project_data = self._load_project(project_id)
                if project_data:
                    all_projects[project_id] = project_data

            export_data = {
                "projects": all_projects,
                "metadata": {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "total_projects": len(all_projects)
                }
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "message": f"数据已导出到 {output_path}",
                "path": str(output_path)
            }
        except IOError as e:
            return {"success": False, "error": f"导出失败: {str(e)}"}

    def import_data(self, input_path: str, merge: bool = False) -> Dict[str, Any]:
        """导入项目数据.

        Args:
            input_path: 输入文件路径
            merge: 是否合并（True）还是替换（False）

        Returns:
            操作结果
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return {"success": False, "error": f"文件不存在: {input_path}"}

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)

            # 支持旧格式（包含 "projects" 键）和新格式
            if "projects" in imported_data:
                projects_to_import = imported_data["projects"]
            else:
                # 新格式：直接是项目数据字典
                projects_to_import = imported_data

            if merge:
                # 合并模式：添加不存在的项目
                count = 0
                for project_id, project_data in projects_to_import.items():
                    project_file = self._get_project_path(project_id)
                    if not project_file.exists():
                        if self._save_project(project_id, project_data):
                            self._projects_cache[project_id] = project_data["info"]["name"]
                            count += 1

                self._save_metadata()
                return {
                    "success": True,
                    "message": f"已导入 {count} 个新项目（合并模式）"
                }
            else:
                # 替换模式：删除所有现有项目，然后导入
                count = 0
                for existing_file in self.storage_dir.glob("*.json"):
                    if existing_file.name != "_metadata.json":
                        existing_file.unlink()

                self._projects_cache.clear()

                for project_id, project_data in projects_to_import.items():
                    if self._save_project(project_id, project_data):
                        self._projects_cache[project_id] = project_data["info"]["name"]
                        count += 1

                self._save_metadata()
                return {
                    "success": True,
                    "message": f"已导入 {count} 个项目（替换模式）"
                }

        except (json.JSONDecodeError, IOError) as e:
            return {"success": False, "error": f"导入失败: {str(e)}"}

    # ==================== 统计功能 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据
        """
        self._refresh_projects_cache()
        total_projects = len(self._projects_cache)

        # 统计项目级标签
        all_tags = []
        feature_stats = {"pending": 0, "in_progress": 0, "completed": 0}
        total_features = 0
        total_notes = 0

        # 统计条目级标签
        feature_tag_counts = {}
        note_tag_counts = {}

        for project_id in self._projects_cache.keys():
            project_data = self._load_project(project_id)
            if project_data is None:
                continue

            all_tags.extend(project_data["info"]["tags"])

            total_features += len(project_data["features"])
            for feature in project_data["features"]:
                status = feature.get("status", "pending")
                if status in feature_stats:
                    feature_stats[status] += 1

                # 统计功能标签
                for tag in feature.get("tags", []):
                    feature_tag_counts[tag] = feature_tag_counts.get(tag, 0) + 1

            total_notes += len(project_data["notes"])

            # 统计笔记标签
            for note in project_data["notes"]:
                for tag in note.get("tags", []):
                    note_tag_counts[tag] = note_tag_counts.get(tag, 0) + 1

        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "success": True,
            "stats": {
                "total_projects": total_projects,
                "total_features": total_features,
                "total_notes": total_notes,
                "feature_status": feature_stats,
                "top_project_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "top_feature_tags": sorted(feature_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "top_note_tags": sorted(note_tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        }
