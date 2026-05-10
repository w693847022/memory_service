# Features - ai_memory_server v1.0.0

## API 接口

- **项目管理**: 注册/列表/查询/重命名/归档项目，支持分页、名称正则过滤、view_mode
- **项目信息修改**: 支持更新项目摘要、标签和路径
- **项目删除/归档**: 拆分为独立接口，激活项目只能归档，归档项目才能删除
- **条目管理**: 统一 add/update/delete 接口，支持 content/summary/status/severity/related/tags
- **条目查询**: 支持 summary 正则过滤、时间范围过滤、分页、view_mode 精简模式
- **标签查询**: project_tags_info 增加分页/过滤/view_mode，支持标签名正则过滤
- **关联系统**: API 层支持 related 字典格式和多条目关联参数

## 分组管理

- **自定义组**: 支持创建自定义分组，配置 content_max_bytes/summary_max_bytes/max_tags 等
- **分组配置**: 支持默认配置与用户配置合并，单组操作和完整配置查询
- **访问控制**: 分组级别 mcp_access 访问控制（writable/readable/disabled）
- **frontend_ 前缀**: 支持前端专用分组（仅通过 REST API 创建）
- **组描述**: 为组配置添加 description 字段
- **标签限制**: 组级别 max_items 和标签数量限制配置

## 存储与缓存

- **拆分文件存储**: 按项目/分组拆分文件结构，移除全局 IO 锁
- **版本控制(CAS)**: 实现版本控制和并发锁机制
- **智能缓存**: 分层缓存系统（内存 → 磁盘），热点自动升级
- **乐观锁管理**: 四层乐观锁管理器，支持并发控制

## 并发与架构

- **阻挡位系统**: 五层阻挡位装饰器系统，全异步架构重构
- **三层架构**: MCP Server / FastAPI Server / Business Server 分离
- **HTTP 连接池**: 客户端连接池优化
- **完全异步化**: REST API 层异步化改造

## 模型与配置

- **Pydantic 模型**: 统一模型目录，从 dataclass 迁移到 Pydantic 模型
- **聚合模型**: ProjectData 聚合模型贯穿存储/缓存/业务层
- **动态验证**: 移除硬编码长度限制，使用组配置动态验证
- **外部配置**: 支持通过配置文件自定义初始标签和关联规则

## REST API 层

- **FastAPI 服务**: 为前端提供 HTTP 接口
- **速率限制**: 请求速率限制、请求追踪和日志滚动
- **异步调用**: FastAPI 通过 HTTP 调用 MCP Server

## MCP 工具

- **MCP Resource**: 注册指南为 MCP Resource，支持 AI 客户端自然发现
- **指南规范**: 新增 content 书写规范，更新过时指南信息

## 部署与运维

- **Docker 配置**: 数据路径配置化和 Windows 兼容
- **init 命令**: Docker init 命令初始化日志目录
- **日志配置**: 完善三个服务的日志配置

## 用户体验

- **超长内容提示**: 增加超长内容提示建议建立 note
- **错误提示**: 优化内容长度超限错误提示格式
