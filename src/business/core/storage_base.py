"""ProjectStorage Module - 项目存储层抽象.

提取 ProjectMemory 的基础方法，包括：
- 初始化、存储路径、缓存
- 数据加载和保存
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
import threading
from datetime import datetime, timedelta

# TTL 缓存配置
CACHE_TTL_SECONDS = 300
CACHE_MAX_SIZE = 50


class ProjectStorage:
    """项目存储管理类 - 提取基础存储层."""

    def __init__(self, storage_dir: Union[str, Path, None] = None):
        """初始化项目存储管理器.

        Args:
            storage_dir: 存储目录路径，默认为 ~/.project_memory_ai/
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".project_memory_ai"
        else:
            storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
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
        """获取项目目录路径（按项目名称存储）.

        支持两种查找方式：
        1. 如果 project_id 是项目名称（目录名），直接使用
        2. 如果 project_id 是 UUID，查找对应的项目名称作为目录名
        """
        # 检查是否为 UUID 格式（简单判断：包含连字符且长度较长）
        if "-" in project_id and len(project_id) > 20:
            # UUID 格式：查找对应的项目名称
            project_name = self._find_project_name_by_uuid(project_id)
            if project_name:
                name_dir = self.storage_dir / project_name
                if name_dir.exists():
                    return name_dir
                # 名称目录不存在，检查 UUID 目录是否存在并迁移
                uuid_dir = self.storage_dir / project_id
                if uuid_dir.exists():
                    # 自动迁移 UUID 目录到名称目录
                    try:
                        uuid_dir.rename(name_dir)
                        return name_dir
                    except OSError:
                        # 迁移失败，返回原 UUID 目录
                        return uuid_dir
                # 新项目，使用名称目录
                return name_dir
            # 无法找到名称，使用 UUID 作为后备
            return self.storage_dir / project_id

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

        except (json.JSONDecodeError, IOError, OSError):
            # 失败清理：删除临时目录，保留原文件
            if temp_dir.exists():
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
                    if "summary" not in note:
                        note["summary"] = ""
                    # 新格式不包含 content 字段，确保不存在
                    if "content" in note:
                        del note["content"]

                # 向后兼容：为没有tag_registry的项目添加空注册表
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

    # ==================== 组配置存储 ====================

    def _get_group_config_path(self, project_id: str) -> Path:
        """获取组配置文件路径.

        Args:
            project_id: 项目ID

        Returns:
            组配置文件路径
        """
        project_dir = self._get_project_dir(project_id)
        return project_dir / "_group_configs.json"

    def _load_group_configs(self, project_id: str) -> Dict[str, Any]:
        """加载组配置文件.

        Args:
            project_id: 项目ID

        Returns:
            组配置字典，groups 值为 UnifiedGroupConfig 数据类对象
        """
        from business.core.groups import UnifiedGroupConfig, DEFAULT_GROUP_CONFIGS, DEFAULT_RELATED_RULES

        config_path = self._get_group_config_path(project_id)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_configs = json.load(f)

                # 转换为 UnifiedGroupConfig 数据类
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

        # 初始化默认配置（包含内置组）
        return {
            "groups": {name: UnifiedGroupConfig.from_dict(cfg) for name, cfg in DEFAULT_GROUP_CONFIGS.items()},
            "group_settings": {
                "default_related_rules": DEFAULT_RELATED_RULES
            }
        }

    def _save_group_configs(self, project_id: str, configs: Dict[str, Any]) -> bool:
        """保存组配置文件.

        Args:
            project_id: 项目ID
            configs: 组配置字典

        Returns:
            是否保存成功
        """
        try:
            config_path = self._get_group_config_path(project_id)
            # 确保项目目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 将 dataclass 转换为字典以便 JSON 序列化
            save_configs = self._serialize_group_configs(configs)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(save_configs, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def _serialize_group_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """将组配置中的 dataclass 转换为字典.

        Args:
            configs: 组配置字典

        Returns:
            可序列化的配置字典
        """
        from business.core.groups import UnifiedGroupConfig

        result = {}
        for key, value in configs.items():
            if key == "groups" and isinstance(value, dict):
                # 转换所有组配置（内置+自定义）
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
        project_name: Optional[str] = None
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

    def _delete_archive_file(self, archived_path: Optional[str]) -> bool:
        """删除归档文件（不阻塞）。

        重命名成功后自动删除归档文件，删除失败不影响重命名结果。

        Args:
            archived_path: 归档文件完整路径

        Returns:
            是否删除成功
        """
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

    # ==================== 归档管理 ====================

    def _get_archive_dir(self) -> Path:
        """获取归档目录路径."""
        archive_dir = self.storage_dir / ".archived"
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    def _compress_and_archive_project(self, project_id: str) -> Dict[str, Any]:
        """压缩项目目录为 tar.gz 并移动到 .archived/，同时生成元数据文件.

        Args:
            project_id: 项目ID

        Returns:
            操作结果，包含 archive_path 和 meta_path
        """
        project_dir = self._get_project_dir(project_id)
        if not project_dir.exists():
            return {"success": False, "error": f"项目目录不存在: {project_dir}"}

        # 读取项目信息用于元数据和命名
        project_data = self._load_project(project_id)
        if project_data is None:
            return {"success": False, "error": f"无法加载项目数据: {project_id}"}

        project_name = project_data["info"].get("name", project_dir.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_base_name = f"{timestamp}_{project_name}"

        archive_dir = self._get_archive_dir()
        archive_file = archive_dir / f"{archive_base_name}.tar.gz"
        meta_file = archive_dir / f"{archive_base_name}_meta.json"

        try:
            # 压缩项目目录为 tar.gz
            with tarfile.open(str(archive_file), "w:gz") as tar:
                tar.add(str(project_dir), arcname=project_dir.name)

            # 生成元数据文件
            meta_data = {
                "id": project_data.get("id") or project_data["info"].get("id", project_id),
                "name": project_name,
                "summary": project_data["info"].get("summary", ""),
                "tags": project_data["info"].get("tags", []),
                "archived_at": datetime.now().isoformat(),
                "archive_file": archive_file.name
            }
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)

            # 删除原项目目录
            shutil.rmtree(project_dir)

            return {
                "success": True,
                "message": f"项目 '{project_name}' 已归档",
                "archive_path": str(archive_file),
                "meta_path": str(meta_file)
            }
        except (OSError, tarfile.TarError) as e:
            # 清理可能残留的文件
            for f in [archive_file, meta_file]:
                if f.exists():
                    try:
                        f.unlink()
                    except OSError:
                        pass
            return {"success": False, "error": f"归档失败: {str(e)}"}

    def _is_project_archived(self, project_id: str) -> bool:
        """检查项目是否已归档（在 .archived/ 中查找 _meta.json）.

        Args:
            project_id: 项目ID

        Returns:
            是否已归档
        """
        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return False

        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                if meta_data.get("id") == project_id:
                    return True
            except (json.JSONDecodeError, IOError):
                continue
        return False

    def _get_archived_projects(self) -> List[Dict[str, Any]]:
        """从 .archived/ 目录读取所有归档项目的元数据.

        Returns:
            归档项目元数据列表
        """
        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return []

        archived = []
        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                archived.append(meta_data)
            except (json.JSONDecodeError, IOError):
                continue
        return archived

    def _delete_archived_project(self, project_id: str) -> bool:
        """删除归档的 tar.gz 和 _meta.json 文件.

        Args:
            project_id: 项目ID

        Returns:
            是否删除成功
        """
        import logging

        archive_dir = self.storage_dir / ".archived"
        if not archive_dir.exists():
            return True

        for meta_file in archive_dir.glob("*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                if meta_data.get("id") == project_id:
                    archive_file = archive_dir / meta_data["archive_file"]
                    # 删除 tar.gz
                    if archive_file.exists():
                        archive_file.unlink()
                    # 删除 meta.json
                    meta_file.unlink()
                    return True
            except (json.JSONDecodeError, IOError):
                continue
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

    def _generate_item_id(self, prefix: str, project_id: Optional[str] = None, project_data: Optional[Dict] = None) -> str:
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

    # ==================== 缓存访问方法（供子类使用）====================

    @property
    def projects_cache(self) -> Dict[str, str]:
        """获取项目缓存."""
        return self._projects_cache

    @property
    def project_data_cache(self) -> TTLCache:
        """获取项目数据缓存."""
        return self._project_data_cache

    @property
    def uuid_to_name_cache(self) -> TTLCache:
        """获取 UUID 到名称的缓存."""
        return self._uuid_to_name_cache

