# 单元测试目录说明

本目录包含按 MCP 接口组织的单元测试文件，每个文件测试一个 MCP 接口的所有边界情况。

## 测试文件组织结构

```
test/unit/
├── MCP 接口测试文件 (按接口组织)
│   ├── test_mcp_project_register.py       # project_register 接口测试
│   ├── test_mcp_project_add.py            # project_add 接口测试
│   ├── test_mcp_project_update.py         # project_update 接口测试
│   ├── test_mcp_project_delete.py         # project_delete 接口测试
│   ├── test_mcp_project_get.py            # project_get 接口测试
│   ├── test_mcp_project_list.py           # project_list 接口测试
│   ├── test_mcp_project_tags_info.py      # project_tags_info 接口测试
│   ├── test_mcp_project_item_tag_manage.py # project_item_tag_manage 接口测试
│   ├── test_mcp_project_operations.py     # project_remove, project_rename, project_groups_list, project_stats
│   ├── test_mcp_tag_operations.py         # tag_register, tag_update, tag_delete, tag_merge
│   └── test_mcp_stats.py                  # stats_summary, stats_cleanup
│
├── REST API 测试
│   └── test_rest_api/
│       ├── test_api_projects.py           # 项目管理 API
│       ├── test_api_groups.py             # 分组管理 API
│       ├── test_api_tags.py               # 标签管理 API
│       ├── test_api_stats.py              # 统计 API
│       └── test_api_errors.py             # 错误处理测试
│
└── 其他测试文件
    ├── test_callstats.py                  # CallStats 类单元测试
    ├── test_imports.py                    # 导入检查测试
    └── test_utils.py                      # 工具函数单元测试
```

## MCP 接口与测试文件映射

| MCP 接口 | 测试文件 | 说明 |
|---------|---------|------|
| project_register | test_mcp_project_register.py | 注册项目 |
| project_rename | test_mcp_project_operations.py | 重命名项目 |
| project_list | test_mcp_project_list.py | 列出项目 |
| project_groups_list | test_mcp_project_operations.py | 列出分组 |
| project_tags_info | test_mcp_project_tags_info.py | 查询标签信息 |
| project_add | test_mcp_project_add.py | 添加条目 |
| project_update | test_mcp_project_update.py | 更新条目 |
| project_delete | test_mcp_project_delete.py | 删除条目 |
| project_item_tag_manage | test_mcp_project_item_tag_manage.py | 管理条目标签 |
| project_remove | test_mcp_project_operations.py | 归档/删除项目 |
| project_get | test_mcp_project_get.py | 获取项目/条目 |
| project_stats | test_mcp_project_operations.py | 获取统计 |
| tag_register | test_mcp_tag_operations.py | 注册标签 |
| tag_update | test_mcp_tag_operations.py | 更新标签 |
| tag_delete | test_mcp_tag_operations.py | 删除标签 |
| tag_merge | test_mcp_tag_operations.py | 合并标签 |
| stats_summary | test_mcp_stats.py | 统计摘要 |
| stats_cleanup | test_mcp_stats.py | 清理统计 |

## 运行测试

使用项目根目录的统一测试脚本：

```bash
# 从项目根目录运行
./scripts/run_tests.sh        # 所有单元测试
./scripts/run_tests.sh -m      # MCP 接口测试
./scripts/run_tests.sh -r      # REST API 测试
./scripts/run_tests.sh -c      # 生成覆盖率报告
./scripts/run_tests.sh -h      # 查看帮助
```

测试脚本会自动激活 `ai_memory_mcp` conda 环境。

## 测试覆盖的边界情况

每个 MCP 接口测试文件包含以下测试类别：

1. **基础功能测试** - 验证正常使用场景
2. **必填参数验证** - 测试缺少必填参数的情况
3. **参数格式验证** - 测试无效的参数值
4. **边界值测试** - 测试参数的边界值
5. **特殊字符处理** - 测试特殊字符、Unicode 等
6. **错误场景测试** - 测试各种错误情况
7. **并发安全测试** - 测试并发操作
8. **响应格式测试** - 验证响应数据格式

## 测试文件命名规范

- `test_mcp_{interface_name}.py` - 单个 MCP 接口测试
- `test_mcp_{category}_operations.py` - 多个相关操作接口
- `test_api_{module}.py` - REST API 测试
- `test_{module}.py` - 非 MCP 接口模块测试

## 已完成的测试文件清单

### 项目管理接口 (4个)
1. `test_mcp_project_register.py` - project_register (28 测试用例)
2. `test_mcp_project_list.py` - project_list (15 测试用例)
3. `test_mcp_project_get.py` - project_get (20 测试用例)
4. `test_mcp_project_operations.py` - project_remove, project_rename, project_groups_list, project_stats (16 测试用例)

### 条目管理接口 (5个)
5. `test_mcp_project_add.py` - project_add (26 测试用例)
6. `test_mcp_project_update.py` - project_update (27 测试用例)
7. `test_mcp_project_delete.py` - project_delete (17 测试用例)
8. `test_mcp_project_tags_info.py` - project_tags_info (20 测试用例)
9. `test_mcp_project_item_tag_manage.py` - project_item_tag_manage (15 测试用例)

### 标签管理接口 (1个)
10. `test_mcp_tag_operations.py` - tag_register, tag_update, tag_delete, tag_merge (22 测试用例)

### 统计接口 (1个)
11. `test_mcp_stats.py` - stats_summary, stats_cleanup (16 测试用例)

### REST API 测试 (5个)
12. `test_rest_api/test_api_projects.py` - 项目管理 API (13 测试用例)
13. `test_rest_api/test_api_groups.py` - 分组管理 API (10 测试用例)
14. `test_rest_api/test_api_tags.py` - 标签管理 API (10 测试用例)
15. `test_rest_api/test_api_stats.py` - 统计 API (9 测试用例)
16. `test_rest_api/test_api_errors.py` - 错误处理 (6 测试用例)

## 测试统计

| 类别 | 测试数 | 覆盖率 |
|------|--------|--------|
| MCP 接口测试 | 253 | 85%+ |
| REST API 测试 | 61 | 99% |
| 其他测试 | 15 | - |
| **总计** | **329** | **85%** |

## 注意事项

1. 所有测试使用 `pytest` 框架
2. 测试使用 `tempfile.mkdtemp()` 创建临时目录，测试后自动清理
3. MCP 测试使用 `unittest.mock.patch` 来 mock api.tools.memory
4. REST API 测试使用 `fastapi.testclient.TestClient`
5. 测试结果以 JSON 格式解析验证
6. 每个测试类包含相关的测试方法，按功能分组
