# =============================================================================
# Perseus git-cgi 容器
#
# 功能：通过 fcgiwrap 提供 git-http-backend CGI 服务，
#       支持 Git HTTP Smart Protocol 的 clone/push/pull 操作。
#
# 架构：
#   Nginx (fastcgi) → git-cgi:9000 (fcgiwrap + git-http-backend)
#       ↓
#   /data/repositories/ (bare git repos)
#
# 注意：Alpine Linux 的 git 包不包含 git-http-backend，
#       因此使用 Debian slim 作为基础镜像
#
# 使用方式:
#   docker compose up -d
# =============================================================================

FROM debian:bookworm-slim

# 针对国内网络环境优化: 使用阿里云 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || \
    echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free" > /etc/apt/sources.list

# 安装依赖
# git: 包含 git-http-backend (在 Debian 中默认包含)
# fcgiwrap: FastCGI 包装器
# spawn-fcgi: 用于启动 fcgiwrap
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    fcgiwrap \
    spawn-fcgi \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# 验证 git-http-backend 存在（在构建阶段就检查）
RUN if [ ! -f /usr/lib/git-core/git-http-backend ]; then \
    echo "ERROR: git-http-backend not found after installation"; \
    echo "Searching in common locations..."; \
    find /usr -name "git-http-backend" 2>/dev/null || true; \
    exit 1; \
    fi && \
    echo "SUCCESS: git-http-backend found at /usr/lib/git-core/git-http-backend" && \
    ls -la /usr/lib/git-core/git-http-backend

# Git HTTP 后端可执行文件路径 (Debian 路径与 Alpine 不同)
ENV GIT_BACKEND_CMD=/usr/lib/git-core/git-http-backend

# fcgiwrap 监听端口（与 Nginx fastcgi_pass 对应）
ENV FCGI_PORT=9000

# 允许导出所有仓库（不限 public/private，认证由应用层处理）
ENV GIT_HTTP_EXPORT_ALL=1

# 仓库根目录（与 app 容器共享 volume）
ENV GIT_PROJECT_ROOT=/data/repositories

# 预配置 safe.directory（Git 2.35.2+ 安全特性）
# app 容器（user 1000:perseus）创建仓库，git-cgi 以 root 运行，
# 不设置此选项会导致 "dubious ownership" 错误
RUN git config --system safe.directory "*"

# 创建仓库目录
RUN mkdir -p /data/repositories && chmod 755 /data/repositories

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
