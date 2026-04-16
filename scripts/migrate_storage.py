#!/usr/bin/env python3
"""存储格式迁移脚本 - 将旧格式迁移到拆分文件格式.

旧格式：project.json 包含所有数据
新格式：_project.json + _tags.json + {group}/_index.json

用法：
    python scripts/migrate_storage.py                    # 迁移所有项目
    python scripts/migrate_storage.py --project ai_memory_mcp  # 迁移指定项目
"""

import argparse
import json
import shutil
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class StorageMigrator:
    """存储格式迁移器."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list:
        """列出所有需要迁移的项目."""
        projects = []
        for project_dir in self.storage_dir.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                project_json = project_dir / "_project.json"
                old_json = project_dir / "project.json"
                # 如果 _project.json 不存在但 project.json 存在，需要迁移
                if not project_json.exists() and old_json.exists():
                    projects.append(project_dir.name)
        return projects

    def migrate_project(self, project_name: str) -> dict:
        """迁移单个项目.

        Returns:
            {"success": bool, "message": str, "archived_path": str}
        """
        project_dir = self.storage_dir / project_name
        old_json_path = project_dir / "project.json"
        backup_path = self.storage_dir / f"{project_name}.json.bak"

        if not old_json_path.exists():
            return {"success": False, "error": f"旧文件不存在: {old_json_path}"}

        # 检查是否已经迁移过
        if (project_dir / "_project.json").exists():
            return {"success": False, "error": "已经迁移过，_project.json 已存在"}

        try:
            # 1. 读取旧数据
            with open(old_json_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            # 2. 备份原文件
            shutil.copy2(old_json_path, backup_path)
            print(f"  ✓ 备份到: {backup_path}")

            # 3. 提取并保存元数据到 _project.json
            meta_data = {
                "id": old_data.get("id"),
                "name": old_data.get("name"),
                "info": old_data.get("info", {}),
                "_version": old_data.get("_version", 1),
                "_versions": old_data.get("_versions", {}),
                "_group_configs": old_data.get("_group_configs"),
            }

            # 提取项目名称和ID到 info（如果缺失）
            if "info" in meta_data and meta_data["info"]:
                if not meta_data["info"].get("id") and meta_data["id"]:
                    meta_data["info"]["id"] = meta_data["id"]
                if not meta_data["info"].get("name") and meta_data["name"]:
                    meta_data["info"]["name"] = meta_data["name"]

            meta_path = project_dir / "_project.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 创建: _project.json")

            # 4. 提取并保存标签到 _tags.json
            tag_registry = old_data.get("tag_registry", {})
            tags_data = {
                "_version": old_data.get("_versions", {}).get("tag_registry", 1),
                "tags": tag_registry
            }

            tags_path = project_dir / "_tags.json"
            with open(tags_path, "w", encoding="utf-8") as f:
                json.dump(tags_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 创建: _tags.json")

            # 5. 保存各分组的 _index.json
            CONTENT_SEPARATE_GROUPS = ["features", "fixes", "notes", "standards"]
            for group_name in CONTENT_SEPARATE_GROUPS:
                items = old_data.get(group_name, [])

                # 确保 _versions 中有该分组的版本号
                group_version = old_data.get("_versions", {}).get(group_name, 1)

                index_data = {
                    "_version": group_version,
                    "items": []
                }

                group_dir = project_dir / group_name
                group_dir.mkdir(exist_ok=True)

                for item in items:
                    # 提取除 content 外的所有字段
                    item_summary = {k: v for k, v in item.items() if k != "content"}
                    index_data["items"].append(item_summary)

                    # 如果有 content，保存到独立文件
                    if "content" in item and item["content"]:
                        content_path = group_dir / f"{item['id']}.md"
                        with open(content_path, "w", encoding="utf-8") as f:
                            f.write(item["content"])

                if index_data["items"] or group_dir.exists():
                    index_path = group_dir / "_index.json"
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index_data, f, ensure_ascii=False, indent=2)
                    print(f"  ✓ 创建: {group_name}/_index.json ({len(index_data['items'])} items)")

            # 6. 验证迁移结果
            if not meta_path.exists():
                return {"success": False, "error": "_project.json 未创建"}

            # 7. 归档原文件
            archive_dir = self.storage_dir / ".archived"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{timestamp}_{project_name}.json"
            archived_path = archive_dir / archive_name

            shutil.move(str(old_json_path), str(archived_path))
            print(f"  ✓ 归档: {archive_name}")

            # 8. 删除备份文件
            if backup_path.exists():
                backup_path.unlink()

            return {
                "success": True,
                "message": f"项目 '{project_name}' 迁移成功",
                "archived_path": str(archived_path)
            }

        except Exception as e:
            # 失败时回滚：恢复备份
            if backup_path.exists():
                try:
                    if old_json_path.exists():
                        old_json_path.unlink()
                    shutil.copy2(backup_path, old_json_path)

                    # 删除已创建的新格式文件
                    for file_name in ["_project.json", "_tags.json"]:
                        file_path = project_dir / file_name
                        if file_path.exists():
                            file_path.unlink()

                    for group_name in ["features", "fixes", "notes", "standards"]:
                        index_path = project_dir / group_name / "_index.json"
                        if index_path.exists():
                            index_path.unlink()
                except:
                    pass

            return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="迁移存储格式")
    parser.add_argument(
        "--storage-dir",
        default="~/.project_memory_ai",
        help="存储目录路径"
    )
    parser.add_argument(
        "--project",
        help="指定要迁移的项目名称（不指定则迁移所有项目）"
    )

    args = parser.parse_args()
    storage_dir = Path(args.storage_dir).expanduser()

    migrator = StorageMigrator(str(storage_dir))

    if args.project:
        # 迁移单个项目
        print(f"迁移项目: {args.project}")
        result = migrator.migrate_project(args.project)
        if result.get("success"):
            print(f"✅ {result['message']}")
        else:
            print(f"❌ 迁移失败: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # 迁移所有项目
        projects = migrator.list_projects()
        if not projects:
            print("没有需要迁移的项目")
            return

        print(f"找到 {len(projects)} 个需要迁移的项目:")
        for p in projects:
            print(f"  - {p}")

        print("\n开始迁移...")
        success_count = 0
        fail_count = 0

        for project_name in projects:
            print(f"\n迁移: {project_name}")
            result = migrator.migrate_project(project_name)
            if result.get("success"):
                print(f"✅ {result['message']}")
                success_count += 1
            else:
                print(f"❌ 迁移失败: {result.get('error', 'Unknown error')}")
                fail_count += 1

        print(f"\n迁移完成: {success_count} 成功, {fail_count} 失败")

        if fail_count > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
