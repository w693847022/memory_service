"""ProjectStorage Module - 项目存储层抽象.

提取 ProjectMemory 的基础方法，包括：
- 初始化、存储路径、缓存
- 数据加载和保存（异步）
- 迁移逻辑
- UUID 验证和 ID 生成
"""

import json
import tarfile
import time
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from cachetools import TTLCache
import aiofiles

from business.core.barrier_manager import BarrierManager
from business.core.smart_cache import SmartCache, CacheConfig, CacheLevel

# TTL 缓存配置
CACHE_TTL_SECONDS = 300
CACHE_MAX_SIZE = 50

# 已知分组（用于版本迁移补全）
KNOWN_GROUPS = ["features", "fixes", "notes", "standards"]


class ProjectStorage:
    """项目存储管理类 - 异步存储层."""

    def __init__(self, storage_dir: Union[str, Path, None] = None, barrier_manager: Optional[BarrierManager] = None):
        """初始化项目存储管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
            barrier_manager: 阻挡位管理器实例
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".project_memory_ai"
        else:
            storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 阻挡位管理器
        self._barrier = barrier_manager or BarrierManager()

        # 元数据文件
        self.metadata_path = self.storage_dir / "_metadata.json"
        self.metadata = None  # 延迟加载，在首次 async 调用中初始化
        self._metadata_loaded = False

        # 项目列表缓存 (ID -> Name)
        self._projects_cache: Dict[str, str] = {}

        # 多级缓存系统
        self._cache = SmartCache(config=CacheConfig())
        # 兼容性：保留原有接口
        self._project_data_cache = self._cache.l2_cache

        # UUID -> 项目名称映射缓存 (用于反向查找)
        self._uuid_to_name_cache = TTLCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL_SECONDS,
            timer=time.time
        )

    async def _ensure_metadata(self) -> Dict[str, Any]:
        """确保元数据已加载."""
        if not self._metadata_loaded:
            self.metadata = await self._load_metadata()
            self._metadata_loaded = True
        return self.metadata  # type: ignore[return-value]

    # ==================== 版本迁移 ====================

    @staticmethod
    def _ensure_versions(data: Dict[str, Any]) -> None:
        """确保项目数据包含完整的版本结构（原地修改）."""
        if "_version" not in data:
            data["_version"] = 1
        if "_versions" not in data:
            data["_versions"] = {}
        v = data["_versions"]
        v.setdefault("project", 1)
        v.setdefault("tag_registry", 1)
        for group_name in KNOWN_GROUPS:
            v.setdefault(group_name, 1)
        if "_group_configs" in data:
            data["_group_configs"].setdefault("_v", 1)

    def _get_project_path(self, project_id: str) -> Path:
        """获取项目文件路径（向后兼容旧格式）."""
        return self.storage_dir / f"{project_id}.json"

    def _get_project_dir(self, project_id: str) -> Path:
        """获取项目目录路径（按项目名称存储）.

        支持两种查找方式：
        1. 如果 project_id 是项目名称（目录名），直接使用
        2. 如果 project_id 是 UUID，查找对应的项目名称作为目录名
        """
        if "-" in project_id and len(project_id) > 20:
            project_name = self._find_project_name_by_uuid(project_id)
            if project_name:
                name_dir = self.storage_dir / project_name
                if name_dir.exists():
                    return name_dir
                uuid_dir = self.storage_dir / project_id
                if uuid_dir.exists():
                    try:
                        uuid_dir.rename(name_dir)
                        return name_dir
                    except OSError:
                        return uuid_dir
                return name_dir
            return self.storage_dir / project_id
        return self.storage_dir / project_id

    def _get_project_json_path(self, project_id: str) -> Path:
        """获取 project.json 文件路径."""
        return self._get_project_dir(project_id) / "project.json"

    def _get_group_content_dir(self, project_id: str, group_name: str) -> Path:
        """获取组的 content 目录路径."""
        content_dir = self._get_project_dir(project_id) / group_name
        content_dir.mkdir(parents=True, exist_ok=True)
        return content_dir

    def _get_item_content_path(self, project_id: str, group_name: str, item_id: str) -> Path:
        """获取单个条目的 .md 文件路径."""
        return self._get_group_content_dir(project_id, group_name) / f"{item_id}.md"

    # ==================== 异步文件 IO ====================

    async def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据文件."""
        if self.metadata_path.exists():
            try:
                async with aiofiles.open(self.metadata_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                return json.loads(content)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_projects": 0
        }

    async def _save_metadata(self) -> bool:
        """保存元数据文件."""
        if self.metadata is None:
            return False
        try:
            self.metadata["total_projects"] = len(self._projects_cache)
            async with self._barrier.io_operation():
                async with aiofiles.open(self.metadata_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(self.metadata, ensure_ascii=False, indent=2))
            return True
        except IOError:
            return False

    async def _load_item_content(self, project_id: str, group_name: str, item_id: str) -> Optional[str]:
        """加载单个条目的 content."""
        content_path = self._get_item_content_path(project_id, group_name, item_id)
        if content_path.exists():
            try:
                async with aiofiles.open(content_path, "r", encoding="utf-8") as f:
                    return await f.read()
            except IOError:
                return None
        return None

    async def _save_item_content(self, project_id: str, group_name: str, item_id: str, content: str) -> bool:
        """保存单个条目的 content."""
        try:
            content_path = self._get_item_content_path(project_id, group_name, item_id)
            content_path.parent.mkdir(parents=True, exist_ok=True)
            async with self._barrier.io_operation():
                async with aiofiles.open(content_path, "w", encoding="utf-8") as f:
                    await f.write(content)
            return True
        except IOError:
            return False

    def _delete_item_content(self, project_id: str, group_name: str, item_id: str) -> bool:
        """删除单个条目的 content 文件（同步，仅 unlink）."""
        try:
            content_path = self._get_item_content_path(project_id, group_name, item_id)
            if content_path.exists():
                content_path.unlink()
            return True
        except IOError:
            return False

    async def _migrate_project_storage(self, project_id: str) -> bool:
        """迁移单个项目的存储结构（旧格式 -> 新格式）.

        使用安全迁移流程：新建目录→拷贝数据→归档原文件
        """
        old_path = self.storage_dir / f"{project_id}.json"

        if not old_path.exists():
            return True

        new_dir = self._get_project_dir(project_id)
        new_json_path = self._get_project_json_path(project_id)

        if new_json_path.exists():
            return True

        temp_dir = self.storage_dir / f".temp_{project_id}"

        try:
            # 1. 读取旧数据
            async with aiofiles.open(old_path, "r", encoding="utf-8") as f:
                content = await f.read()
            data = json.loads(content)

            # 2. 迁移 content 到独立 .md 文件
            from business.core.groups import CONTENT_SEPARATE_GROUPS
            for group_name in CONTENT_SEPARATE_GROUPS:
                for item in data.get(group_name, []):
                    if "content" in item and item["content"]:
                        await self._save_item_content(project_id, group_name, item["id"], item["content"])
                        del item["content"]

            # 3. 创建临时目录并保存新的 project.json
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_json_path = temp_dir / "project.json"
            async with self._barrier.io_operation():
                async with aiofiles.open(temp_json_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))

            # 4. 拷贝已有组的 content 目录
            for group_name in CONTENT_SEPARATE_GROUPS:
                existing_dir = new_dir / group_name
                if existing_dir.exists():
                    temp_group_dir = temp_dir / group_name
                    shutil.copytree(existing_dir, temp_group_dir, copy_function=shutil.copy2)

            # 5. 将临时目录移动到最终位置
            temp_dir.rename(new_dir)

            # 6. 归档原文件
            archive_dir = self.storage_dir / ".archived"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{timestamp}_{project_id}.json"
            archived_path = archive_dir / archive_name

            old_path.rename(archived_path)

            return True

        except (json.JSONDecodeError, IOError, OSError):
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except OSError:
                    pass
            return False

    async def _load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载单个项目数据（带向后兼容和缓存）."""
        # 快速路径：多级缓存查询
        cached_data = self._cache.get(project_id)
        if cached_data is not None:
            return cached_data

        # 从磁盘加载
        new_json_path = self._get_project_json_path(project_id)
        old_path = self._get_project_path(project_id)

        project_path = None
        if new_json_path.exists():
            project_path = new_json_path
        elif old_path.exists():
            if await self._migrate_project_storage(project_id):
                project_path = new_json_path
            else:
                project_path = old_path

        if project_path and project_path.exists():
            try:
                async with aiofiles.open(project_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                data = json.loads(content)

                # 向后兼容处理
                for note in data.get("notes", []):
                    if "summary" not in note:
                        note["summary"] = ""

                # 兼容旧格式：将内联 content 迁移到独立文件
                from business.core.groups import CONTENT_SEPARATE_GROUPS
                need_save = False
                for group_name in CONTENT_SEPARATE_GROUPS:
                    for item in data.get(group_name, []):
                        if "content" in item and item["content"]:
                            await self._save_item_content(project_id, group_name, item["id"], item["content"])
                            del item["content"]
                            need_save = True
                if need_save:
                    project_json_path = self._get_project_json_path(project_id)
                    async with self._barrier.io_operation():
                        async with aiofiles.open(project_json_path, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

                if "tag_registry" not in data:
                    data["tag_registry"] = {}

                if "fixes" not in data:
                    data["fixes"] = []

                # 版本控制迁移
                migrated = self._migrate_to_version_control(project_id, data)
                if migrated:
                    project_json_path = self._get_project_json_path(project_id)
                    async with self._barrier.io_operation():
                        async with aiofiles.open(project_json_path, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

                # 补全版本结构
                self._ensure_versions(data)

                # 存入多级缓存
                self._cache.set(project_id, data, CacheLevel.L2_WARM)

                return data
            except (json.JSONDecodeError, IOError):
                return None
        return None

    async def _save_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """保存单个项目数据（write-through 缓存）.

        注意：所有默认组的 content 字段不写入 JSON，而是单独保存为 .md 文件
        """
        try:
            # 确保项目目录存在
            project_dir = self._get_project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)

            # 确保所有默认组的 content 目录存在
            from business.core.groups import CONTENT_SEPARATE_GROUPS
            for group_name in CONTENT_SEPARATE_GROUPS:
                self._get_group_content_dir(project_id, group_name)

            # 复制数据，移除所有默认组中的 content 字段
            save_data = project_data.copy()
            for group_name in CONTENT_SEPARATE_GROUPS:
                if group_name in save_data:
                    save_data[group_name] = [
                        {k: v for k, v in item.items() if k != "content"}
                        for item in save_data[group_name]
                    ]

            # 保存 project.json
            project_json_path = self._get_project_json_path(project_id)
            async with self._barrier.io_operation():
                async with aiofiles.open(project_json_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(save_data, ensure_ascii=False, indent=2))

            # 更新多级缓存 (write-through)
            self._cache.set(project_id, project_data, CacheLevel.L2_WARM)

            return True
        except IOError:
            return False

    # ==================== 组配置存储 ====================

    def _get_group_config_path(self, project_id: str) -> Path:
        """获取组配置文件路径."""
        project_dir = self._get_project_dir(project_id)
        return project_dir / "_group_configs.json"

    async def _load_group_configs(self, project_id: str) -> Dict[str, Any]:
        """加载组配置文件."""
        from business.core.groups import UnifiedGroupConfig, DEFAULT_GROUP_CONFIGS, DEFAULT_RELATED_RULES

        config_path = self._get_group_config_path(project_id)
        if config_path.exists():
            try:
                async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                raw_configs = json.loads(content)

                if "groups" in raw_configs:
                    groups = {}
                    for group_name, group_config in raw_configs["groups"].items():
                        if isinstance(group_config, dict):
                            groups[group_name] = UnifiedGroupConfig.from_dict(group_config)
                        else:
                            groups[group_name] = group_config
                    raw_configs["groups"] = groups

                return raw_configs
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "groups": {name: UnifiedGroupConfig.from_dict(cfg) for name, cfg in DEFAULT_GROUP_CONFIGS.items()},
            "group_settings": {
                "default_related_rules": DEFAULT_RELATED_RULES
            }
        }

    async def _save_group_configs(self, project_id: str, configs: Dict[str, Any]) -> bool:
        """保存组配置文件."""
        try:
            config_path = self._get_group_config_path(project_id)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            save_configs = self._serialize_group_configs(configs)

            async with self._barrier.io_operation():
                async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(save_configs, ensure_ascii=False, indent=2))
            return True
        except IOError:
            return False

    def _serialize_group_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """将组配置中的 dataclass 转换为字典."""
        from business.core.groups import UnifiedGroupConfig

        result = {}
        for key, value in configs.items():
            if key == "groups" and isinstance(value, dict):
                result[key] = {}
                for group_name, group_config in value.items():
                    if isinstance(group_config, UnifiedGroupConfig):
                        result[key][group_name] = group_config.to_dict()
                    elif isinstance(group_config, dict):
                        result[key][group_name] = group_config
            elif isinstance(value, dict):
                result[key] = self._serialize_group_configs(value)
            else:
                result[key] = value
        return result

    async def _refresh_projects_cache(self):
        """刷新项目缓存（支持新旧格式）."""
        self._projects_cache = {}
        self._uuid_to_name_cache = {}

        # 检查旧格式：*.json 文件
        for file_path in self.storage_dir.glob("*.json"):
            if file_path.name not in ["_metadata.json", "_stats.json"]:
                project_id = file_path.stem
                project_data = await self._load_project(project_id)
                if project_data and "info" in project_data:
                    name = project_data["info"].get("name", project_id)
                    self._projects_cache[project_id] = name
                    uuid_val = project_data.get("id") or project_data["info"].get("id")
                    if uuid_val:
                        self._uuid_to_name_cache[uuid_val] = name

        # 检查新格式：目录下的 project.json
        for project_dir in self.storage_dir.iterdir():
            if project_dir.is_dir():
                project_json = project_dir / "project.json"
                if project_json.exists():
                    project_name = project_dir.name
                    project_data = await self._load_project(project_name)
                    if project_data:
                        uuid_val = project_data.get("id") or project_data.get("info", {}).get("id")
                        name = project_data.get("name") or project_data.get("info", {}).get("name", project_name)

                        if uuid_val:
                            self._projects_cache[uuid_val] = name
                            self._uuid_to_name_cache[uuid_val] = name
                        else:
                            self._projects_cache[project_name] = name

    def _generate_timestamps(self) -> Dict[str, str]:
        """生成创建和更新时间戳字典."""
        now = datetime.now().isoformat()
        return {"created_at": now, "updated_at": now}

    def _update_timestamp(self, item: Dict[str, Any]) -> None:
        """更新条目的 updated_at 字段."""
        item["updated_at"] = datetime.now().isoformat()

    # ==================== UUID 验证 ====================

    def _is_valid_uuid(self, id_str: str) -> bool:
        """验证字符串是否为有效的 UUID v4 格式."""
        UUID_V4_PATTERN = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(UUID_V4_PATTERN.match(id_str))

    # ==================== 项目ID生成 ====================

    def _generate_id(self, name: str) -> str:
        """生成项目ID - 使用 UUID."""
        import uuid
        return str(uuid.uuid4())

    # ==================== 安全目录迁移 ====================

    def _safe_migrate_project_dir(
        self,
        old_path: Path,
        new_path: Path,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """安全迁移项目目录：新建→拷贝→归档。"""
        if new_path.exists():
            return {"success": False, "error": f"目标目录已存在: {new_path}"}

        if not old_path.exists():
            return {"success": False, "error": f"原目录不存在: {old_path}"}

        temp_new_path = None

        try:
            shutil.copytree(old_path, new_path, copy_function=shutil.copy2)
            temp_new_path = new_path

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
            if temp_new_path and temp_new_path.exists():
                try:
                    shutil.rmtree(temp_new_path)
                except OSError:
                    pass

            return {"success": False, "error": f"目录迁移失败: {str(e)}"}

    def _delete_archive_file(self, archived_path: Optional[str]) -> bool:
        """删除归档文件."""
        if not archived_path:
            return False

        archive_path = Path(archived_path)
        if not archive_path.exists():
            return True

        try:
            if archive_path.is_dir():
                shutil.rmtree(archive_path)
            else:
                archive_path.unlink()
            return True
        except OSError:
            return False

    # ==================== 归档管理 ====================

    def _get_archive_dir(self) -> Path:
        """获取归档目录路径."""
        archive_dir = self.storage_dir / ".archived"
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    async def _compress_and_archive_project(self, project_id: str) -> Dict[str, Any]:
        """压缩项目目录为 tar.gz 并移动到 .archived/."""
        project_dir = self._get_project_dir(project_id)
        if not project_dir.exists():
            return {"success": False, "error": f"项目目录不存在: {project_dir}"}

        project_data = await self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"无法加载项目数据: {project_id}"}

        project_name = project_data["info"].get("name", project_dir.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_base_name = f"{timestamp}_{project_name}"

        archive_dir = self._get_archive_dir()
        archive_file = archive_dir / f"{archive_base_name}.tar.gz"
        meta_file = archive_dir / f"{archive_base_name}_meta.json"

        try:
            with tarfile.open(str(archive_file), "w:gz") as tar:
                tar.add(str(project_dir), arcname=project_dir.name)

            meta_data = {
                "id": project_data.get("id") or project_data["info"].get("id", project_id),
                "name": project_name,
                "summary": project_data["info"].get("summary", ""),
                "tags": project_data["info"].get("tags", []),
                "archived_at": datetime.now().isoformat(),
                "archive_file": archive_file.name
            }
            async with self._barrier.io_operation():
                async with aiofiles.open(meta_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(meta_data, ensure_ascii=False, indent=2))

            shutil.rmtree(project_dir)

            return {
                "success": True,
                "message": f"项目 '{project_name}' 已归档",
                "archive_path": str(archive_file),
                "meta_path": str(meta_file)
            }
        except (OSError, tarfile.TarError) as e:
            for f in [archive_file, meta_file]:
                if f.exists():
                    try:
                        f.unlink()
                    except OSError:
                        pass
            return {"success": False, "error": f"归档失败: {str(e)}"}

    async def _is_project_archived(self, project_id: str) -> bool:
        """检查项目是否已归档."""
        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return False

        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                meta_data = json.loads(content)
                if meta_data.get("id") == project_id:
                    return True
            except (json.JSONDecodeError, IOError):
                continue
        return False

    async def _get_archived_projects(self) -> List[Dict[str, Any]]:
        """从 .archived/ 目录读取所有归档项目的元数据."""
        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return []

        archived = []
        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                meta_data = json.loads(content)
                archived.append(meta_data)
            except (json.JSONDecodeError, IOError):
                continue
        return archived

    async def _delete_archived_project(self, project_id: str) -> bool:
        """删除归档的 tar.gz 和 _meta.json 文件."""
        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return True

        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                meta_data = json.loads(content)
                if meta_data.get("id") == project_id:
                    archive_file = archive_dir / meta_data["archive_file"]
                    if archive_file.exists():
                        archive_file.unlink()
                    meta_file.unlink()
                    return True
            except (json.JSONDecodeError, IOError):
                continue
        return False

    def _find_project_name_by_uuid(self, uuid_str: str) -> Optional[str]:
        """通过 UUID 查找项目名称（目录名）."""
        if uuid_str in self._uuid_to_name_cache:
            return self._uuid_to_name_cache[uuid_str]

        for project_dir in self.storage_dir.iterdir():
            if project_dir.is_dir():
                project_json = project_dir / "project.json"
                if project_json.exists():
                    try:
                        with open(project_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            project_id = data.get("id") or data.get("info", {}).get("id")
                            if project_id == uuid_str:
                                project_name = data.get("name") or data.get("info", {}).get("name", project_dir.name)
                                self._uuid_to_name_cache[uuid_str] = project_name
                                return project_name
                    except (json.JSONDecodeError, IOError):
                        continue

        return None

    def _generate_item_id(self, prefix: str, project_id: Optional[str] = None, project_data: Optional[Dict] = None) -> str:
        """生成条目唯一ID."""
        date_str = datetime.now().strftime("%Y%m%d")
        max_counter = 0

        if project_id:
            if project_data is None:
                # 注意: 这里不能异步加载，调用方应传入 project_data
                pass
            if project_data:
                prefix_to_list = {
                    "feat": "features",
                    "note": "notes",
                    "fix": "fixes",
                    "std": "standards"
                }
                items_list = prefix_to_list.get(prefix, "features")

                prefix_with_date = f"{prefix}_{date_str}_"
                for item in project_data.get(items_list, []):
                    item_id = item.get("id", "")
                    if item_id.startswith(prefix_with_date):
                        try:
                            counter_str = item_id[len(prefix_with_date):]
                            counter = int(counter_str)
                            max_counter = max(max_counter, counter)
                        except (ValueError, IndexError):
                            continue

        return f"{prefix}_{date_str}_{max_counter + 1}"

    def _migrate_to_version_control(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """迁移项目数据到版本控制结构（为所有条目添加 version 字段）."""
        need_save = False
        default_groups = ["features", "fixes", "notes", "standards"]

        for group_name in default_groups:
            for item in project_data.get(group_name, []):
                if "version" not in item:
                    item["version"] = 1
                    need_save = True

        return need_save

    # ==================== 缓存访问方法 ====================

    @property
    def projects_cache(self) -> Dict[str, str]:
        """获取项目缓存."""
        return self._projects_cache

    @property
    def project_data_cache(self):
        """获取项目数据缓存."""
        return self._project_data_cache

    @property
    def uuid_to_name_cache(self) -> TTLCache:
        """获取 UUID 到名称的缓存."""
        return self._uuid_to_name_cache

    @property
    def barrier(self) -> BarrierManager:
        """获取阻挡位管理器."""
        return self._barrier

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息.

        Returns:
            包含缓存统计的字典
        """
        stats = self._cache.get_stats()
        return {
            "hit_rate": f"{stats.hit_rate:.2%}",
            "l1_hits": stats.l1_hits,
            "l2_hits": stats.l2_hits,
            "l3_hits": stats.l3_hits,
            "total_misses": stats.l1_misses + stats.l2_misses + stats.l3_misses,
            "promotions": stats.promotions,
            "l1_size": len(self._cache.l1_cache),
            "l2_size": len(self._cache.l2_cache),
            "l3_size": len(self._cache.l3_cache),
        }
