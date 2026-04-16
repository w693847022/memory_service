"""端到端测试 pytest 配置和共享 fixtures."""

import pytest
import sys
from pathlib import Path

# 添加 test 目录到路径
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

# 模块级变量，存储活跃的服务器实例（用于失败时打印日志）
_active_servers = []

# 导入测试工具类
from e2e.utils import (
    BusinessTestServer,
    McpTestServer,
    RestTestServer,
    McpClient,
    RestClient,
    BusinessClient,
    create_temp_storage,
    cleanup_temp_storage,
)


# ===================
# Session 级别 Fixtures (整个测试会话只启动一次)
# ===================

@pytest.fixture(scope="session")
def business_server():
    """启动 Business API 服务器 (端口 18002).

    这是业务逻辑核心服务器，其他服务都依赖它。
    """
    server = BusinessTestServer(port=18002)
    server.start()
    _active_servers.append(server)
    yield server
    print("\n[Business] 停止服务器...")
    server.stop()
    server.cleanup()
    _active_servers.remove(server)


@pytest.fixture(scope="session")
def mcp_server(business_server):
    """启动 MCP Server (端口 18000).

    MCP Server 是转发层，将 MCP 协议请求转发到 Business API。
    """
    server = McpTestServer(
        port=18000,
        business_url="http://localhost:18002"
    )
    server.start()
    _active_servers.append(server)
    yield server
    print("\n[MCP] 停止服务器...")
    server.stop()
    server.cleanup()
    _active_servers.remove(server)


@pytest.fixture(scope="session")
def rest_server(business_server):
    """启动 REST API 服务器 (端口 18001).

    REST API 是转发层，将 HTTP REST 请求转发到 Business API。
    """
    server = RestTestServer(
        port=18001,
        business_url="http://localhost:18002"
    )
    server.start()
    _active_servers.append(server)
    yield server
    print("\n[REST] 停止服务器...")
    server.stop()
    server.cleanup()
    _active_servers.remove(server)


# ===================
# Function 级别 Fixtures (每个测试独立)
# ===================

@pytest.fixture(scope="function")
def temp_storage():
    """创建临时存储目录.

    每个测试使用独立的临时目录，测试后自动清理。
    """
    temp_dir = create_temp_storage()
    yield temp_dir
    cleanup_temp_storage(temp_dir)


@pytest.fixture(scope="function")
def mcp_client(mcp_server):
    """创建 MCP 协议客户端.

    用于测试 MCP Server 的工具接口。
    依赖 mcp_server 确保服务器已启动。
    """
    client = McpClient(server_url="http://localhost:18000/mcp")
    yield client
    client.close()


@pytest.fixture(scope="function")
def rest_client(rest_server):
    """创建 REST API 客户端.

    用于测试 REST API 的 HTTP 接口。
    依赖 rest_server 确保服务器已启动。
    """
    client = RestClient(base_url="http://localhost:18001")
    yield client
    client.close()


@pytest.fixture(scope="function")
def business_client():
    """创建 Business API 客户端.

    用于直接测试 Business API (绕过转发层)。
    """
    client = BusinessClient(base_url="http://localhost:18002")
    yield client
    client.close()


# ===================
# pytest 配置
# ===================

def pytest_configure(config):
    """pytest 配置钩子."""
    # 自定义标记
    config.addinivalue_line("markers", "mcp: MCP Server 端到端测试")
    config.addinivalue_line("markers", "rest: REST API 端到端测试")
    config.addinivalue_line("markers", "business: Business API 直接测试")
    config.addinivalue_line("markers", "slow: 标记慢速测试")


@pytest.fixture(scope="function", autouse=True)
def print_test_name(request):
    """自动打印测试名称，失败时打印服务日志."""
    print(f"\n>>> 运行测试: {request.node.name}")
    yield
    # 测试失败时，打印服务日志
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        for server in _active_servers:
            server.dump_logs()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """捕获测试结果，用于在 print_test_name 中判断失败."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时的钩子 - 确保所有服务都已关闭."""
    import subprocess
    print("\n[pytest_sessionfinish] 清理测试服务...")
    for server in _active_servers[:]:  # 复制列表避免迭代时修改
        try:
            print(f"[{server.name}] 停止服务器...")
            server.stop()
            server.cleanup()
            _active_servers.remove(server)
        except Exception as e:
            print(f"[{server.name}] 清理失败: {e}")

    # 验证测试端口已释放
    test_ports = [18000, 18001, 18002]
    ports_in_use = []
    for port in test_ports:
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                ports_in_use.append(port)
        except Exception:
            pass  # lsof 可能不可用

    if ports_in_use:
        print(f"[pytest_sessionfinish] 警告: 端口 {ports_in_use} 仍被占用")
    else:
        print("[pytest_sessionfinish] 所有测试端口已释放")
    print("[pytest_sessionfinish] 清理完成")
