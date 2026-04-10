"""
常量定义模块

本模块定义项目中使用的所有常量，包括：
- 字段名常量
- 错误消息模板
- 成功消息模板
- 状态值常量
- 严重程度常量
- 操作模式常量
- 视图模式常量
- 默认值常量
- 正则表达式模式
"""


class FieldNames:
    """常用字段名常量"""
    # API 响应字段
    SUCCESS = "success"
    ERROR = "error"
    MESSAGE = "message"
    DATA = "data"

    # 项目元数据字段
    VERSION = "_version"
    VERSIONS = "_versions"
    TAG_REGISTRY = "tag_registry"
    INFO = "info"

    # 分组名
    FEATURES = "features"
    FIXES = "fixes"
    NOTES = "notes"
    STANDARDS = "standards"


class ErrorMessages:
    """错误消息模板"""
    # 资源不存在
    PROJECT_NOT_FOUND = "项目 '{project_id}' 不存在"
    GROUP_NOT_FOUND = "分组 '{group_name}' 不存在"
    ITEM_NOT_FOUND = "在分组 '{group}' 中找不到条目 '{item_id}'"
    TAG_NOT_REGISTERED = "标签 '{tag_name}' 未注册"
    ITEM_ID_NOT_EXISTS = "条目ID '{item_id}' 不存在"

    # 操作失败
    SAVE_FAILED = "保存数据失败"
    SAVE_CONFIG_FAILED = "保存配置失败"
    CONFIG_FORMAT_ERROR = "配置格式错误: {error}"

    # 参数验证
    PARAMETER_REQUIRED = "{param} 参数不能为空"

    # 验证错误
    INVALID_STATUS = "无效的 status 值: {status} (有效值: {valid_values})"
    INVALID_SEVERITY = "无效的 severity 值: {severity} (有效值: {valid_values})"
    CONTENT_TOO_LONG = "内容过长：{bytes} 字节，最大允许 {max_bytes} 字节"
    SUMMARY_TOO_LONG = "摘要过长：{bytes} 字节，最大允许 {max_bytes} 字节"


class SuccessMessages:
    """成功消息模板"""
    PROJECT_REGISTERED = "项目 '{name}' 已成功注册，ID: {project_id}"
    ITEM_ADDED = "条目 '{item_id}' 已添加到 '{group}' 分组"
    ITEM_UPDATED = "条目 '{item_id}' 已更新"
    ITEM_DELETED = "条目 '{item_id}' 已删除"
    TAG_REGISTERED = "标签 '{tag_name}' 已成功注册"
    TAG_UPDATED = "标签 '{tag_name}' 已更新"
    TAG_DELETED = "标签 '{tag_name}' 已删除"
    CONFIG_UPDATED = "组 '{group}' 配置已更新"


class StatusValues:
    """状态值常量"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

    @classmethod
    def all(cls) -> list[str]:
        """返回所有有效的状态值"""
        return [cls.PENDING, cls.IN_PROGRESS, cls.COMPLETED]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """检查状态值是否有效"""
        return value in cls.all()


class SeverityValues:
    """严重程度常量"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def all(cls) -> list[str]:
        """返回所有有效的严重程度值"""
        return [cls.CRITICAL, cls.HIGH, cls.MEDIUM, cls.LOW]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """检查严重程度值是否有效"""
        return value in cls.all()


class OperationModes:
    """操作模式常量"""
    ARCHIVE = "archive"
    DELETE = "delete"


class ViewModes:
    """视图模式常量"""
    SUMMARY = "summary"
    DETAIL = "detail"


class Defaults:
    """默认值常量"""
    INITIAL_VERSION = 1
    INITIAL_USAGE_COUNT = 0
    INITIAL_ALIASES: list = []
    DEFAULT_SEVERITY = "medium"
    DEFAULT_STATUS = "pending"
    DEFAULT_VIEW_MODE = "summary"
    DEFAULT_OPERATION_MODE = "archive"
    DEFAULT_PAGE = 1
    DEFAULT_SIZE = 0  # 0 表示使用服务器默认值


class Patterns:
    """正则表达式模式常量"""
    TAG_NAME = r'^[a-zA-Z0-9_-]{1,30}$'
    ITEM_ID = r'^([a-z]+)_([0-9]{8})_([0-9]+)$'
    TAG_FORMAT = r'^[a-z0-9_-]+$'
