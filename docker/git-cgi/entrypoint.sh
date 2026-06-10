#!/bin/sh
# =============================================================================
# git-cgi 容器入口点
#
# 启动 fcgiwrap 并通过 spawn-fcgi 绑定到 TCP 端口，
# 使 Nginx 可以通过 fastcgi_pass 将 Git HTTP 请求转发过来。
# =============================================================================

set -e

# 验证 git-http-backend 可执行文件存在
if [ ! -x "$GIT_BACKEND_CMD" ]; then
    echo "ERROR: git-http-backend not found at $GIT_BACKEND_CMD"
    echo "Available git-core executables:"
    ls /usr/libexec/git-core/ 2>/dev/null || echo "(none found)"
    exit 1
fi

# 验证仓库目录存在
if [ ! -d "$GIT_PROJECT_ROOT" ]; then
    echo "Creating GIT_PROJECT_ROOT: $GIT_PROJECT_ROOT"
    mkdir -p "$GIT_PROJECT_ROOT"
fi

echo "=== git-cgi starting ==="
echo "Git backend: $GIT_BACKEND_CMD"
echo "Project root: $GIT_PROJECT_ROOT"
echo "Listening on port: $FCGI_PORT"
echo "Export all: $GIT_HTTP_EXPORT_ALL"
echo "========================"

# 启动 fcgiwrap 并通过 spawn-fcgi 绑定到 TCP 端口
# -a <address> -p <port>  绑定到 TCP 地址和端口
# -n                      保持前台运行（容器主进程）
# -f -c 4                 fork 4 个子进程处理并发请求
exec spawn-fcgi -n -a "0.0.0.0" -p "${FCGI_PORT}" -C 4 -- "$(which fcgiwrap)" -f
