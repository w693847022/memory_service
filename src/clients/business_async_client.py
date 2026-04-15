"""Business API 异步 HTTP 客户端.

供 FastAPI Server 等异步场景调用 business 层 HTTP 服务。
"""

import os
from typing import Optional, Dict, List, Union, Any
import httpx
from src.models import ApiResponse
from .pool_config import ConnectionPoolConfig


def _get_business_api_url() -> str:
    """动态获取 Business API 服务地址."""
    return os.environ.get("BUSINESS_API_URL", "http://localhost:8002")


class BusinessApiAsyncClient:
    """Business API 异步 HTTP 客户端."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """初始化客户端.

        Args:
            base_url: Business API 服务地址，如果为 None 则从环境变量获取
            timeout: 请求超时时间（秒）
        """
        if base_url is None:
            base_url = _get_business_api_url()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._pool_config = ConnectionPoolConfig.from_env(timeout)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取或创建异步 HTTP 客户端."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=self._pool_config.to_limits(),
                http2=self._pool_config.http2,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        """关闭异步 HTTP 客户端."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口."""
        await self.close()

    async def _request(self, method: str, path: str, **kwargs) -> ApiResponse:
        """发送异步 HTTP 请求.

        Args:
            method: HTTP 方法
            path: 请求路径
            **kwargs: 其他请求参数

        Returns:
            ApiResponse 对象
        """
        url = f"{self.base_url}{path}"
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            result = response.json()
            return ApiResponse.from_dict(result)
        except httpx.HTTPStatusError as e:
            try:
                error_detail = e.response.json()
                if isinstance(error_detail, dict) and "detail" in error_detail:
                    detail = error_detail["detail"]
                    if isinstance(detail, list):
                        errors = []
                        for item in detail:
                            if isinstance(item, dict):
                                msg = item.get("msg", "")
                                loc = item.get("loc", [])
                                if loc:
                                    errors.append(f"{loc[-1] if loc else '参数'}: {msg}")
                                else:
                                    errors.append(msg)
                        error_msg = "; ".join(errors)
                        return ApiResponse(success=False, error=error_msg)
                    return ApiResponse(success=False, error=str(detail))
                return ApiResponse(success=False, error=str(e))
            except Exception:
                return ApiResponse(success=False, error=str(e))
        except httpx.HTTPError as e:
            return ApiResponse(success=False, error=str(e))
        except Exception as e:
            return ApiResponse(success=False, error=f"请求失败: {str(e)}")

    async def _get(self, path: str, **kwargs) -> ApiResponse:
        """发送异步 GET 请求."""
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs) -> ApiResponse:
        """发送异步 POST 请求."""
        return await self._request("POST", path, **kwargs)

    async def _put(self, path: str, **kwargs) -> ApiResponse:
        """发送异步 PUT 请求."""
        return await self._request("PUT", path, **kwargs)

    async def _delete(self, path: str, **kwargs) -> ApiResponse:
        """发送异步 DELETE 请求."""
        return await self._request("DELETE", path, **kwargs)

    # ===================
    # Project APIs
    # ===================

    async def project_list(
        self,
        view_mode: str = "summary",
        page: int = 1,
        size: int = 0,
        name_pattern: str = "",
        include_archived: bool = False
    ) -> ApiResponse:
        """列出所有项目."""
        params = {
            "view_mode": view_mode,
            "page": page,
            "size": size,
            "name_pattern": name_pattern,
            "include_archived": include_archived
        }
        return await self._get("/api/projects", params=params)

    async def register_project(
        self,
        name: str,
        path: str = "",
        summary: str = "",
        tags: str = ""
    ) -> ApiResponse:
        """注册新项目."""
        json_data = {"name": name, "path": path, "summary": summary, "tags": tags}
        return await self._post("/api/projects", json=json_data)

    async def get_project(self, project_id: str) -> ApiResponse:
        """获取项目详情."""
        return await self._get(f"/api/projects/{project_id}")

    async def rename_project(self, project_id: str, new_name: str) -> ApiResponse:
        """重命名项目."""
        return await self._put(f"/api/projects/{project_id}/rename", params={"new_name": new_name})

    async def remove_project(self, project_id: str, mode: str = "archive") -> ApiResponse:
        """删除或归档项目."""
        return await self._delete(f"/api/projects/{project_id}", params={"mode": mode})

    async def list_groups(self, project_id: str) -> ApiResponse:
        """列出项目的所有分组."""
        return await self._get(f"/api/projects/{project_id}/groups")

    async def project_tags_info(
        self,
        project_id: str,
        group_name: str = "",
        tag_name: str = "",
        unregistered_only: bool = False,
        page: int = 1,
        size: int = 0,
        view_mode: str = "summary",
        summary_pattern: str = "",
        tag_name_pattern: str = ""
    ) -> ApiResponse:
        """查询标签信息."""
        params = {
            "group_name": group_name,
            "tag_name": tag_name,
            "unregistered_only": unregistered_only,
            "page": page,
            "size": size,
            "view_mode": view_mode,
            "summary_pattern": summary_pattern,
            "tag_name_pattern": tag_name_pattern
        }
        return await self._get(f"/api/projects/{project_id}/tags", params=params)

    async def project_get(
        self,
        project_id: str,
        group_name: str = "",
        item_id: str = "",
        status: str = "",
        severity: str = "",
        tags: str = "",
        page: int = 1,
        size: int = 0,
        view_mode: str = "summary",
        summary_pattern: str = "",
        created_after: str = "",
        created_before: str = "",
        updated_after: str = "",
        updated_before: str = ""
    ) -> ApiResponse:
        """获取项目信息或查询条目列表/详情."""
        params = {
            "group_name": group_name,
            "item_id": item_id,
            "status": status,
            "severity": severity,
            "tags": tags,
            "page": page,
            "size": size,
            "view_mode": view_mode,
            "summary_pattern": summary_pattern,
            "created_after": created_after,
            "created_before": created_before,
            "updated_after": updated_after,
            "updated_before": updated_before
        }
        # 根据 group_name 选择正确的端点
        if not group_name:
            # 获取整个项目信息
            return await self._get(f"/api/projects/{project_id}")
        # 获取项目条目
        return await self._get(f"/api/projects/{project_id}/items", params=params)

    async def project_add(
        self,
        project_id: str,
        group: str,
        content: str = "",
        summary: str = "",
        status: Optional[str] = None,
        severity: str = "medium",
        related: Union[str, Dict[str, List[str]]] = "",
        tags: str = ""
    ) -> ApiResponse:
        """添加项目条目."""
        data = {
            "content": content,
            "summary": summary,
            "status": status,
            "severity": severity,
            "related": related,
            "tags": tags
        }
        data = {k: v for k, v in data.items() if v is not None}
        return await self._post(f"/api/projects/{project_id}/items", params={"group": group}, json=data)

    async def project_update(
        self,
        project_id: str,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        related: Optional[Union[str, Dict[str, List[str]]]] = None,
        tags: Optional[str] = None,
        version: Optional[int] = None
    ) -> ApiResponse:
        """更新项目条目."""
        import json
        data = {
            "content": content,
            "summary": summary,
            "status": status,
            "severity": severity,
            "related": json.dumps(related) if isinstance(related, dict) else related,
            "tags": tags,
            "version": version
        }
        data = {k: v for k, v in data.items() if v is not None}
        return await self._put(f"/api/projects/{project_id}/items/{item_id}", params={"group": group}, json=data)

    async def project_delete(self, project_id: str, group: str, item_id: str) -> ApiResponse:
        """删除项目条目."""
        params = {"group": group}
        return await self._delete(f"/api/projects/{project_id}/items/{item_id}", params=params)

    async def manage_item_tags(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        operation: str,
        tag: str = "",
        tags: str = ""
    ) -> ApiResponse:
        """管理条目标签."""
        params = {
            "group_name": group_name,
            "item_id": item_id,
            "operation": operation,
            "tag": tag,
            "tags": tags
        }
        return await self._post(f"/api/projects/{project_id}/items/{item_id}/tags", params=params)

    # ===================
    # Tag APIs
    # ===================

    async def tag_register(
        self,
        project_id: str,
        tag_name: str,
        summary: str,
        aliases: str = ""
    ) -> ApiResponse:
        """注册项目标签."""
        json_data = {"project_id": project_id, "tag_name": tag_name, "summary": summary, "aliases": aliases}
        return await self._post("/api/tags/register", json=json_data)

    async def tag_update(
        self,
        project_id: str,
        tag_name: str,
        summary: Optional[str] = None
    ) -> ApiResponse:
        """更新已注册标签."""
        json_data = {"project_id": project_id, "tag_name": tag_name}
        if summary is not None:
            json_data["summary"] = summary
        return await self._put("/api/tags/update", json=json_data)

    async def tag_delete(
        self,
        project_id: str,
        tag_name: str,
        force: str = "false"
    ) -> ApiResponse:
        """删除标签注册."""
        json_data = {"project_id": project_id, "tag_name": tag_name, "force": force}
        return await self._delete("/api/tags/delete", json=json_data)

    async def tag_merge(
        self,
        project_id: str,
        old_tag: str,
        new_tag: str
    ) -> ApiResponse:
        """合并标签."""
        json_data = {"project_id": project_id, "old_tag": old_tag, "new_tag": new_tag}
        return await self._post("/api/tags/merge", json=json_data)

    # ===================
    # Stats APIs
    # ===================

    async def project_stats(self) -> ApiResponse:
        """获取全局统计信息."""
        return await self._get("/api/stats")

    async def stats_summary(
        self,
        type: str = "",
        tool_name: str = "",
        project_id: str = "",
        date: str = ""
    ) -> ApiResponse:
        """获取统计摘要."""
        params = {"type": type, "tool_name": tool_name, "project_id": project_id, "date": date}
        return await self._get("/api/stats/summary", params=params)

    async def stats_cleanup(self, retention_days: int = 30) -> ApiResponse:
        """清理过期统计数据."""
        return await self._delete("/api/stats/cleanup", params={"retention_days": retention_days})

    # ===================
    # Group APIs
    # ===================

    async def create_custom_group(
        self,
        project_id: str,
        group_name: str,
        content_max_bytes: int = 240,
        summary_max_bytes: int = 90,
        allow_related: bool = False,
        allowed_related_to: str = "",
        enable_status: bool = True,
        enable_severity: bool = False,
        description: str = ""
    ) -> ApiResponse:
        """创建自定义组."""
        params = {
            "project_id": project_id,
            "group_name": group_name,
            "content_max_bytes": content_max_bytes,
            "summary_max_bytes": summary_max_bytes,
            "allow_related": allow_related,
            "allowed_related_to": allowed_related_to,
            "enable_status": enable_status,
            "enable_severity": enable_severity,
            "description": description
        }
        return await self._post("/api/groups/custom", params=params)

    async def update_group(
        self,
        project_id: str,
        group_name: str,
        content_max_bytes: Optional[int] = None,
        summary_max_bytes: Optional[int] = None,
        allow_related: Optional[bool] = None,
        allowed_related_to: Optional[str] = None,
        enable_status: Optional[bool] = None,
        enable_severity: Optional[bool] = None,
        max_tags: Optional[int] = None,
        status_values: Optional[str] = None,
        severity_values: Optional[str] = None,
        required_fields: Optional[str] = None,
        description: Optional[str] = None
    ) -> ApiResponse:
        """更新组配置."""
        params = {"project_id": project_id, "group_name": group_name}
        for k, v in [("content_max_bytes", content_max_bytes), ("summary_max_bytes", summary_max_bytes),
                     ("allow_related", allow_related), ("allowed_related_to", allowed_related_to),
                     ("enable_status", enable_status), ("enable_severity", enable_severity),
                     ("max_tags", max_tags), ("status_values", status_values),
                     ("severity_values", severity_values), ("required_fields", required_fields),
                     ("description", description)]:
            if v is not None:
                params[k] = v
        return await self._put("/api/groups/custom", params=params)

    async def delete_custom_group(self, project_id: str, group_name: str) -> ApiResponse:
        """删除自定义组."""
        params = {"project_id": project_id, "group_name": group_name}
        return await self._delete("/api/groups/custom", params=params)

    async def get_group_settings(self, project_id: str, group: str = "") -> ApiResponse:
        """获取组设置（支持单组查询）.

        Args:
            project_id: 项目ID
            group: 组名称（可选），传入时返回该组的配置
        """
        params = {"project_id": project_id}
        if group:
            params["group"] = group
        return await self._get("/api/groups/settings", params=params)

    async def update_group_settings(
        self,
        project_id: str,
        group: str = "",
        default_related_rules: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> ApiResponse:
        """更新组设置（支持单组更新）.

        Args:
            project_id: 项目ID
            group: 组名称（可选），传入时更新该组的配置
            default_related_rules: 默认关联规则（不传 group 时使用）
            config: 组配置对象（传 group 时使用）
        """
        params = {"project_id": project_id}
        if group:
            params["group"] = group
            json_data = {"config": config}
        else:
            json_data = {"default_related_rules": default_related_rules}
        return await self._put("/api/groups/settings", params=params, json=json_data)


# 全局异步客户端实例
_async_client: Optional[BusinessApiAsyncClient] = None


async def get_business_async_client() -> BusinessApiAsyncClient:
    """获取全局 Business API 异步客户端实例."""
    global _async_client
    if _async_client is None:
        _async_client = BusinessApiAsyncClient()
    return _async_client


async def close_business_async_client():
    """关闭全局 Business API 异步客户端."""
    global _async_client
    if _async_client:
        await _async_client.close()
        _async_client = None
