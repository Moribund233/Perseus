#!/usr/bin/env bash
# =============================================================================
# Perseus 一键安装 / 升级脚本（Linux, Docker Compose V2）
#
# 用法:
#   bash scripts/install.sh                 # 交互式（5s 内按 Enter 进入自定义配置）
#   bash scripts/install.sh -d              # 默认部署（非交互，使用 .env 默认值）
#   bash scripts/install.sh --upgrade       # 升级已有安装（自动备份 → 迁移 → 重启）
#   bash scripts/install.sh --tag v0.2.0    # 安装/升级到指定镜像 tag（默认 latest）
#   bash scripts/install.sh --no-build      # 跳过构建/pull, 使用已存在镜像
#   bash scripts/install.sh --with-monitoring   # 部署后启用监控栈
#   bash scripts/install.sh --no-cli        # 不安装全局 perseus 命令
#
# 交互式配置项（直接回车取方括号默认值）:
#   网关对外端口 / 管理员用户名 / 管理员邮箱 / 镜像 tag
#   Admin 控制台来源白名单（IP/CIDR, 逗号分隔; 留空=网关拒绝）
#   是否启用监控栈 / 是否安装全局 perseus 命令
#
# 流程（内部状态机, 失败即中断）:
#   preflight → 交互判定 → .env 引导 → 镜像准备 → PostgreSQL/Redis 就绪
#   → 一次性 init（Alembic 迁移 + 管理员引导）→ 业务层启动 → 网关健康
#   →（可选）监控栈 →（可选）全局命令 → 凭据展示
#
# 部署完成后统一使用 `perseus` 命令运维:
#   perseus update | doctor | uninstall | status | logs | backup ...
#
# 升级等价命令:  perseus update   （或 bash scripts/mgt.sh upgrade）
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
cd "$PROJECT_ROOT"

UPGRADE=false
TAG=""
NO_BUILD=false
DEFAULT_MODE=false
ENABLE_MONITORING=false
MONITORING_FLAG_SET=false
INSTALL_CLI=true
NO_CLI=false
INTERACTIVE=false

usage() {
  cat <<'EOF'
用法: bash scripts/install.sh [选项]

选项:
  -d, --default       默认部署（非交互，使用 .env 默认值）
  --upgrade           升级已有安装（自动先备份）
  --tag <tag>         使用指定镜像 tag（写入 .env 的 PERSEUS_IMAGE_TAG）
  --no-build          跳过镜像构建/拉取（复用本机已有镜像）
  --with-monitoring   部署后启用监控栈 (Prometheus/Grafana)
  --no-cli            不安装全局 perseus 命令
  -h, --help          显示帮助

说明:
  不带参数时为交互式: 启动后 5 秒内按 Enter 可进入自定义配置，
  否则自动使用默认部署（等价 -d）。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--default) DEFAULT_MODE=true ;;
    --upgrade) UPGRADE=true ;;
    --tag) TAG="${2:?--tag 需要参数}"; shift ;;
    --no-build) NO_BUILD=true ;;
    --with-monitoring) ENABLE_MONITORING=true; MONITORING_FLAG_SET=true ;;
    --no-cli) NO_CLI=true; INSTALL_CLI=false ;;
    -h|--help) usage; exit 0 ;;
    *) die "未知参数: $1 (bash scripts/install.sh --help)" ;;
  esac
  shift
done

print_credentials() {
  local user pw port
  user="$(env_get PERSEUS_ADMIN_USERNAME)"; [[ -z "$user" ]] && user="admin"
  pw="$(env_get PERSEUS_ADMIN_PASSWORD)"
  port="$(env_get PERSEUS_GATEWAY_PORT)"; [[ -z "$port" ]] && port="8000"
  local local_ip
  local_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -z "$local_ip" ]] && local_ip="127.0.0.1"

  echo ""
  echo "================================================================"
  log_ok "Perseus 部署完成"
  echo "  访问地址:      http://${local_ip}:${port}/docs"
  echo "  本机访问:      http://127.0.0.1:${port}"
  echo ""
  echo "  管理员账号:    ${user}"
  [[ -n "$pw" ]] && echo "  管理员密码:    ${C_BOLD}${pw}${C_RESET}"
  echo ""
  if [[ "$ENABLE_MONITORING" == true ]]; then
    echo "  Grafana (监控): ${C_BOLD}http://${local_ip}:${port}/grafana${C_RESET}"
    echo "                 admin 控制台「打开 Grafana」自动登录; 凭据 .env GRAFANA_ADMIN_PASSWORD"
  fi
  log_warn "管理员密码请妥善保存；若遗忘执行: perseus reset-admin"
  echo "  运维命令:      perseus help   (bash scripts/mgt.sh help)"
  echo "================================================================"
  echo ""
}

interactive_config() {
  echo ""
  log_info "自定义部署配置（直接回车使用方括号默认值）"

  local cur_port cur_user cur_email cur_tag
  cur_port="$(env_get PERSEUS_GATEWAY_PORT)"; cur_port="${cur_port:-8000}"
  cur_user="$(env_get PERSEUS_ADMIN_USERNAME)"; cur_user="${cur_user:-admin}"
  cur_email="$(env_get PERSEUS_ADMIN_EMAIL)"; cur_email="${cur_email:-admin@perseus.local}"
  cur_tag="$(env_get PERSEUS_IMAGE_TAG)"; cur_tag="${cur_tag:-latest}"

  local port user email tag
  port="$(prompt_value "网关对外端口" "$cur_port")"
  user="$(prompt_value "管理员用户名" "$cur_user")"
  email="$(prompt_value "管理员邮箱" "$cur_email")"
  tag="$(prompt_value "镜像 tag" "$cur_tag")"
  local sources cur_sources
  cur_sources="$(env_get PERSEUS_ADMIN_ALLOWED_SOURCES)"
  sources="$(prompt_value "Admin 控制台允许来源 (IP/CIDR, 逗号分隔; 留空=网关拒绝)" "$cur_sources")"

  [[ "$port" =~ ^[0-9]+$ ]] || die "网关端口必须为数字: $port"
  [[ -n "$user" ]] || die "管理员用户名不能为空"
  [[ -n "$email" ]] || die "管理员邮箱不能为空"

  set_env_key "PERSEUS_GATEWAY_PORT" "$port"
  set_env_key "PERSEUS_ADMIN_USERNAME" "$user"
  set_env_key "PERSEUS_ADMIN_EMAIL" "$email"
  set_env_key "PERSEUS_IMAGE_TAG" "$tag"
  set_env_key "PERSEUS_ADMIN_ALLOWED_SOURCES" "$sources"

  if prompt_yes_no "部署后启用监控栈 (Prometheus/Grafana)?" "n"; then
    ENABLE_MONITORING=true
  fi
  if [[ "$NO_CLI" != true ]]; then
    if ! prompt_yes_no "安装全局 perseus 命令 (update/doctor/uninstall)?" "y"; then
      INSTALL_CLI=false
    fi
  fi
}

main() {
  echo ""
  log_info "Perseus 部署脚本"
  echo ""

  require_docker
  require_compose_v2
  require_python

  # ---------- 0. 交互判定（默认部署 vs 自定义） ----------
  if [[ "$DEFAULT_MODE" != true && "$UPGRADE" != true ]]; then
    if interactive_prompt_or_default 5; then
      INTERACTIVE=false
    else
      INTERACTIVE=true
    fi
  fi

  # ---------- 1. .env 引导（必须在任何 compose 调用之前，否则首次安装会因
  #       compose 必需变量(:? 校验)未定义而报错退出） ----------
  if [[ ! -f "$ENV_FILE" ]]; then
    log_info "首次安装: 生成 .env 与随机密钥..."
    python3 "$SCRIPT_DIR/generate_env.py" --prod --show || die ".env 生成失败"
  else
    log_info ".env 已存在, 校验必需变量..."
    require_env
  fi

  # 补充升级后新增的可选配置字段（旧版 .env 可能缺失; 缺失才追加, 默认空=管理员控制台拒绝）
  ensure_env_keys PERSEUS_ADMIN_ALLOWED_SOURCES=
  ensure_env_keys PERSEUS_GATEWAY_HOST=127.0.0.1
  # 监控栈偏好持久化到 .env（历史部署缺失时默认关闭; 升级/再次部署沿用上次选择）
  ensure_env_keys MONITORING_ENABLED=false

  if [[ -n "$TAG" ]]; then
    set_env_key "PERSEUS_IMAGE_TAG" "$TAG"
  fi

  # 未显式传 --with-monitoring 时, 沿用 .env 中持久化的监控栈选择
  if [[ "$MONITORING_FLAG_SET" != true ]]; then
    if [[ "$(env_get MONITORING_ENABLED)" == true ]]; then
      ENABLE_MONITORING=true
    else
      ENABLE_MONITORING=false
    fi
  fi

  # ---------- 2. 自定义配置 ----------
  if [[ "$INTERACTIVE" == true ]]; then
    interactive_config
  fi

  # 持久化本次生效的监控栈选择, 供后续 --upgrade / 再次部署沿用
  if [[ "$ENABLE_MONITORING" == true ]]; then
    set_env_key "MONITORING_ENABLED" "true"
  else
    set_env_key "MONITORING_ENABLED" "false"
  fi

  # ---------- 3. 部署状态判定 ----------
  local existing
  existing="$(compose ps -q 2>/dev/null | tr -d '\n' | wc -c || true)"
  if [[ "${existing:-0}" != "0" && "$UPGRADE" != true ]]; then
    die "检测到已有服务正在运行, 升级请使用: bash scripts/install.sh --upgrade（或 perseus update）"
  fi

  if [[ "$UPGRADE" == true ]]; then
    log_info "升级模式: 先执行数据库备份..."
    bash "$SCRIPT_DIR/mgt.sh" backup || die "升级前备份失败, 已中止"
  fi

  local prefix
  prefix="$(image_prefix)"
  if [[ -n "$prefix" ]]; then
    log_info "镜像版本: ${prefix}-*:$(env_get PERSEUS_IMAGE_TAG) (私有仓库模式)"
  else
    log_info "镜像版本: perseus-*:$(env_get PERSEUS_IMAGE_TAG) (本地构建)"
  fi

  # ---------- 4. 镜像准备 ----------
  if [[ "$NO_BUILD" != true ]]; then
    build_images
  else
    log_warn "--no-build 已指定, 跳过镜像构建/拉取"
  fi

  # ---------- 5. 基础设施层（PostgreSQL / Redis） ----------
  log_info "启动基础设施层 (postgres, redis)..."
  compose up -d postgres redis
  wait_healthy perseus-postgres 180
  wait_healthy perseus-redis 120

  # ---------- 6. 一次性初始化（迁移 + 管理员引导） ----------
  log_info "执行数据库初始化 (Alembic 迁移 + 管理员引导)..."
  compose --profile init run --rm init || die "数据库初始化失败, 请查看上方日志"

  # ---------- 7. 业务层启动 ----------
  log_info "启动业务层 (app, collab, git-cgi, gateway, sshd)..."
  compose up -d
  wait_healthy perseus-gateway 240

  # ---------- 8. 可选监控栈 ----------
  if [[ "$ENABLE_MONITORING" == true ]]; then
    log_info "启动监控栈 (Prometheus/Grafana)..."
    compose -f docker-compose.monitoring.yml up -d \
      || log_warn "监控栈启动失败, 可稍后手动: docker compose -f docker-compose.monitoring.yml up -d"
  fi

  # ---------- 9. 可选全局命令 ----------
  if [[ "$INSTALL_CLI" == true ]]; then
    install_global_cli \
      || log_warn "全局命令安装失败, 可手动: sudo ln -sf $PROJECT_ROOT/scripts/perseus.sh /usr/local/bin/perseus"
  fi

  log_ok "全部服务已就绪"
  print_credentials
}

main "$@"
