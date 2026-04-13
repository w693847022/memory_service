#!/bin/bash
# 测试运行脚本 - ai_memory_mcp

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 激活 conda 环境 (如果存在)
CONDA_ENV="ai_memory_mcp"
if [ -d "/home/wrs/miniconda3/envs/$CONDA_ENV" ] || [ -d "$HOME/miniconda3/envs/$CONDA_ENV" ]; then
    eval "$(conda shell.bash hook)" 2>/dev/null || true
    conda activate "$CONDA_ENV" 2>/dev/null || true
fi

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT"

# 默认参数
TEST_PATH="test"
VERBOSE=""
COVERAGE=""
TB="short"
PARALLEL=""
PYTEST_ARGS=""
MARKER=""

# 帮助信息
show_help() {
    cat << EOF
用法: $(basename "$0") [选项] [测试路径]

选项:
    -a, --all          运行所有测试 (包括集成测试)
    -u, --unit         只运行单元测试 (默认)
    -e, --e2e          运行端到端测试 (MCP + REST)
    -m, --mcp          只运行 MCP Server 端到端测试
    -r, --rest         只运行 REST API 端到端测试
    -i, --integration  只运行集成测试
    -v, --verbose      详细输出
    -c, --coverage     生成覆盖率报告
    -q, --quiet        简化输出 (无错误回溯)
    -p, --parallel     并行运行测试
    -h, --help         显示此帮助信息

示例:
    $(basename "$0")                    # 运行单元测试
    $(basename "$0") -e                 # 运行端到端测试
    $(basename "$0") -m -v              # MCP 端到端测试 + 详细输出
    $(basename "$0") -r -c              # REST API 端到端测试 + 覆盖率
    $(basename "$0") -c                 # 生成覆盖率报告
EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            TEST_PATH="test"
            shift
            ;;
        -u|--unit)
            TEST_PATH="test/unit"
            MARKER="not e2e"
            shift
            ;;
        -e|--e2e)
            TEST_PATH="test/e2e"
            MARKER="e2e"
            shift
            ;;
        -m|--mcp)
            TEST_PATH="test/e2e"
            MARKER="mcp"
            shift
            ;;
        -r|--rest)
            TEST_PATH="test/e2e"
            MARKER="rest"
            shift
            ;;
        -i|--integration)
            TEST_PATH="test/integration"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v -s"
            shift
            ;;
        -c|--coverage)
            COVERAGE="--cov --cov-report=term-missing --cov-report=html"
            shift
            ;;
        -q|--quiet)
            TB="no"
            shift
            ;;
        -p|--parallel)
            PARALLEL="-n auto"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        --)
            shift
            PYTEST_ARGS="$*"
            break
            ;;
        -*)
            # 传递给 pytest 的额外参数
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# 添加标记表达式
if [[ -n "$MARKER" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS -m $MARKER"
fi

# 构建 pytest 命令
PYTEST_CMD="pytest $TEST_PATH $VERBOSE $COVERAGE --tb=$TB $PARALLEL $PYTEST_ARGS"

# 显示运行信息
echo "=================================="
echo "测试路径: $TEST_PATH"
[[ -n "$VERBOSE" ]] && echo "详细模式: 是"
[[ -n "$COVERAGE" ]] && echo "覆盖率: 是"
[[ -n "$PARALLEL" ]] && echo "并行模式: 是"
echo "=================================="
echo

# 运行测试
eval "$PYTEST_CMD"
