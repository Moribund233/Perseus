# =============================================================================
# Perseus Docker 多阶段构建
#
# 构建说明:
#   docker build -t perseus:latest .
#
# 开发模式:
#   docker compose up
#
# 生产模式:
#   docker compose -f docker-compose.yml up -d
# =============================================================================

# ---- 构建阶段 ----
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装 Poetry
RUN pip install --no-cache-dir poetry

# 复制依赖定义
COPY pyproject.toml /build/

# 安装生产依赖到系统
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main --no-interaction --no-ansi

# ---- 运行阶段 ----
FROM python:3.12-slim AS runtime

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    fcgiwrap \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . /app/

# 创建必要目录
RUN mkdir -p /data/repositories /app/logs

# 暴露端口
EXPOSE 8000

# 默认使用 Uvicorn 运行（适合 Docker/K8s）
CMD ["uvicorn", "app:get_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
