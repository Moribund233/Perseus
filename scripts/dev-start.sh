#!/bin/bash
# =============================================================================
# Perseus 开发环境启动脚本 (Bash - 用于 WSL/Linux)
#
# 功能:
#   - 检查环境变量配置
#   - 构建并启动 Docker 服务
#   - 提供常用命令快捷方式
#
# 使用方法:
#   ./scripts/dev-start.sh          # 启动所有服务
#   ./scripts/dev-start.sh build    # 强制重新构建镜像
#   ./scripts/dev-start.sh stop     # 停止服务
#   ./scripts/dev-start.sh logs     # 查看日志
#   ./scripts/dev-start.sh shell    # 进入后端容器
#   ./scripts/dev-start.sh clean    # 停止并清除所有数据
# =============================================================================

set -e

COMPOSE_FILE="docker-compose.dev.yml"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    if [ ! -f ".env" ]; then
        warn ".env 文件不存在"
        info "正在从 .env.dev 创建 .env..."
        cp .env.dev .env
        success ".env 文件已创建"
        warn "请编辑 .env 文件，设置 PERSEUS_SECURITY_SECRET_KEY 密钥后再启动"
        exit 1
    fi

    # 检查密钥是否已修改
    if grep -q "PERSEUS_SECURITY_SECRET_KEY=your-secret-key-here" .env; then
        error "请修改 .env 文件中的 PERSEUS_SECURITY_SECRET_KEY 密钥！"
        info "生成密钥命令: openssl rand -hex 32"
        exit 1
    fi
}

start() {
    info "检查环境配置..."
    check_env

    info "启动 Perseus 开发环境..."
    info "Docker Compose 文件: $COMPOSE_FILE"

    # 检查 Docker 是否运行
    if ! docker info > /dev/null 2>&1; then
        error "Docker 未运行，请先启动 Docker"
        exit 1
    fi

    # 构建并启动服务
    docker compose -f $COMPOSE_FILE up -d --build

    success "服务启动成功！"
    echo ""
    echo "访问地址:"
    echo "  - 前端:       http://localhost:5173 (请在 client/web 目录运行 pnpm dev)"
    echo "  - API 文档:   http://localhost:8080/docs"
    echo "  - API:        http://localhost:8080/api"
    echo "  - 数据库:     localhost:5432"
    echo ""
    echo "常用命令:"
    echo "  - 查看日志:   ./scripts/dev-start.sh logs"
    echo "  - 进入容器:   ./scripts/dev-start.sh shell"
    echo "  - 停止服务:   ./scripts/dev-start.sh stop"
    echo ""
    info "正在显示日志..."
    docker compose -f $COMPOSE_FILE logs -f
}

stop() {
    info "停止 Perseus 开发环境..."
    docker compose -f $COMPOSE_FILE down
    success "服务已停止"
}

logs() {
    info "显示服务日志..."
    docker compose -f $COMPOSE_FILE logs -f
}

shell() {
    info "进入后端容器..."
    docker compose -f $COMPOSE_FILE exec app bash
}

clean() {
    warn "这将停止服务并删除所有数据卷！"
    read -p "确认继续? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f $COMPOSE_FILE down -v
        success "环境已清理"
    else
        info "已取消"
    fi
}

rebuild() {
    info "强制重新构建镜像..."
    docker compose -f $COMPOSE_FILE build --no-cache
    success "镜像构建完成"
    start
}

# 主逻辑
case "${1:-start}" in
    start)
        start
        ;;
    build)
        rebuild
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    shell)
        shell
        ;;
    clean)
        clean
        ;;
    *)
        echo "Perseus 开发环境管理脚本"
        echo ""
        echo "用法: ./scripts/dev-start.sh [命令]"
        echo ""
        echo "命令:"
        echo "  start  - 启动开发环境 (默认)"
        echo "  build  - 重新构建镜像并启动"
        echo "  stop   - 停止服务"
        echo "  logs   - 查看日志"
        echo "  shell  - 进入后端容器"
        echo "  clean  - 停止并清除所有数据"
        ;;
esac
