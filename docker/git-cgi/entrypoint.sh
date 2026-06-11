#!/bin/sh
# =============================================================================
# git-cgi 容器入口点
#
# 启动 fcgiwrap 并通过 spawn-fcgi 绑定到 TCP 端口，
# 使 Nginx 可以通过 fastcgi_pass 将 Git HTTP 请求转发过来。
# =============================================================================

set -e

# 颜色定义（如果终端支持）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 验证 fcgiwrap 可执行文件存在
FCGIWRAP_BIN=$(which fcgiwrap)
if [ -z "$FCGIWRAP_BIN" ]; then
    log_error "fcgiwrap not found in PATH"
    exit 1
fi
log_info "fcgiwrap found: $FCGIWRAP_BIN"

# 验证 spawn-fcgi 可执行文件存在
SPAWN_FCGI_BIN=$(which spawn-fcgi)
if [ -z "$SPAWN_FCGI_BIN" ]; then
    log_error "spawn-fcgi not found in PATH"
    exit 1
fi
log_info "spawn-fcgi found: $SPAWN_FCGI_BIN"

# 验证 git-http-backend 可执行文件存在
if [ ! -x "$GIT_BACKEND_CMD" ]; then
    log_error "git-http-backend not found at $GIT_BACKEND_CMD"
    log_info "Searching for git-http-backend in common locations..."

    # 尝试在其他常见位置查找 (Debian/Ubuntu: /usr/lib/git-core/, Alpine: /usr/libexec/git-core/)
    for path in /usr/lib/git-core/git-http-backend \
                /usr/libexec/git-core/git-http-backend \
                /usr/bin/git-http-backend; do
        if [ -x "$path" ]; then
            log_info "Found git-http-backend at: $path"
            GIT_BACKEND_CMD="$path"
            export GIT_BACKEND_CMD
            break
        fi
    done

    # 如果还是没找到，列出可用的 git 命令
    if [ ! -x "$GIT_BACKEND_CMD" ]; then
        log_error "git-http-backend not found in any standard location"
        log_info "Available git executables in /usr/libexec/git-core/:"
        ls /usr/libexec/git-core/ 2>/dev/null | head -30 || echo "(directory not found)"
        exit 1
    fi
fi

log_info "git-http-backend found: $GIT_BACKEND_CMD"

# 验证仓库目录存在
if [ ! -d "$GIT_PROJECT_ROOT" ]; then
    log_warn "GIT_PROJECT_ROOT does not exist, creating: $GIT_PROJECT_ROOT"
    mkdir -p "$GIT_PROJECT_ROOT"
fi
log_info "Project root: $GIT_PROJECT_ROOT"

# 检查端口是否被占用
if netstat -tuln 2>/dev/null | grep -q ":$FCGI_PORT "; then
    log_error "Port $FCGI_PORT is already in use"
    netstat -tuln | grep ":$FCGI_PORT "
    exit 1
fi

# 输出启动信息
echo "========================================"
echo "  Perseus Git CGI Server"
echo "========================================"
echo "  Git backend:  $GIT_BACKEND_CMD"
echo "  Project root: $GIT_PROJECT_ROOT"
echo "  Listen port:  $FCGI_PORT"
echo "  Export all:   $GIT_HTTP_EXPORT_ALL"
echo "========================================"

# 测试 git-http-backend 是否可以执行
log_info "Testing git-http-backend..."
if ! "$GIT_BACKEND_CMD" --help 2>&1 | head -5; then
    log_warn "git-http-backend test returned non-zero (this may be normal)"
fi

# 启动 fcgiwrap 并通过 spawn-fcgi 绑定到 TCP 端口
# -a <address> -p <port>  绑定到 TCP 地址和端口
# -n                      保持前台运行（容器主进程）
# -C 4                     fork 4 个子进程处理并发请求
# -f                      fcgiwrap 前台模式

log_info "Starting fcgiwrap on port $FCGI_PORT..."

exec "$SPAWN_FCGI_BIN" \
    -n \
    -a "0.0.0.0" \
    -p "$FCGI_PORT" \
    -C 4 \
    -- "$FCGIWRAP_BIN" -f
