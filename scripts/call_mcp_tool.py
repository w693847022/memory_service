#!/usr/bin/env python
"""MCP 工具调用脚本 - 通过 import 直接调用 MCP 工具函数."""

import sys
import json
import argparse
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from api.tools import (
    project_register, project_rename, project_list, project_groups_list, project_tags_info,
    project_add, project_update, project_delete, project_remove, project_item_tag_manage,
    tag_register, tag_update, tag_delete, tag_merge,
    project_get, project_stats,
    stats_summary, stats_cleanup,
)

# 工具映射表
TOOLS = {
    # 项目管理
    "project_register": project_register,
    "project_rename": project_rename,
    "project_list": project_list,
    "project_groups_list": project_groups_list,
    "project_tags_info": project_tags_info,
    # CRUD
    "project_add": project_add,
    "project_update": project_update,
    "project_delete": project_delete,
    "project_remove": project_remove,
    "project_item_tag_manage": project_item_tag_manage,
    # 标签管理
    "tag_register": tag_register,
    "tag_update": tag_update,
    "tag_delete": tag_delete,
    "tag_merge": tag_merge,
    # 查询
    "project_get": project_get,
    "project_stats": project_stats,
    # 统计
    "stats_summary": stats_summary,
    "stats_cleanup": stats_cleanup,
}


def parse_value(value: str) -> any:
    """解析参数值.

    支持:
    - JSON 字符串: '{"key": "value"}' -> dict
    - 布尔值: true/false -> bool
    - 数字: 123 -> int
    - 字符串: 原样返回
    """
    if not value:
        return None

    # 尝试解析 JSON
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    # 尝试解析布尔值
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    # 尝试解析数字
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # 返回字符串
    return value


def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="调用 MCP 工具")
    parser.add_argument("tool", choices=list(TOOLS.keys()), help="工具名称")
    parser.add_argument("--project_id", help="项目 ID")
    parser.add_argument("--name", help="项目/标签名称")
    parser.add_argument("--new_name", help="新名称")
    parser.add_argument("--path", help="项目路径")
    parser.add_argument("--summary", help="摘要")
    parser.add_argument("--content", help="内容")
    parser.add_argument("--group", help="分组名称")
    parser.add_argument("--group_name", help="分组名称")
    parser.add_argument("--item_id", help="条目 ID")
    parser.add_argument("--status", help="状态")
    parser.add_argument("--severity", help="严重程度")
    parser.add_argument("--tags", help="标签（逗号分隔）")
    parser.add_argument("--related", help="关联条目（JSON 字符串）")
    parser.add_argument("--tag_name", help="标签名称")
    parser.add_argument("--old_tag", help="旧标签名称")
    parser.add_argument("--new_tag", help="新标签名称")
    parser.add_argument("--aliases", help="别名（逗号分隔）")
    parser.add_argument("--mode", help="操作模式")
    parser.add_argument("--operation", help="操作类型")
    parser.add_argument("--tag", help="单个标签")
    parser.add_argument("--type", help="类型")
    parser.add_argument("--tool_name", help="工具名称")
    parser.add_argument("--date", help="日期")
    parser.add_argument("--retention_days", help="保留天数")
    parser.add_argument("--view_mode", help="视图模式")
    parser.add_argument("--page", help="页码", type=int)
    parser.add_argument("--size", help="每页条数", type=int)
    parser.add_argument("--summary_pattern", help="摘要正则")
    parser.add_argument("--tag_name_pattern", help="标签名正则")
    parser.add_argument("--created_after", help="创建时间起始")
    parser.add_argument("--created_before", help="创建时间截止")
    parser.add_argument("--updated_after", help="修改时间起始")
    parser.add_argument("--updated_before", help="修改时间截止")
    parser.add_argument("--include_archived", help="包含归档", type=bool)
    parser.add_argument("--name_pattern", help="名称正则")
    parser.add_argument("--unregistered_only", help="仅未注册", type=bool)
    parser.add_argument("--force", help="强制删除")

    args = parser.parse_args()

    # 获取工具函数
    tool_func = TOOLS.get(args.tool)
    if not tool_func:
        print(json.dumps({"success": False, "error": f"Unknown tool: {args.tool}"}))
        sys.exit(1)

    # 构建参数字典
    kwargs = {}
    for key, value in vars(args).items():
        if key == "tool":
            continue
        if value is not None:
            # 特殊处理布尔参数
            if key in ("include_archived", "unregistered_only", "force"):
                kwargs[key] = value
            else:
                kwargs[key] = parse_value(str(value))

    try:
        # 调用工具函数
        result = tool_func(**kwargs)
        print(result)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Tool execution error: {str(e)}"
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
