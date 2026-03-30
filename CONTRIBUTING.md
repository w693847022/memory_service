# 贡献指南

感谢你对 AI Memory MCP 项目的关注！

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 在 Issues 中搜索是否已有相关问题
2. 如果没有，创建新 Issue，包含：
   - 清晰的标题
   - 复现步骤
   - 期望行为 vs 实际行为
   - 环境信息（Python 版本、操作系统等）

### 提交功能建议

1. 在 Issues 中描述你建议的功能
2. 说明使用场景和预期效果
3. 等待讨论和反馈

### 提交代码

1. **Fork** 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. **测试** 确保代码通过测试 (`./scripts/run_tests.sh`)
4. **提交** 更改 (`git commit -m 'Add some AmazingFeature'`)
5. **推送** 到分支 (`git push origin feature/AmazingFeature`)
6. 开启 **Pull Request**

## 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用类型注解
- 函数添加 docstring 说明

### 提交信息规范

使用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：
```
feat(storage): 添加项目数据备份功能

- 实现自动备份机制
- 支持手动触发备份
- 添加备份列表查询接口

Closes #123
```

## 开发环境

### 环境配置

项目使用 conda 管理依赖：

```bash
# 创建并激活 conda 环境
conda create -n ai_memory_mcp python=3.12
conda activate ai_memory_mcp

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-test.txt      # 测试依赖
pip install -r requirements-fastapi.txt   # REST API 依赖
```

### 运行测试

使用统一的测试脚本：

```bash
# 默认运行所有单元测试
./scripts/run_tests.sh

# 只运行 MCP 接口测试
./scripts/run_tests.sh -m

# 只运行 REST API 测试
./scripts/run_tests.sh -r

# 生成覆盖率报告
./scripts/run_tests.sh -c

# 详细输出
./scripts/run_tests.sh -v

# 查看所有选项
./scripts/run_tests.sh -h
```

测试脚本会自动激活 `ai_memory_mcp` conda 环境。

### 启动开发服务器

```bash
# MCP 服务器
python run.py

# REST API 服务器
python run_fastapi.py
```

## 行为准则

- 尊重不同观点和经验
- 使用包容性语言
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心
