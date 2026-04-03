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

# 导入通用配置
from common.config import parse_args

# 导入 MCP 工具
from .tools import (
    project_register, project_rename, project_list, project_groups_list, project_tags_info,
    project_add, project_update, project_delete, project_remove, project_item_tag_manage,
    tag_register, tag_update, tag_delete, tag_merge,
    project_get,
)

# 导入版本信息
from __init__ import __version__


# ===================
# Server Setup (Lazy Initialization)
# ===================
# 服务器实例延迟到首次访问时创建
_server = None

def _get_server():
    """延迟获取或创建服务器实例."""
    global _server
    if _server is None:
        # 在服务器初始化前解析参数
        args = parse_args()

        # 配置日志（支持滚动删除）
        import os
        from common.logging_config import setup_logging

        log_level = os.getenv("MCP_LOG_LEVEL", args.log_level.upper())
        log_dir = os.getenv("LOG_DIR", "/app/logs")
        max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 默认 10MB
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # 默认保留 5 个文件

        setup_logging(
            service_name="mcp",
            log_level=log_level,
            log_dir=log_dir,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )

        # 创建 MCP 服务器实例
        _server = FastMCP(
            name="project-memory-mcp",
            instructions="项目本地记忆 MCP Server - 提供项目记忆管理和代码搜索功能。",
            log_level=args.log_level,
            host=args.host,
            port=args.port,
            stateless_http=True,
            json_response=True,
        )

        # Register Tools
        _server.tool()(project_register)
        _server.tool()(project_rename)
        _server.tool()(project_list)
        _server.tool()(project_groups_list)
        _server.tool()(project_tags_info)

        # CRUD Tools
        _server.tool()(project_add)
        _server.tool()(project_update)
        _server.tool()(project_delete)
        _server.tool()(project_remove)
        _server.tool()(project_item_tag_manage)

        # Tag Management Tools
        _server.tool()(tag_register)
        _server.tool()(tag_update)
        _server.tool()(tag_delete)
        _server.tool()(tag_merge)

        # Query Tools
        _server.tool()(project_get)

    return _server


# 为了向后兼容，提供 server 属性
@property
def server():
    return _get_server()


# ===================
# Main Entry Point
# ===================

if __name__ == "__main__":
    server = _get_server()
    args = parse_args()
    server.run(transport=args.transport)
