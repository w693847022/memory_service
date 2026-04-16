#!/bin/bash
# Docker 管理脚本 - MCP Memory Server

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 显示使用说明
show_usage() {
    echo "MCP Memory Server Docker 管理脚本"
    echo ""
    echo "用法: ./manage.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start     启动服务"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  status    查看服务状态"
    echo "  logs      查看服务日志"
    echo "  init      初始化日志目录"
    echo "  build     重新构建镜像"
    echo "  shell     进入容器 shell"
    echo "  clean     清理容器和镜像"
    echo "  help      显示此帮助信息"
    echo ""
}

# 启动服务
start_service() {
    cd "$SCRIPT_DIR"
    echo "🚀 启动 MCP Memory Server..."
    docker-compose up -d
    sleep 2
    docker-compose ps
}

# 初始化日志目录
init_logs() {
    echo "🔧 初始化日志目录..."
    # 读取 .env 中的日志路径
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
    fi

    # 默认日志路径
    LOG_HOST_PATH="${LOG_HOST_PATH:-~/.project_memory_ai/logs}"
    # 展开波浪号
    LOG_HOST_PATH="${LOG_HOST_PATH/#\~/$HOME}"

    # 检查目录是否存在且有正确的所有权
    if [ -d "$LOG_HOST_PATH" ]; then
        OWNER=$(stat -c "%U:%G" "$LOG_HOST_PATH" 2>/dev/null || echo "unknown")
        CURRENT_USER=$(whoami)
        if [[ "$OWNER" == "root:"* ]] && [[ "$CURRENT_USER" != "root" ]]; then
            echo "⚠️  检测到日志目录权限问题 (当前: $OWNER)"
            echo "请手动修复权限:"
            echo "  sudo chown -R \$USER:\$USER $LOG_HOST_PATH"
            return 1
        fi
    fi

    # 创建日志子目录
    echo "创建日志目录: $LOG_HOST_PATH"
    mkdir -p "$LOG_HOST_PATH/business"
    mkdir -p "$LOG_HOST_PATH/mcp"
    mkdir -p "$LOG_HOST_PATH/fastapi"

    # 设置权限
    chmod 755 "$LOG_HOST_PATH" 2>/dev/null || true
    chmod 755 "$LOG_HOST_PATH/business" 2>/dev/null || true
    chmod 755 "$LOG_HOST_PATH/mcp" 2>/dev/null || true
    chmod 755 "$LOG_HOST_PATH/fastapi" 2>/dev/null || true

    echo "✅ 日志目录初始化完成"
    ls -la "$LOG_HOST_PATH"
}

# 停止服务
stop_service() {
    cd "$SCRIPT_DIR"
    echo "🛑 停止 MCP Memory Server..."
    docker-compose down
}

# 重启服务
restart_service() {
    cd "$SCRIPT_DIR"
    echo "🔄 重启 MCP Memory Server..."
    docker-compose restart
    sleep 2
    docker-compose ps
}

# 查看状态
show_status() {
    cd "$SCRIPT_DIR"
    echo "📊 服务状态:"
    echo ""
    docker-compose ps
    echo ""
    echo "🌐 端口监听:"
    docker-compose exec mcp-memory-server netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null || echo "无法查看端口信息"
}

# 查看日志
show_logs() {
    cd "$SCRIPT_DIR"
    docker-compose logs -f --tail=100
}

# 重新构建
rebuild() {
    cd "$SCRIPT_DIR"
    echo "🔨 重新构建镜像..."
    docker-compose build --no-cache
    echo "✅ 构建完成"
}

# 进入容器
enter_shell() {
    cd "$SCRIPT_DIR"
    echo "🐚 进入容器 shell..."
    docker-compose exec mcp-memory-server /bin/bash
}

# 清理
clean() {
    cd "$SCRIPT_DIR"
    echo "🧹 清理容器和镜像..."
    read -p "确定要清理吗? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --rmi all
        echo "✅ 清理完成"
    else
        echo "❌ 取消清理"
    fi
}

# 主逻辑
case "${1:-}" in
    start)
        start_service
        ;;
    init)
        init_logs
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    build)
        rebuild
        ;;
    shell)
        enter_shell
        ;;
    clean)
        clean
        ;;
    help|--help|-h|"")
        show_usage
        ;;
    *)
        echo "❌ 未知命令: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
