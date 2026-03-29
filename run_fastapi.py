#!/usr/bin/env python
"""FastAPI REST API 启动脚本."""

import sys
import argparse
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="FastAPI REST API 服务器")
    parser.add_argument(
        "--host", "-H",
        default="0.0.0.0",
        help="监听地址"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8001,
        help="监听端口"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用自动重载（开发模式）"
    )
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="日志级别"
    )

    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "rest_api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
