#!/usr/bin/env bash
# =============================================================================
# Perseus 运维命令（Linux, Docker Compose V2）
#
# 用法: bash scripts/mgt.sh <command> [参数]
#
# 命令:
#   start                    启动全部服务（若 schema 未就绪会提醒先 init）
#   stop                     停止全部服务（保留数据卷）
#   restart [svc...]         重启（默认全部）
#   status                   查看容器状态与健康
#   logs [svc...]            跟踪日志（默认全部）
#   init [--check-only]      执行数据库初始化 / 只读就绪校验
#   backup [--with-data] [dir]   备份数据库+配置（--with-data 含 Git 仓库数据）
#   restore <backup文件> [--with-data]   恢复备份（破坏性, 需确认）
#   upgrade [--tag X] [--no-build]       升级（自动备份 → 构建 → 迁移 → 重启）
#   rollback [backup文件]    回滚到最近一次备份（相当于 restore + 重启）
#   reset-admin [新密码]     重设管理员密码（缺省用 .env 的 PERSEUS_ADMIN_PASSWORD）
#   doctor                   环境体检（依赖/配置/schema/健康/磁盘）
#   uninstall                彻底卸载（删除数据卷, 需二次确认）
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
cd "$PROJECT_ROOT"

BACKUP_ROOT="backups"

# ---------- 基础命令 ----------
cmd_start() {
  require_docker; require_compose_v2; require_env
  compose up -d postgres redis
  wait_healthy perseus-postgres 180
  wait_healthy perseus-redis 120
  # 若 schema 未就绪, 先跑一次 init（幂等）, 避免 app 反复就绪失败
  compose run --rm --no-deps init python scripts/init_db.py --check-only >/dev/null 2>&1 \
    || { log_warn "schema 未就绪, 自动执行初始化任务..."; compose --profile init run --rm init; }
  compose up -d
  wait_healthy perseus-gateway 240
  log_ok "服务已启动"
}

cmd_stop() {
  require_docker
  compose stop
  log_ok "服务已停止（数据卷保留）"
}

cmd_restart() {
  require_docker
  if [[ $# -eq 0 ]]; then
    compose restart
  else
    compose restart "$@"
  fi
}

cmd_status() {
  require_docker
  compose ps
  echo ""
  log_info "常规校验: bash scripts/mgt.sh doctor"
}

cmd_logs() {
  require_docker
  if [[ $# -eq 0 ]]; then
    compose logs -f
  else
    compose logs -f "$@"
  fi
}

cmd_init() {
  require_docker; require_compose_v2; require_env
  if [[ "${1:-}" == "--check-only" ]]; then
    log_info "只读校验 schema 就绪状态..."
    compose run --rm --no-deps init python scripts/init_db.py --check-only
  else
    log_info "执行数据库迁移与管理员引导（幂等）..."
    compose --profile init run --rm init
    log_ok "初始化完成"
  fi
}

# ---------- 备份 / 恢复 ----------
cmd_backup() {
  local with_data=false
  local args=()
  for a in "$@"; do
    case "$a" in
      --with-data) with_data=true ;;
      *) args+=("$a") ;;
    esac
  done
  local dir="${args[0]:-$BACKUP_ROOT}"
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"
  local stage="$dir/.stage-$ts"
  local archive="$dir/perseus-backup-$ts.tar.gz"

  require_docker; require_compose_v2
  mkdir -p "$dir" "$stage"

  log_info "确保基础设施运行以执行备份..."
  compose up -d postgres
  wait_healthy perseus-postgres 180

  log_info "备份 PostgreSQL 数据..."
  compose exec -T postgres pg_dump -U perseus --clean --if-exists perseus > "$stage/database.sql" \
    || die "数据库备份失败"

  log_info "备份配置与版本信息..."
  cp "$ENV_FILE" "$stage/env" 2>/dev/null || log_warn ".env 不存在, 跳过"
  if [[ -f config.toml ]]; then cp config.toml "$stage/config.toml"; fi
  {
    printf '%s\n' "$ts"
    git rev-parse --short HEAD 2>/dev/null || printf 'unknown\n'
  } > "$stage/version.txt"

  if [[ "$with_data" == true ]]; then
    log_info "备份 Git 仓库数据卷 (repos)..."
    compose up -d git-cgi
    wait_running perseus-git-cgi 90 2>/dev/null || true
    compose exec -T git-cgi sh -c 'cd /data/repositories && tar czf - .' > "$stage/repos.tar.gz" \
      || log_warn "repos 数据卷备份失败, 继续（归档中不含仓库数据）"
  fi

  tar czf "$archive" -C "$stage" .
  rm -rf "$stage"
  log_ok "备份完成: $archive"

  # 保留最近 7 份备份
  local old
  old="$(ls -1t "$dir"/perseus-backup-*.tar.gz 2>/dev/null | tail -n +8 || true)"
  if [[ -n "$old" ]]; then
    log_info "清理过期备份(<8)..."
    echo "$old" | xargs -r rm -f
  fi
}

cmd_restore() {
  local with_data=false
  local restore_env=false
  local args=()
  for a in "$@"; do
    case "$a" in
      --with-data) with_data=true ;;
      --restore-env) restore_env=true ;;
      *) args+=("$a") ;;
    esac
  done
  local archive="${args[0]:-}"
  if [[ -z "$archive" ]]; then
    archive="$(ls -1t "$BACKUP_ROOT"/perseus-backup-*.tar.gz 2>/dev/null | head -n1 || true)"
    [[ -z "$archive" ]] && die "未找到备份文件, 请指定: bash scripts/mgt.sh restore <文件>"
    log_info "使用最近备份: $archive"
  fi
  [[ -f "$archive" ]] || die "备份文件不存在: $archive"

  local stage
  stage="$(mktemp -d)"
  trap 'rm -rf "$stage"' EXIT
  tar xzf "$archive" -C "$stage"

  log_warn "恢复将覆盖当前数据库/配置, 该操作不可撤销！"
  confirm "确认恢复备份 $(basename "$archive") ?" || die "已取消"
  [[ -f "$stage/database.sql" ]] || die "归档中缺少 database.sql, 无法恢复"

  require_docker; require_compose_v2

  log_info "停止业务服务, 避免写入冲突..."
  compose stop app collab git-cgi gateway sshd 2>/dev/null || true

  log_info "确保 PostgreSQL 运行..."
  compose up -d postgres
  wait_healthy perseus-postgres 180

  log_info "恢复数据库..."
  compose exec -T postgres psql -v ON_ERROR_STOP=1 -U perseus -d perseus < "$stage/database.sql" \
    || die "数据库恢复失败"

  log_info "恢复应用配置 config.toml..."
  if [[ -f "$stage/config.toml" ]]; then
    cp "$stage/config.toml" ./config.toml
    log_ok "config.toml 已恢复"
  fi

  if [[ "$restore_env" == true ]]; then
    log_warn "--restore-env: 将恢复 .env（含密钥与数据库密码）。"
    log_warn "若备份中的 POSTGRES_PASSWORD 与当前 PG 实例实际密码不一致, 应用将无法连接。"
    if confirm "仍然恢复 .env ?"; then
      if [[ -f "$stage/env" ]]; then
        cp "$stage/env" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log_ok ".env 已恢复"
      else
        log_warn "归档中不包含 env, 跳过"
      fi
    else
      log_warn "跳过 .env 恢复"
    fi
  else
    log_info "保留当前 .env 中的密钥/凭据（认证信息未被覆盖）"
  fi

  if [[ "$with_data" == true && -f "$stage/repos.tar.gz" ]]; then
    log_info "恢复 Git 仓库数据卷 (repos)..."
    compose up -d git-cgi
    wait_running perseus-git-cgi 90 2>/dev/null || true
    compose exec -T git-cgi sh -c 'cd /data/repositories && tar xzf -' < "$stage/repos.tar.gz" \
      || log_warn "repos 数据卷恢复失败"
  elif [[ "$with_data" != true ]]; then
    log_info "未指定 --with-data, 跳过 Git 仓库数据卷（如需要请加该参数重新恢复）"
  fi

  log_info "重新启动服务..."
  compose up -d
  wait_healthy perseus-gateway 240
  log_ok "恢复完成"
}

# ---------- 升级 / 回滚 ----------
cmd_upgrade() {
  local tag=""
  local no_build=false
  local with_data=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-build) no_build=true ;;
      --with-data) with_data=true ;;
      --tag) tag="${2:?--tag 需要参数}"; shift ;;
      -h|--help) usage; return 0 ;;
      *) die "未知参数: $1" ;;
    esac
    shift
  done

  require_docker; require_compose_v2; require_env

  log_warn "升级流程: 自动备份 → 构建/拉取 → 迁移 → 重启。"
  confirm "开始升级 Perseus ?" || die "已取消"

  log_info "步骤 1/4: 备份当前状态..."
  if [[ "$with_data" == true ]]; then
    cmd_backup --with-data
  else
    cmd_backup
  fi

  if [[ -n "$tag" ]]; then
    log_info "步骤 2/4: 镜像版本 → $tag"
    set_env_key "PERSEUS_IMAGE_TAG" "$tag"
  else
    log_info "步骤 2/4: 准备镜像 (tag=$(env_get PERSEUS_IMAGE_TAG))..."
  fi
  [[ "$no_build" != true ]] && build_images

  log_info "步骤 3/4: 数据库增量迁移..."
  compose --profile init run --rm init || die "数据库迁移失败, 回滚命令: bash scripts/mgt.sh rollback"
  wait_healthy perseus-postgres 180

  log_info "步骤 4/4: 重启业务层..."
  compose up -d
  wait_healthy perseus-gateway 240
  log_ok "升级完成 (镜像 tag=$(env_get PERSEUS_IMAGE_TAG))"
  log_warn "如需回滚: bash scripts/mgt.sh rollback"
}

cmd_rollback() {
  local archive="${1:-}"
  log_warn "回滚 = 恢复最近备份 + 重启服务"
  local args=()
  [[ -n "$archive" ]] && args+=("$archive")
  cmd_restore "${args[@]}"
}

# ---------- 管理员重设 ----------
cmd_reset_admin() {
  local pw="${1:-}"
  require_docker; require_compose_v2; require_env
  if [[ -z "$pw" ]]; then
    pw="$(env_get PERSEUS_ADMIN_PASSWORD)"
    [[ -z "$pw" ]] && die "未指定密码且 .env 中无 PERSEUS_ADMIN_PASSWORD"
    log_warn "未显式提供密码, 将使用 .env 中当前的值。"
    confirm "继续 ?" || die "已取消"
  fi
  log_info "重设管理员密码..."
  compose run --rm --no-deps app python scripts/reset_admin.py "$pw" \
    || die "密码重设失败"
  log_ok "管理员密码已更新"
}

# ---------- 体检 ----------
cmd_doctor() {
  echo "== Perseus 环境体检 =="
  echo ""
  echo "[1/6] Docker 环境"
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    log_ok "docker 守护进程可用 ($(docker version --format '{{.Server.Version}}' 2>/dev/null))"
  else
    log_error "docker 不可用"
  fi
  if docker compose version >/dev/null 2>&1; then
    log_ok "Docker Compose 可用 ($(docker compose version 2>/dev/null))"
  else
    log_error "Docker Compose 不可用 (需要 docker compose 插件)"
  fi

  echo ""
  echo "[2/6] .env 配置"
  if [[ -f "$ENV_FILE" ]]; then
    log_ok ".env 存在"
    for key in PERSEUS_SECURITY_SECRET_KEY POSTGRES_PASSWORD PERSEUS_ADMIN_PASSWORD \
               PERSEUS_COLLAB_INTERNAL_SECRET; do
      if [[ -z "$(env_get "$key")" ]]; then
        log_error "缺失变量: $key"
      fi
    done
  else
    log_error ".env 不存在 (python3 scripts/generate_env.py --prod)"
  fi

  echo ""
  echo "[3/6] compose 配置校验"
  if compose config --quiet 2>/dev/null; then
    log_ok "docker-compose.yml 配置有效"
  else
    log_error "compose 配置无效 (docker compose config)"
  fi

  echo ""
  echo "[4/6] 容器状态"
  compose ps -a 2>/dev/null || true

  echo ""
  echo "[5/6] schema 就绪状态"
  if compose run --rm --no-deps init python scripts/init_db.py --check-only >/dev/null 2>&1; then
    log_ok "数据库 schema 已就绪"
  else
    log_error "数据库 schema 未就绪: bash scripts/mgt.sh init"
  fi

  echo ""
  echo "[6/6] 资源"
  df -h . | awk 'NR==1 || $6=="/" { print }'
  free -h 2>/dev/null | head -n2 || true

  echo ""
  log_info "体检结束; 修复建议见上方 [ERR] 标记"
}

# ---------- 卸载 ----------
cmd_uninstall() {
  log_warn "卸载将删除全部数据（数据库 / Git 仓库 / 日志），且不可恢复！"
  confirm "确定卸载 Perseus ?" || die "已取消"
  log_warn "请再次确认, 该操作将执行 docker compose down -v 删除数据卷。"
  local answer
  read -r -p "输入 YES 继续: " answer || answer=""
  [[ "$answer" == "YES" ]] || die "已取消"

  require_docker; require_compose_v2
  compose down -v
  log_ok "服务与数据卷已删除。"
  log_info "备份目录保留: $BACKUP_ROOT/ （如需彻底删除请手动清理）"
  log_info "镜像保留: docker rmi \$(docker images -q 'perseus-*') 可手动清理"
}

usage() {
  cat <<'EOF'
Perseus 运维命令

用法: bash scripts/mgt.sh <command> [参数]

命令:
  start                 启动全部服务（缺失 schema 时自动初始化）
  stop                  停止全部服务（保留数据卷）
  restart [svc...]      重启（默认全部）
  status                查看容器状态与健康
  logs [svc...]         跟踪日志（默认全部）
  init [--check-only]   执行数据库初始化 / 只读就绪校验
  backup [--with-data] [dir]   备份数据库+配置（--with-data 含 Git 仓库数据）
  restore <备份文件> [--with-data]  恢复备份（破坏性, 需确认）
  upgrade [--tag X] [--no-build]   升级（自动备份 → 构建 → 迁移 → 重启）
  rollback [备份文件]    回滚到最近备份（restore + 重启）
  reset-admin [新密码]   重设管理员密码（缺省用 .env 中的值）
  doctor                环境体检
  uninstall             彻底卸载（删除数据卷, 需二次确认）
EOF
}

CMD="${1:-help}"
shift || true

case "$CMD" in
  help|--help|-h) usage ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart "$@" ;;
  status|ps) cmd_status ;;
  logs) cmd_logs "$@" ;;
  init|migrate) cmd_init "$@" ;;
  backup) cmd_backup "$@" ;;
  restore) cmd_restore "$@" ;;
  upgrade) cmd_upgrade "$@" ;;
  rollback) cmd_rollback "$@" ;;
  reset-admin) cmd_reset_admin "$@" ;;
  doctor|check) cmd_doctor ;;
  uninstall) cmd_uninstall ;;
  *) die "未知命令: $CMD (bash scripts/mgt.sh help)" ;;
esac