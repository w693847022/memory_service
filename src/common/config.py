"""配置和初始化模块."""

import argparse
import os


def parse_args():
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description="项目本地记忆 MCP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
传输模式说明:
  stdio           标准输入输出模式 (默认，用于 Claude Code/Claude Desktop)
  sse             Server-Sent Events 模式
  streamable-http Streamable HTTP 模式 (推荐，2026年标准)

示例:
  python server.py                              # 使用默认 stdio 模式
  python server.py --transport sse              # SSE 模式
  python server.py --transport streamable-http --port 9000  # HTTP 模式

环境变量:
  MCP_TRANSPORT  传输协议 (stdio, sse, streamable-http)
  MCP_HOST       服务器主机地址 (默认: 127.0.0.1)
  MCP_PORT       服务器端口 (默认: 8000)
  MCP_LOG_LEVEL  日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
    )

    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="传输协议 (默认: stdio, 环境变量: MCP_TRANSPORT)"
    )

    parser.add_argument(
        "--host", "-H",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="服务器主机地址 (默认: 127.0.0.1, 环境变量: MCP_HOST)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="服务器端口 (默认: 8000, 环境变量: MCP_PORT)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("MCP_LOG_LEVEL", "INFO"),
        help="日志级别 (默认: INFO, 环境变量: MCP_LOG_LEVEL)"
    )

    return parser.parse_args()
