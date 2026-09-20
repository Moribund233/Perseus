# syntax=docker/dockerfile:1
# =============================================================================
# Perseus 网关镜像：OpenResty + 内嵌 Web 构建产物
#
# 多阶段构建，宿主机无需 Node/pnpm（一键部署/升级只依赖 Docker）:
#   1. web-builder : Node 容器内构建 client/web（pnpm install + build）
#   2. runtime     : OpenResty 运行时 + 将 dist 复制到 /var/www/perseus-web
#
# 构建上下文为 client/web（见 docker-compose.yml gateway.build.context），
# 因此 client/web/.dockerignore 生效（排除 node_modules/dist）。
# nginx.conf 仍由 compose 只读挂载，便于按环境调整；镜像本身不内嵌配置。
# =============================================================================

FROM node:22-alpine AS web-builder
WORKDIR /app
RUN npm install -g pnpm@11
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# 空 VITE_API_URL = 与页面同源（走网关），避免构建产物指向 127.0.0.1:8002 造成跨域
ENV VITE_API_URL=
RUN pnpm build

FROM openresty/openresty:1.31.1.1-0-bookworm-fat AS runtime
COPY --from=web-builder /app/dist /var/www/perseus-web
