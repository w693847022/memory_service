"""MCP 客户端模块 - 通过 subprocess 调用 MCP Server."""

import json
import subprocess
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，通过 subprocess 调用 MCP 工具."""

    def __init__(self, script_path: Optional[str] = None):
        """初始化 MCP 客户端.

        Args:
            script_path: MCP 调用脚本路径，默认使用 scripts/call_mcp_tool.py
        """
        if script_path is None:
            # 默认使用项目内的调用脚本
            script_path = str(Path(__file__).parent.parent.parent / "scripts" / "call_mcp_tool.py")
        self.script_path = script_path

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 MCP 工具.

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具返回结果（已解析的 JSON）
        """
        import sys

        cmd = [sys.executable, self.script_path, tool_name]

        # 添加参数
        for key, value in kwargs.items():
            if value is not None:
                cmd.extend([f"--{key}", str(value)])

        try:
            logger.debug(f"Calling MCP tool: {tool_name} with args: {kwargs}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode != 0:
                logger.error(f"MCP tool error: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr or "MCP tool execution failed"
                }

            # 解析 JSON 返回
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP response: {e}")
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {result.stdout}"
                }

        except subprocess.TimeoutExpired:
            logger.error(f"MCP tool timeout: {tool_name}")
            return {
                "success": False,
                "error": "MCP tool execution timeout"
            }
        except Exception as e:
            logger.error(f"MCP tool exception: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局 MCP 客户端实例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
