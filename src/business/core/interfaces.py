"""Service Interface Definitions - 服务接口抽象层.

使用 Protocol 方式定义服务接口，实现解耦和依赖倒置。
"""

from typing import Protocol, Optional, List, Dict, Any, Union

from src.models.group import UnifiedGroupConfig


class ProjectServiceInterface(Protocol):
    """项目管理服务接口.

    定义项目管理和条目操作的核心方法签名。
    """

    def register_project(
        self,
        name: str,
        path: Optional[str] = None,
        summary: str = "",
        tags: Optional[List[str]] = None,
        git_remote: Optional[str] = None,
        git_remote_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """注册新项目.

        Args:
            name: 项目名称
            path: 项目路径（可选）
            summary: 项目摘要（可选）
            tags: 项目标签列表（可选）
            git_remote: Git 远程名称（可选）
            git_remote_url: Git 远程 URL（可选）

        Returns:
            操作结果
        """
        ...

    def list_projects(self, include_archived: bool = False) -> Dict[str, Any]:
        """列出所有项目.

        Args:
            include_archived: 是否包含归档项目

        Returns:
            项目列表
        """
        ...

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息.

        Args:
            project_id: 项目ID

        Returns:
            项目信息
        """
        ...

    def project_rename(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """重命名项目（修改 name 字段并重命名目录）.

        Args:
            project_id: 项目 UUID
            new_name: 新的项目名称

        Returns:
            操作结果
        """
        ...

    def remove_project(self, project_id: str, mode: str = "archive") -> Dict[str, Any]:
        """归档或永久删除项目.

        Args:
            project_id: 项目ID
            mode: 操作模式 - "archive"(归档) 或 "delete"(永久删除)

        Returns:
            操作结果
        """
        ...

    def list_groups(self, project_id: str) -> Dict[str, Any]:
        """列出项目的所有分组.

        Args:
            project_id: 项目ID

        Returns:
            分组列表及统计信息
        """
        ...

    def validate_add_item(
        self,
        group: str,
        content: str,
        summary: str,
        status: Optional[str],
        severity: str,
        related: Optional[Union[str, Dict[str, List[str]]]],
        tag_list: List[str],
        custom_groups: Optional[Dict[str, UnifiedGroupConfig]] = None,
        default_rules: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """统一验证添加条目的所有参数.

        Args:
            group: 分组类型
            content: 条目内容
            summary: 条目摘要
            status: 状态（可选）
            severity: 严重程度
            related: 关联数据
            tag_list: 标签列表
            custom_groups: 自定义组配置字典（可选）
            default_rules: 默认关联规则（可选）

        Returns:
            验证结果
        """
        ...

    def validate_update_item(
        self,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        related: Optional[Union[str, Dict[str, List[str]]]] = None,
        custom_groups: Optional[Dict[str, UnifiedGroupConfig]] = None,
        default_rules: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """统一验证更新条目参数.

        Args:
            group: 分组类型
            item_id: 条目ID
            content: 新内容（可选）
            summary: 新摘要（可选）
            related: 关联数据（可选）
            custom_groups: 自定义组配置字典（可选）
            default_rules: 默认关联规则（可选）

        Returns:
            验证结果
        """
        ...

    def add_item(
        self,
        project_id: str,
        group: str,
        content: str,
        summary: str,
        status: Optional[str] = None,
        severity: str = "medium",
        related: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """添加项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            content: 条目内容
            summary: 条目摘要
            status: 状态（可选）
            severity: 严重程度（可选）
            related: 关联数据（可选）
            tags: 标签列表（可选）

        Returns:
            操作结果
        """
        ...

    def update_item(
        self,
        project_id: str,
        group: str,
        item_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        related: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """更新项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            item_id: 条目ID
            content: 内容更新（可选）
            summary: 摘要更新（可选）
            status: 状态更新（可选）
            severity: 严重程度更新（可选）
            related: 关联更新（可选）
            tags: 标签更新（可选）

        Returns:
            操作结果
        """
        ...

    def delete_item(
        self,
        project_id: str,
        group: str,
        item_id: str
    ) -> Dict[str, Any]:
        """删除项目条目.

        Args:
            project_id: 项目ID
            group: 分组类型
            item_id: 条目ID

        Returns:
            操作结果
        """
        ...


class TagServiceInterface(Protocol):
    """标签管理服务接口.

    定义标签注册、更新、删除、合并和查询的方法签名。
    """

    def register_tag(
        self,
        project_id: str,
        tag_name: str,
        summary: str,
        aliases: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """注册新标签到项目标签库.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            summary: 标签语义摘要（10-200字符）
            aliases: 别名列表（可选）

        Returns:
            操作结果
        """
        ...

    def update_tag(
        self,
        project_id: str,
        tag_name: str,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新已注册标签的语义信息.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            summary: 新的摘要（可选）

        Returns:
            操作结果
        """
        ...

    def delete_tag(
        self,
        project_id: str,
        tag_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """删除标签注册.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            force: 是否强制删除（即使标签正在使用）

        Returns:
            操作结果
        """
        ...

    def merge_tags(
        self,
        project_id: str,
        old_tag: str,
        new_tag: str
    ) -> Dict[str, Any]:
        """合并标签：将所有 old_tag 的引用迁移到 new_tag.

        Args:
            project_id: 项目ID
            old_tag: 旧标签名称（将被删除）
            new_tag: 新标签名称（合并目标）

        Returns:
            操作结果
        """
        ...

    def list_all_registered_tags(self, project_id: str) -> Dict[str, Any]:
        """列出项目中所有已注册的标签.

        Args:
            project_id: 项目ID

        Returns:
            所有已注册标签的列表
        """
        ...

    def list_unregistered_tags(
        self,
        project_id: str,
        group_name: str
    ) -> Dict[str, Any]:
        """列出指定分组下所有未注册的标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称

        Returns:
            未注册标签列表
        """
        ...

    def list_group_tags(
        self,
        project_id: str,
        group_name: str
    ) -> Dict[str, Any]:
        """列出指定分组下的所有标签及使用次数.

        Args:
            project_id: 项目ID
            group_name: 分组名称

        Returns:
            标签列表及每个标签的条目数量
        """
        ...

    def query_by_tag(
        self,
        project_id: str,
        group_name: str,
        tag: str
    ) -> Dict[str, Any]:
        """查询指定分组下某标签的所有条目.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            tag: 标签名称

        Returns:
            该标签下的所有条目列表
        """
        ...

    def add_item_tag(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        tag: str
    ) -> Dict[str, Any]:
        """为条目添加单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
            tag: 要添加的标签

        Returns:
            操作结果
        """
        ...

    def remove_item_tag(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        tag: str
    ) -> Dict[str, Any]:
        """从条目移除单个标签.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
            tag: 要移除的标签

        Returns:
            操作结果
        """
        ...
