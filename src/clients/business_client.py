"""Business API HTTP 客户端.

供 MCP Server 和 REST API Server 调用 business 层 HTTP 服务。
"""

import os
import httpx
from typing import Optional, Dict, List, Union, Any
from common.response import ApiResponse

# Business API 服务地址
BUSINESS_API_BASE_URL = os.environ.get("BUSINESS_API_URL", "http://localhost:8002")


class BusinessApiClient:
    """Business API HTTP 客户端."""

    def __init__(self, base_url: str = BUSINESS_API_BASE_URL, timeout: float = 30.0):
        """初始化客户端.

        Args:
            base_url: Business API 服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """获取或创建 HTTP 客户端."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self):
        """关闭 HTTP 客户端."""
        if self._client:
            self._client.close()
            self._client = None

    def _request(self, method: str, path: str, **kwargs) -> ApiResponse:
        """发送 HTTP 请求.

        Args:
            method: HTTP 方法
            path: 请求路径
            **kwargs: 其他请求参数

        Returns:
            ApiResponse 对象
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            result = response.json()
            return ApiResponse.from_dict(result)
        except httpx.HTTPError as e:
            return ApiResponse(success=False, error=str(e))
        except Exception as e:
            return ApiResponse(success=False, error=f"请求失败: {str(e)}")

    def _get(self, path: str, **kwargs) -> ApiResponse:
        """发送 GET 请求."""
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> ApiResponse:
        """发送 POST 请求."""
        return self._request("POST", path, **kwargs)

    def _put(self, path: str, **kwargs) -> ApiResponse:
        """发送 PUT 请求."""
        return self._request("PUT", path, **kwargs)

    def _delete(self, path: str, **kwargs) -> ApiResponse:
        """发送 DELETE 请求."""
        return self._request("DELETE", path, **kwargs)

    # ===================
    # Project APIs
    # ===================

    def project_list(
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
        return self._get("/api/projects", params=params)

    def register_project(
        self,
        name: str,
        path: str = "",
        summary: str = "",
        tags: str = ""
    ) -> ApiResponse:
        """注册新项目."""
        data = {"name": name, "path": path, "summary": summary, "tags": tags}
        return self._post("/api/projects", params=data)

    def get_project(self, project_id: str) -> ApiResponse:
        """获取项目详情."""
        return self._get(f"/api/projects/{project_id}")

    def rename_project(self, project_id: str, new_name: str) -> ApiResponse:
        """重命名项目."""
        return self._put(f"/api/projects/{project_id}/rename", params={"new_name": new_name})

    def remove_project(self, project_id: str, mode: str = "archive") -> ApiResponse:
        """删除或归档项目."""
        return self._delete(f"/api/projects/{project_id}", params={"mode": mode})

    def list_groups(self, project_id: str) -> ApiResponse:
        """列出项目的所有分组."""
        return self._get(f"/api/projects/{project_id}/groups")

    def project_tags_info(
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
        return self._get(f"/api/projects/{project_id}/tags", params=params)

    def project_get(
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
        return self._get(f"/api/projects/{project_id}/items", params=params)

    def project_add(
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
            "group": group,
            "content": content,
            "summary": summary,
            "status": status,
            "severity": severity,
            "related": related,
            "tags": tags
        }
        return self._post(f"/api/projects/{project_id}/items", params=data)

    def project_update(
        self,
        project_id: str,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        related: Optional[Union[str, Dict[str, List[str]]]] = None,
        tags: Optional[str] = None
    ) -> ApiResponse:
        """更新项目条目."""
        data = {
            "group": group,
            "content": content,
            "summary": summary,
            "status": status,
            "severity": severity,
            "related": related,
            "tags": tags
        }
        # 移除 None 值
        data = {k: v for k, v in data.items() if v is not None}
        return self._put(f"/api/projects/{project_id}/items/{item_id}", params=data)

    def project_delete(self, project_id: str, group: str, item_id: str) -> ApiResponse:
        """删除项目条目."""
        params = {"group": group}
        return self._delete(f"/api/projects/{project_id}/items/{item_id}", params=params)

    def manage_item_tags(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        operation: str,
        tag: str = "",
        tags: str = ""
    ) -> ApiResponse:
        """管理条目标签."""
        data = {
            "group_name": group_name,
            "item_id": item_id,
            "operation": operation,
            "tag": tag,
            "tags": tags
        }
        return self._post(f"/api/projects/{project_id}/items/{item_id}/tags", params=data)

    # ===================
    # Tag APIs
    # ===================

    def tag_register(
        self,
        project_id: str,
        tag_name: str,
        summary: str,
        aliases: str = ""
    ) -> ApiResponse:
        """注册项目标签."""
        data = {"project_id": project_id, "tag_name": tag_name, "summary": summary, "aliases": aliases}
        return self._post("/api/tags/register", params=data)

    def tag_update(
        self,
        project_id: str,
        tag_name: str,
        summary: Optional[str] = None
    ) -> ApiResponse:
        """更新已注册标签."""
        data = {"project_id": project_id, "tag_name": tag_name, "summary": summary}
        data = {k: v for k, v in data.items() if v is not None}
        return self._put("/api/tags/update", params=data)

    def tag_delete(
        self,
        project_id: str,
        tag_name: str,
        force: str = "false"
    ) -> ApiResponse:
        """删除标签注册."""
        data = {"project_id": project_id, "tag_name": tag_name, "force": force}
        return self._delete("/api/tags/delete", params=data)

    def tag_merge(
        self,
        project_id: str,
        old_tag: str,
        new_tag: str
    ) -> ApiResponse:
        """合并标签."""
        data = {"project_id": project_id, "old_tag": old_tag, "new_tag": new_tag}
        return self._post("/api/tags/merge", params=data)

    # ===================
    # Stats APIs
    # ===================

    def project_stats(self) -> ApiResponse:
        """获取全局统计信息."""
        return self._get("/api/stats")

    def stats_summary(
        self,
        type: str = "",
        tool_name: str = "",
        project_id: str = "",
        date: str = ""
    ) -> ApiResponse:
        """获取统计摘要."""
        params = {"type": type, "tool_name": tool_name, "project_id": project_id, "date": date}
        return self._get("/api/stats/summary", params=params)

    def stats_cleanup(self, retention_days: int = 30) -> ApiResponse:
        """清理过期统计数据."""
        return self._delete("/api/stats/cleanup", params={"retention_days": retention_days})

    # ===================
    # Group APIs
    # ===================

    def create_custom_group(
        self,
        project_id: str,
        group_name: str,
        content_max_bytes: int = 240,
        summary_max_bytes: int = 90,
        allow_related: bool = False,
        allowed_related_to: str = "",
        enable_status: bool = True,
        enable_severity: bool = False
    ) -> ApiResponse:
        """创建自定义组."""
        data = {
            "project_id": project_id,
            "group_name": group_name,
            "content_max_bytes": content_max_bytes,
            "summary_max_bytes": summary_max_bytes,
            "allow_related": allow_related,
            "allowed_related_to": allowed_related_to,
            "enable_status": enable_status,
            "enable_severity": enable_severity
        }
        return self._post("/api/groups/custom", params=data)

    def update_group(
        self,
        project_id: str,
        group_name: str,
        content_max_bytes: Optional[int] = None,
        summary_max_bytes: Optional[int] = None,
        allow_related: Optional[bool] = None,
        allowed_related_to: Optional[str] = None,
        enable_status: Optional[bool] = None,
        enable_severity: Optional[bool] = None
    ) -> ApiResponse:
        """更新组配置."""
        data = {"project_id": project_id, "group_name": group_name}
        for k, v in [("content_max_bytes", content_max_bytes), ("summary_max_bytes", summary_max_bytes),
                     ("allow_related", allow_related), ("allowed_related_to", allowed_related_to),
                     ("enable_status", enable_status), ("enable_severity", enable_severity)]:
            if v is not None:
                data[k] = v
        return self._put("/api/groups/custom", params=data)

    def delete_custom_group(self, project_id: str, group_name: str) -> ApiResponse:
        """删除自定义组."""
        params = {"project_id": project_id, "group_name": group_name}
        return self._delete("/api/groups/custom", params=params)

    def get_group_settings(self, project_id: str) -> ApiResponse:
        """获取组设置."""
        return self._get("/api/groups/settings", params={"project_id": project_id})

    def update_group_settings(
        self,
        project_id: str,
        default_related_rules: Optional[Dict] = None
    ) -> ApiResponse:
        """更新组设置."""
        data = {"project_id": project_id, "default_related_rules": default_related_rules}
        return self._put("/api/groups/settings", params=data)


# 全局客户端实例
_client: Optional[BusinessApiClient] = None


def get_business_client() -> BusinessApiClient:
    """获取全局 Business API 客户端实例."""
    global _client
    if _client is None:
        _client = BusinessApiClient()
    return _client


def close_business_client():
    """关闭全局 Business API 客户端."""
    global _client
    if _client:
        _client.close()
        _client = None
