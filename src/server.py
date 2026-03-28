#!/usr/bin/env python
"""项目本地记忆 MCP Server - 提供项目记忆管理和代码搜索功能。"""

from mcp.server.fastmcp import FastMCP
import json
import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from __init__ import __version__

from core.config import parse_args
from core.utils import track_calls
from features.guidelines import _build_guidelines_content
from api.tools import (
    project_register, project_rename, project_list, project_groups_list, project_tags_info,
    project_add, project_update, project_delete, project_remove, project_item_tag_manage,
    tag_register, tag_update, tag_delete, tag_merge,
    project_get, project_stats,
    stats_summary, stats_cleanup,
)


# ===================
# Server Setup
# ===================
# 在服务器初始化前解析参数
_args = parse_args()

# 创建 MCP 服务器实例
server = FastMCP(
    name="project-memory-server",
    instructions=__doc__,
    log_level=_args.log_level,
    host=_args.host,      # 监听地址
    port=_args.port,      # 监听端口
    stateless_http=True,  # 启用无状态HTTP模式，兼容Claude Code
    json_response=True,   # 使用JSON响应格式，兼容Claude Code HTTP客户端
)


# ===================
# Register Tools
# ===================

# Project Management Tools
server.tool()(track_calls(project_register))
server.tool()(track_calls(project_rename))
server.tool()(track_calls(project_list))
server.tool()(track_calls(project_groups_list))
server.tool()(track_calls(project_tags_info))

# CRUD Tools
server.tool()(track_calls(project_add))
server.tool()(track_calls(project_update))
server.tool()(track_calls(project_delete))
server.tool()(track_calls(project_remove))
server.tool()(track_calls(project_item_tag_manage))

# Tag Management Tools
server.tool()(track_calls(tag_register))
server.tool()(track_calls(tag_update))
server.tool()(track_calls(tag_delete))
server.tool()(track_calls(tag_merge))

# Query Tools
server.tool()(track_calls(project_get))
server.tool()(track_calls(project_stats))

# Statistics Tools
server.tool()(track_calls(stats_summary))
server.tool()(track_calls(stats_cleanup))


# ===================
# Resources
# ===================

@server.resource("guidelines://usage")
def get_usage_guidelines() -> str:
    """获取AI智能体使用建议（默认中文）.

    提供项目记忆功能的最佳实践、命名规范、查询流程等指导。

    Returns:
        结构化的使用建议JSON
    """
    guidelines = _build_guidelines_content("zh")
    return json.dumps(guidelines, ensure_ascii=False, indent=2)


@server.resource("guidelines://usage/en")
def get_usage_guidelines_en() -> str:
    """Get AI agent usage guidelines (English).

    Provides best practices, naming conventions, query workflows, etc.

    Returns:
        Structured usage guidelines JSON
    """
    guidelines = _build_guidelines_content("en")
    return json.dumps(guidelines, ensure_ascii=False, indent=2)


@server.resource("info://server")
def get_server_info() -> str:
    """获取服务器信息."""
    info = {
        "name": "项目本地记忆服务器",
        "version": __version__,
        "description": "提供项目记忆管理、代码搜索功能、接口调用统计和AI智能体使用建议的MCP服务器",
        "features": [
            "项目注册与管理",
            "功能记录与状态跟踪",
            "Bug修复记录与追踪",
            "开发笔记记录",
            "笔记关联功能（feature/fix ↔ note）",
            "标签系统（4层查询：项目→分组→标签→条目）",
            "代码搜索（GitHub + Stack Overflow）",
            "接口调用统计（按工具、项目、客户端、IP、日期）",
            "数据迁移与备份"
        ],
        "resources": [
            {
                "uri": "info://server",
                "name": "服务器信息",
                "description": "服务器版本、功能和资源列表"
            },
            {
                "uri": "guidelines://usage",
                "name": "使用指南（中文）",
                "description": "完整的使用规范和最佳实践"
            },
            {
                "uri": "guidelines://usage/en",
                "name": "Usage Guidelines (English)",
                "description": "Comprehensive usage guidelines and best practices"
            }
        ],
        "runtime": {
            "storage_location": "~/.project_memory_ai/",
            "note": "使用 tools/list 接口获取完整的工具列表及参数说明"
        }
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


# ===================
# Main Entry Point
# ===================

if __name__ == "__main__":
    args = parse_args()
    server.run(transport=args.transport)
