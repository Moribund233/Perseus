# =============================================================================
# Perseus 协作编辑 Yjs 网关容器 (Hocuspocus 哑管道)
#
# 功能: CRDT 实时同步 + app 回调 (鉴权/文档加载/Git 保存)
# 架构:
#   Nginx (ws) → collab:4444 (Hocuspocus)
#       ↓ 回调 (内部共享密钥)
#   app:8000  (FastAPI /api/v1/collab/*)
#
# 注意: 业务逻辑 (鉴权/Git 提交) 全部在 app, 本容器零业务代码
# =============================================================================

FROM node:22-alpine

# 针对国内网络环境优化: npmmirror
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

WORKDIR /app/gateway

# 先装依赖 (利用层缓存)
COPY collab-gateway/package.json collab-gateway/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# 复制网关源码
COPY collab-gateway/server.mjs ./

# 非 root 运行
USER node

EXPOSE 4444 4445

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:4445/ || exit 1

CMD ["node", "server.mjs"]
