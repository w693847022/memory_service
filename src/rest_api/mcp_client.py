"""MCP 客户端模块 - 通过 HTTP 调用 MCP Server."""

import json
import logging
import os
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，通过 HTTP 调用 MCP Server."""

    def __init__(self, server_url: Optional[str] = None):
        """初始化 MCP 客户端.

        Args:
            server_url: MCP Server URL，默认使用环境变量 MCP_SERVER_URL 或 http://mcp-memory-server:8000/mcp
        """
        if server_url is None:
            server_url = os.getenv(
                "MCP_SERVER_URL",
                "http://mcp-memory-server:8000/mcp"
            )
        self.server_url = server_url
        self._request_id = 0

    def _get_request_id(self) -> int:
        """获取下一个请求 ID."""
        self._request_id += 1
        return self._request_id

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 MCP 工具.

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具返回结果（已解析的 JSON）
        """
        # 过滤 None 参数
        params = {k: v for k, v in kwargs.items() if v is not None}

        request_payload = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            }
        }

        try:
            logger.debug(f"Calling MCP tool: {tool_name} with args: {params}")

            response = requests.post(
                self.server_url,
                json=request_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # 检查错误
            if "error" in data:
                logger.error(f"MCP tool error: {data['error']}")
                return {
                    "success": False,
                    "error": data["error"].get("message", "MCP tool execution failed")
                }

            # 从 MCP 响应中提取结果
            # 格式: {"result": {"content": [{"type": "text", "text": "{\"success\":...}"}]}}
            result = data.get("result", {})
            content_list = result.get("content", [])

            if not content_list:
                return {
                    "success": False,
                    "error": "Empty response from MCP server"
                }

            # 获取第一个 content 的 text 字段
            text_content = content_list[0].get("text", "")

            # 解析 JSON
            try:
                return json.loads(text_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP response: {e}")
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {text_content}"
                }

        except requests.exceptions.Timeout:
            logger.error(f"MCP tool timeout: {tool_name}")
            return {
                "success": False,
                "error": "MCP tool execution timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP tool request error: {e}")
            return {
                "success": False,
                "error": "Failed to connect to MCP server"
            }
        except Exception as e:
            logger.error(f"MCP tool exception: {e}")
            return {
                "success": False,
                "error": "Internal MCP tool error"
            }


# 全局 MCP 客户端实例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
