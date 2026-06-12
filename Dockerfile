# =============================================================================
# Perseus Docker 多阶段构建 (生产环境)
#
# 构建说明:
#   docker build -t perseus:latest .
#
# 特性:
#   - 多阶段构建，减小镜像体积
#   - 使用 UV 替代 Poetry，更快的依赖安装
#   - 针对国内网络环境优化 (阿里云镜像源)
#   - 基于 pyproject.toml 安装依赖（更好的版本管理）
#
# 开发模式:
#   docker compose -f docker-compose.dev.yml up
#
# 生产模式:
#   docker compose -f docker-compose.yml up -d
#
# 注意:
#   - 前端目录 client/ 已被 .dockerignore 排除
#   - 需要 pyproject.toml 和 README.md 来安装依赖
# =============================================================================

# ---- 构建阶段 ----
FROM python:3.12-slim AS builder

WORKDIR /build

# 针对国内网络环境优化: 配置阿里云 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || \
    echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libgit2-dev \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 配置阿里云 PyPI 镜像
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_TRUSTED_HOST=mirrors.aliyun.com
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 安装 UV
RUN pip install --no-cache-dir uv -i https://mirrors.aliyun.com/pypi/simple/

# 复制依赖定义文件
COPY pyproject.toml README.md ./

# 基于 pyproject.toml 安装生产依赖
# --system: 安装到系统 Python
RUN uv pip install --system -e .

# ---- 运行阶段 ----
FROM python:3.12-slim AS runtime

# 针对国内网络环境优化: 配置阿里云 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || \
    echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list

# 安装运行时系统依赖
# git: 用于程序化 Git 操作（创建 bare repo、分支管理等）
# libpq5: PostgreSQL 客户端库（psycopg2 运行时需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . /app/

# 创建非 root 用户
RUN groupadd -g 1000 perseus && useradd -u 1000 -g perseus perseus \
    && mkdir -p /data/repositories /app/logs \
    && chown -R perseus:perseus /app /data/repositories /app/logs

# 切换到非 root 用户
USER perseus

# 暴露端口
EXPOSE 8000

# 默认使用 Uvicorn 运行（适合 Docker/K8s）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
