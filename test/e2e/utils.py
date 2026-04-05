"""端到端测试工具类."""

import os
import sys
import signal
import subprocess
import tempfile
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import requests
import httpx

# Add src to path
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


class TestServer:
    """测试服务器基类."""

    def __init__(self, name: str, port: int, storage_dir: Optional[str] = None):
        """初始化测试服务器.

        Args:
            name: 服务器名称
            port: 服务器端口
            storage_dir: 存储目录，如果为 None 则使用临时目录
        """
        self.name = name
        self.port = port
        self.storage_dir = storage_dir or tempfile.mkdtemp(prefix=f"{name}_test_")
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://127.0.0.1:{port}"
        self._log_prefix = f"[{name}:{port}]"

    def start(self) -> None:
        """启动服务器."""
        raise NotImplementedError

    def stop(self) -> None:
        """停止服务器."""
        if self.process:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
            self.process = None

    def cleanup(self) -> None:
        """清理临时目录."""
        if self.storage_dir and os.path.exists(self.storage_dir):
            shutil.rmtree(self.storage_dir, ignore_errors=True)

    def _wait_for_ready(self, health_path: str = "/health", timeout: int = 30) -> None:
        """等待服务器就绪."""
        print(f"{self._log_prefix} 等待服务启动...")
        for _ in range(timeout * 2):
            try:
                response = requests.get(f"{self.base_url}{health_path}", timeout=1)
                if response.status_code == 200:
                    print(f"{self._log_prefix} 服务已就绪")
                    return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError(f"{self._log_prefix} 服务启动超时")

    def __enter__(self):
        """上下文管理器入口."""
        self.start()
        return self

    def __exit__(self, *_args):
        """上下文管理器退出."""
        self.stop()
        self.cleanup()


class BusinessTestServer(TestServer):
    """Business API 测试服务器."""

    def __init__(self, port: int = 18002, storage_dir: Optional[str] = None):
        super().__init__("business", port, storage_dir)

    def start(self) -> None:
        """启动 Business API 服务器."""
        env = os.environ.copy()
        env["MCP_STORAGE_DIR"] = self.storage_dir
        env["PYTHONUNBUFFERED"] = "1"
        env["BUSINESS_PORT"] = str(self.port)

        cmd = [sys.executable, "-m", "uvicorn", "business.main:app",
               "--host", "0.0.0.0", "--port", str(self.port)]

        print(f"{self._log_prefix} 启动命令: {' '.join(cmd)}")
        print(f"{self._log_prefix} 存储目录: {self.storage_dir}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(src_dir),
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )

        self._wait_for_ready("/health")


class McpTestServer(TestServer):
    """MCP Server 测试服务器."""

    def __init__(self, port: int = 18000, business_url: str = "http://localhost:18002",
                 storage_dir: Optional[str] = None):
        super().__init__("mcp", port, storage_dir)
        self.business_url = business_url

    def start(self) -> None:
        """启动 MCP Server."""
        env = os.environ.copy()
        env["MCP_STORAGE_DIR"] = self.storage_dir
        env["MCP_PORT"] = str(self.port)
        env["MCP_HOST"] = "0.0.0.0"
        env["MCP_TRANSPORT"] = "streamable-http"
        env["BUSINESS_API_URL"] = self.business_url
        env["PYTHONUNBUFFERED"] = "1"

        # 使用 run_mcp.py 启动
        run_mcp_path = Path(__file__).parent.parent.parent / "run_mcp.py"
        cmd = [sys.executable, str(run_mcp_path)]

        print(f"{self._log_prefix} 启动命令: {' '.join(cmd)}")
        print(f"{self._log_prefix} Business API: {self.business_url}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(src_dir.parent),
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )

        # MCP Server 可能没有 /health 端点，等待一段时间
        print(f"{self._log_prefix} 等待服务启动...")
        time.sleep(3)
        print(f"{self._log_prefix} 服务已就绪")


class RestTestServer(TestServer):
    """REST API 测试服务器."""

    def __init__(self, port: int = 18001, business_url: str = "http://localhost:18002",
                 storage_dir: Optional[str] = None):
        super().__init__("rest", port, storage_dir)
        self.business_url = business_url

    def start(self) -> None:
        """启动 REST API 服务器."""
        env = os.environ.copy()
        env["MCP_STORAGE_DIR"] = self.storage_dir
        env["BUSINESS_API_URL"] = self.business_url
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [sys.executable, "-m", "uvicorn", "rest_api.main:app",
               "--host", "0.0.0.0", "--port", str(self.port)]

        print(f"{self._log_prefix} 启动命令: {' '.join(cmd)}")
        print(f"{self._log_prefix} Business API: {self.business_url}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(src_dir),
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )

        self._wait_for_ready("/health")


class McpClient:
    """MCP 协议客户端."""

    def __init__(self, server_url: str = "http://localhost:18000/mcp"):
        """初始化 MCP 客户端.

        Args:
            server_url: MCP Server URL (默认包含 /mcp 路径)
        """
        self.server_url = server_url.rstrip("/")
        self._request_id = 0
        self._client = httpx.Client(timeout=120.0)

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
            工具返回结果
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

        response = self._client.post(
            self.server_url,
            json=request_payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()

        # 检查错误
        if "error" in data:
            return {
                "success": False,
                "error": data["error"].get("message", "MCP tool execution failed")
            }

        # 从 MCP 响应中提取结果
        result = data.get("result", {})
        content_list = result.get("content", [])

        if not content_list:
            return {"success": False, "error": "Empty response from MCP server"}

        # 获取第一个 content 的 text 字段并解析 JSON
        import json
        text_content = content_list[0].get("text", "")
        return json.loads(text_content)

    def close(self):
        """关闭客户端."""
        self._client.close()


class RestClient:
    """REST API 客户端."""

    def __init__(self, base_url: str = "http://localhost:18001"):
        """初始化 REST 客户端.

        Args:
            base_url: REST API 基础 URL
        """
        self.base_url = base_url.rstrip("/")
        self._client = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求."""
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 GET 请求."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 POST 请求."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 PUT 请求."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 DELETE 请求."""
        return self._request("DELETE", path, **kwargs)

    def close(self):
        """关闭客户端."""
        self._client.close()


class BusinessClient:
    """Business API 客户端 (直接调用)."""

    def __init__(self, base_url: str = "http://localhost:18002"):
        """初始化 Business 客户端.

        Args:
            base_url: Business API 基础 URL
        """
        self.base_url = base_url.rstrip("/")
        self._client = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求."""
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 GET 请求."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 POST 请求."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 PUT 请求."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送 DELETE 请求."""
        return self._request("DELETE", path, **kwargs)

    def close(self):
        """关闭客户端."""
        self._client.close()


def create_temp_storage() -> str:
    """创建临时存储目录."""
    return tempfile.mkdtemp(prefix="mcp_e2e_")


def cleanup_temp_storage(storage_dir: str) -> None:
    """清理临时存储目录."""
    if storage_dir and os.path.exists(storage_dir):
        shutil.rmtree(storage_dir, ignore_errors=True)
