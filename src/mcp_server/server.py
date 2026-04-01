#!/usr/bin/env python
"""MCP 适配层服务器 - 基于 business 层提供 MCP 工具接口.

此服务器作为 MCP 适配层，通过调用 business 层服务来提供 MCP 工具接口。
业务逻辑核心在 business-server (端口 8002)，此服务作为 AI 工具接口层。
"""

import os
import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from mcp.server.fastmcp import FastMCP

# 导入业务层配置
from business.core.config import parse_args
from business.core.utils import track_calls

# 导入 MCP 工具
from .tools import (
    project_register, project_rename, project_list, project_groups_list, project_tags_info,
    project_add, project_update, project_delete, project_remove, project_item_tag_manage,
    tag_register, tag_update, tag_delete, tag_merge,
    project_get, project_stats,
    stats_summary, stats_cleanup,
)

# 导入版本信息
from __init__ import __version__


# ===================
# Server Setup
# ===================
# 在服务器初始化前解析参数
_args = parse_args()

# 创建 MCP 服务器实例
server = FastMCP(
    name="project-memory-mcp",
    instructions="项目本地记忆 MCP Server - 提供项目记忆管理和代码搜索功能。",
    log_level=_args.log_level,
    host=_args.host,
    port=_args.port,
    stateless_http=True,
    json_response=True,
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
# Main Entry Point
# ===================

if __name__ == "__main__":
    args = parse_args()
    server.run(transport=args.transport)