#!/usr/bin/env python
"""MCP Server 启动脚本.

独立启动 MCP Server 服务（端口 8000）。
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到 Python 路径
# 检测运行环境：Docker 中脚本位于 /app/，本地位于 /path/to/project/scripts/
if Path(__file__).parent.name == "app" or str(Path(__file__).parent) == "/app":
    # Docker 环境
    src_path = Path("/app/src")
    project_root = Path("/app")
else:
    # 本地环境
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    from mcp_server.server import _get_server
    from business.core.config import parse_args

    port = int(os.environ.get("MCP_PORT", 8000))
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")

    print(f"启动 MCP Server 服务...")
    print(f"监听地址: {host}:{port}")
    print(f"传输方式: {transport}")
    print()

    server = _get_server()
    args = parse_args()
    server.run(transport=args.transport)