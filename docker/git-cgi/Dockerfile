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
# 使用方式:
#   docker compose up -d
# =============================================================================

FROM alpine:3.19

RUN apk add --no-cache \
    git \
    fcgiwrap \
    spawn-fcgi \
    && rm -rf /var/cache/apk/*

# Git HTTP 后端可执行文件路径
ENV GIT_BACKEND_CMD=/usr/libexec/git-core/git-http-backend

# fcgiwrap 监听端口（与 Nginx fastcgi_pass 对应）
ENV FCGI_PORT=9000

# 允许导出所有仓库（不限 public/private，认证由应用层处理）
ENV GIT_HTTP_EXPORT_ALL=1

# 仓库根目录（与 app 容器共享 volume）
ENV GIT_PROJECT_ROOT=/data/repositories

# 创建仓库目录
RUN mkdir -p /data/repositories

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
