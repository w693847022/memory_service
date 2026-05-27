# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [v1.0.1] - 2026-05-27

### Added
- **related**: 条目关联支持同组内条目，增加存在性与自引用校验

### Fixed
- **mcp**: project_add/project_update content 参数支持 dict/list 并确保 unicode 可读
- **mcp, client**: project_add/project_update content dict 自动转换为 JSON string
- **project**: 自定义组条目ID生成支持小写转换及重名检查大小写不敏感
- **storage**: 自定义组条目ID生成支持大小写不敏感的group key查找

## [1.0.0] - 2026-05-09

### Added
- **resource**: 注册指南为 MCP Resource，支持 AI 客户端自然发现和访问
- **guidelines**: 新增 content 书写规范并同步更新过时指南信息
- **project**: 新增项目信息修改功能，支持更新摘要、标签和路径
- **api**: 拆分项目删除和归档为独立接口，MCP 仅允许归档
- **groups**: 增加 frontend_ 前缀自定义组和 max_items 设置
- **groups**: 增加分组级别的 mcp_access 访问控制
- **group**: 为组配置添加 description 字段并优化删除行为提示
- **config**: 支持通过配置文件自定义初始标签和关联规则
- **groups**: 默认组配置和初始配置支持外部配置化
- **groups**: 添加组标签数量限制配置
- **models**: 统一模型设计，ProjectData 聚合模型贯穿存储/缓存/业务层
- **models**: 统一模型目录，迁移所有 dataclass 到 Pydantic 模型
- **models**: 移除 Item 模型硬编码长度限制，使用组配置动态验证
- **groups**: 增强分组配置管理，支持默认配置与用户配置合并
- **groups**: 增强分组配置管理，支持单组操作和完整配置查询
- **barrier**: 实现阻挡位装饰器系统并迁移服务层
- **storage**: 实现拆分文件存储结构，移除全局 IO 锁
- **cache**: 实现智能分层缓存系统与热点自动升级
- **rest-api**: 实现完全异步化改造
- **clients**: 实现 HTTP 客户端连接池优化
- **concurrency**: 实现五层阻挡位系统与全异步架构重构
- **concurrency**: 实现四层乐观锁管理器
- **storage**: 实现版本控制(CAS)和并发锁机制
- **docker**: 添加 init 命令初始化日志目录
- **logging**: 完善三个服务的日志配置
- **三层架构重构**: 实现步骤 1.7-1.12
- **business**: 实现 tag_service, stats_service, storage 业务服务
- **project**: 新增自定义组及组设置功能
- **rest-api**: 添加速率限制、请求追踪和日志滚动功能
- **rest-api**: FastAPI 服务改为通过 HTTP 调用 MCP Server
- **rest-api**: 新增 FastAPI REST API 层，为前端提供 HTTP 接口
- **api**: project_tags_info 增加分页/过滤/view_mode 功能并重构通用工具函数
- **api**: 新增项目删除/归档接口 project_remove
- **api**: project_get 增加 summary 正则过滤和时间范围过滤
- **api**: project_list 添加 view_mode/page/size/name_pattern 参数
- **api**: project_get 添加 view_mode 参数减少 token 消耗
- **api**: API 层支持 related 参数字典格式
- **api**: API 层支持多条目关联参数
- **ux**: 增加超长内容提示建议建立 note
- **api**: 统一 add/update/delete 接口为 add_item/update_item/delete_item
- **api**: project_get 仅传入项目 ID 时返回精简概览
- **notes**: 将 notes 内容上限从 500 提升至 1000 tokens
- **storage**: 优化内容长度超限错误提示格式
- **docker**: 优化 Docker 配置支持数据路径配置化和 Windows 兼容
- 统一模型与分组服务重构，规范日志输出，精简部署脚本

### Fixed
- **project**: 完善项目归档元数据保留时间字段和注册标签名校验
- **api**: 项目列表接口 detail 模式下返回创建时间和更新时间
- **api**: 完善项目删除流程，激活项目只能归档、归档项目才能删除
- **docker**: 将 config 目录添加到 Docker 镜像和卷挂载中
- **storage**: 移除 CONTENT_SEPARATE_GROUPS 硬编码，统一所有分组 content 独立存储
- **custom-group**: 修复自定义组条目 ID 生成不唯一的问题
- **tags**: 移除 TagService 中硬编码 GroupType.values() 校验
- **api**: 移除 REST API 和 Business API 的硬编码分组校验
- **rest_api**: 规范化请求/响应模型，修复接口文档返回结构不清晰问题
- **storage**: 修复项目重命名时旧目录未归档和缓存导致目录重建问题
- **project_service**: 修复 status/severity 验证逻辑硬编码问题
- **project_service**: 写入层兜底过滤分组不支持的字段值
- **validation**: 修复更新条目时缺少 status 和 severity 验证
- **groups**: 修复组配置更新缺少部分配置项的问题
- **api**: 修复 project_update 接口 related 参数序列化问题
- **api**: 修复 project_update status/severity 参数无法更新问题
- **rest_api**: 调整路由顺序修复自定义组接口匹配问题
- **tags**: 注册项目时始终注册 DEFAULT_TAGS 默认标签
- **imports**: 修复 call_stats 的错误导入路径
- **imports**: 修复 memory 和 call_stats 的错误导入路径
- **pyright**: 修复类型注解错误，符合 PEP 484 规范
- **api**: 同步 project_update 与 project_add 的 content 长度限制
- **storage**: 注册项目时自动生成默认标签
- **api,storage**: 修复 features/fixes 分组 content/description 字段映射错误
- 修复 standards 分组 ID 生成重复问题
- Potential fix for code scanning alert no. 1: Information exposure through an exception
- **skills**: 修复 do-fix 技能配置错误并增强验证流程
- **skill**: 优化 feature-dev-s 技能和修复相关小问题
- **test_smart_cache**: 更新测试以适配 CacheConfig 嵌套结构

### Changed
- **三层架构重构**: 实现三层架构分离（MCP Server / FastAPI Server / Business Server）
- 统一模型与分组服务重构，规范日志输出，精简部署脚本

### Chore
- **docs**: 重构项目文档并优化部署配置
- **chore**: 清理未使用的配置文件
- **chore**: 删除 test 目录下所有测试文件
