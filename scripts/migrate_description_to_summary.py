#!/usr/bin/env python
"""数据迁移脚本: description -> summary 字段重命名

此脚本将所有已存储项目数据中的 description 字段重命名为 summary。

使用方法:
    python scripts/migrate_description_to_summary.py [--dry-run]

--dry-run: 仅显示将要修改的内容，不实际执行修改
"""

import argparse
import json
import os
from pathlib import Path


def migrate_project_file(project_path: Path, dry_run: bool = False) -> dict:
    """迁移单个项目文件。

    Args:
        project_path: project.json 文件路径
        dry_run: 是否仅预览不执行

    Returns:
        迁移统计信息
    """
    stats = {
        "description_to_summary": 0,
        "errors": []
    }

    try:
        with open(project_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        modified = False

        # 迁移 info.description -> info.summary
        if "info" in data and "description" in data["info"]:
            if dry_run:
                print(f"  [DRY-RUN] 将 description -> summary in info")
            else:
                data["info"]["summary"] = data["info"].pop("description")
            stats["description_to_summary"] += 1
            modified = True

        # 迁移 features[].description -> features[].summary
        for feature in data.get("features", []):
            if "description" in feature:
                if dry_run:
                    print(f"  [DRY-RUN] 将 feature {feature.get('id', '?')} description -> summary")
                else:
                    feature["summary"] = feature.pop("description")
                stats["description_to_summary"] += 1
                modified = True

        # 迁移 fixes[].description -> fixes[].summary
        for fix in data.get("fixes", []):
            if "description" in fix:
                if dry_run:
                    print(f"  [DRY-RUN] 将 fix {fix.get('id', '?')} description -> summary")
                else:
                    fix["summary"] = fix.pop("description")
                stats["description_to_summary"] += 1
                modified = True

        # 迁移 notes[].description -> notes[].summary
        for note in data.get("notes", []):
            if "description" in note:
                if dry_run:
                    print(f"  [DRY-RUN] 将 note {note.get('id', '?')} description -> summary")
                else:
                    note["summary"] = note.pop("description")
                stats["description_to_summary"] += 1
                modified = True

        # 迁移 standards[].description -> standards[].summary
        for standard in data.get("standards", []):
            if "description" in standard:
                if dry_run:
                    print(f"  [DRY-RUN] 将 standard {standard.get('id', '?')} description -> summary")
                else:
                    standard["summary"] = standard.pop("description")
                stats["description_to_summary"] += 1
                modified = True

        # 迁移 tag_registry[].description -> tag_registry[].summary
        tag_registry = data.get("tag_registry", {})
        for tag_name, tag_info in tag_registry.items():
            if "description" in tag_info:
                if dry_run:
                    print(f"  [DRY-RUN] 将 tag {tag_name} description -> summary")
                else:
                    tag_info["summary"] = tag_info.pop("description")
                stats["description_to_summary"] += 1
                modified = True

        # 保存修改
        if not dry_run and modified:
            backup_path = project_path.with_suffix(".json.bak")
            # 创建备份
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # 保存修改后的文件
            with open(project_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  已迁移并备份到 {backup_path.name}")

        return stats

    except Exception as e:
        stats["errors"].append(str(e))
        return stats


def main():
    parser = argparse.ArgumentParser(description="迁移 description -> summary 字段")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行")
    args = parser.parse_args()

    # 获取存储目录
    storage_dir = Path.home() / ".project_memory_ai"

    if not storage_dir.exists():
        print(f"存储目录不存在: {storage_dir}")
        return 1

    print(f"扫描存储目录: {storage_dir}")
    print(f"模式: {'DRY-RUN (仅预览)' if args.dry_run else '执行迁移'}\n")

    total_stats = {
        "projects": 0,
        "description_to_summary": 0,
        "errors": []
    }

    # 遍历所有项目目录
    for project_dir in storage_dir.iterdir():
        if not project_dir.is_dir():
            continue

        project_file = project_dir / "project.json"
        if not project_file.exists():
            continue

        print(f"处理项目: {project_dir.name}")
        total_stats["projects"] += 1

        stats = migrate_project_file(project_file, dry_run=args.dry_run)
        total_stats["description_to_summary"] += stats["description_to_summary"]
        total_stats["errors"].extend(stats["errors"])

        if stats["errors"]:
            for err in stats["errors"]:
                print(f"  错误: {err}")

    # 输出汇总
    print("\n" + "=" * 50)
    print("迁移汇总:")
    print(f"  处理项目数: {total_stats['projects']}")
    print(f"  字段迁移数: {total_stats['description_to_summary']}")
    print(f"  错误数: {len(total_stats['errors'])}")

    if args.dry_run:
        print("\n这是 DRY-RUN 模式，没有实际修改任何文件。")
        print("移除 --dry-run 参数来执行实际迁移。")

    return 0 if not total_stats["errors"] else 1


if __name__ == "__main__":
    exit(main())
