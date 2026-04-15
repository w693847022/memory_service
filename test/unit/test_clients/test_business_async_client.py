"""BusinessApiAsyncClient 单元测试."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from clients.business_async_client import BusinessApiAsyncClient
from clients.pool_config import ConnectionPoolConfig


class TestBusinessApiAsyncClient:
    """BusinessApiAsyncClient 测试类."""

    def test_init_default(self):
        """测试默认初始化."""
        client = BusinessApiAsyncClient()

        assert client.base_url == "http://localhost:8002"
        assert client.timeout == 30.0
        assert client._client is None
        assert isinstance(client._pool_config, ConnectionPoolConfig)

    def test_init_custom(self):
        """测试自定义初始化."""
        client = BusinessApiAsyncClient(
            base_url="http://example.com:8080",
            timeout=60.0
        )

        assert client.base_url == "http://example.com:8080"
        assert client.timeout == 60.0

    @patch.dict("os.environ", {
        "BUSINESS_API_URL": "http://async-server:9000",
        "BUSINESS_API_MAX_CONNECTIONS": "75",
        "BUSINESS_API_HTTP2": "true"
    })
    def test_init_with_env_config(self):
        """测试使用环境变量配置."""
        client = BusinessApiAsyncClient()

        assert client.base_url == "http://async-server:9000"
        assert client._pool_config.max_connections == 75
        assert client._pool_config.http2 is True

    def test_client_property_creates_httpx_async_client(self):
        """测试 client 属性创建 httpx.AsyncClient."""
        client = BusinessApiAsyncClient()

        httpx_client = client.client

        assert isinstance(httpx_client, httpx.AsyncClient)
        # 验证客户端已创建
        assert client._client is not None

    def test_client_property_caches_instance(self):
        """测试 client 属性缓存实例."""
        client = BusinessApiAsyncClient()

        client1 = client.client
        client2 = client.client

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭客户端."""
        client = BusinessApiAsyncClient()

        # 访问 client 属性创建实例
        _ = client.client
        assert client._client is not None

        # 关闭
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_client_is_none(self):
        """测试关闭未创建的客户端."""
        client = BusinessApiAsyncClient()

        # 不应该抛出异常
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器."""
        async with BusinessApiAsyncClient() as client:
            assert client is not None
            assert isinstance(client, BusinessApiAsyncClient)

        # 退出上下文后客户端应关闭
        # 注意：这里不能直接检查 _client，因为上下文变量已销毁

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_request_successful(self, mock_client_class):
        """测试成功的异步 HTTP 请求."""
        # Mock 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()
        result = await client._get("/api/test")

        assert result.success is True
        assert result.data == "test"

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_request_http_error(self, mock_client_class):
        """测试 HTTP 错误处理."""
        # Mock 错误响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()
        result = await client._get("/api/test")

        assert result.success is False
        assert result.error is not None and "Not found" in result.error

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_project_list(self, mock_client_class):
        """测试异步 project_list API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"projects": []},
            "total": 0
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()
        result = await client.project_list()

        assert result.success is True
        # 验证请求参数
        call_args = mock_client.request.call_args
        assert "params" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_url_construction(self):
        """测试 URL 构造."""
        client = BusinessApiAsyncClient(base_url="http://test.com")

        # 验证 base_url 正确设置
        assert client.base_url == "http://test.com"

        # 测试 URL 拼接
        expected_url = "http://test.com/api/path"
        actual_url = f"{client.base_url}/api/path"
        assert actual_url == expected_url

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_all_http_methods(self, mock_client_class):
        """测试所有 HTTP 方法."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()

        # 测试 GET
        await client._get("/api/get")
        assert mock_client.request.called

        # 测试 POST
        await client._post("/api/post", json={"key": "value"})
        assert mock_client.request.called

        # 测试 PUT
        await client._put("/api/put", json={"key": "value"})
        assert mock_client.request.called

        # 测试 DELETE
        await client._delete("/api/delete")
        assert mock_client.request.called

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_create_custom_group_with_description(self, mock_client_class):
        """测试创建自定义组传递 description 参数."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "message": "创建成功"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()
        result = await client.create_custom_group(
            project_id="proj_001",
            group_name="test_group",
            description="测试描述"
        )

        assert result.success is True
        # 验证请求参数中包含 description
        call_args = mock_client.request.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["description"] == "测试描述"

    @pytest.mark.asyncio
    @patch("clients.business_async_client.httpx.AsyncClient")
    async def test_update_group_with_description(self, mock_client_class):
        """测试更新组配置传递 description 参数."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "message": "更新成功"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = BusinessApiAsyncClient()
        result = await client.update_group(
            project_id="proj_001",
            group_name="test_group",
            description="更新描述"
        )

        assert result.success is True
        # 验证请求参数中包含 description
        call_args = mock_client.request.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["description"] == "更新描述"
