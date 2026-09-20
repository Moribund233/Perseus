#!/usr/bin/env bash
# =============================================================================
# Perseus 脚本公共库（仅被 source 引入，不应直接执行）
#
# 提供: 路径/颜色/日志、.env 安全读写、compose 封装、健康等待、
#       镜像构建模式、必备组件检查。
# 注意: 出于密码可能含 shell 特殊字符（$ & ^ 等）的考虑，
#       一律不 source .env，改用行级解析读取，避免污染/执行注入。
# =============================================================================

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT_DIR="$(cd "$LIB_DIR/.." && pwd -P)"
PROJECT_ROOT="$(cd "$LIB_DIR/../.." && pwd -P)"
ENV_FILE="$PROJECT_ROOT/.env"

# ---------- 颜色与日志 ----------
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  C_GREEN=$'\e[32m'
  C_YELLOW=$'\e[33m'
  C_RED=$'\e[31m'
  C_BLUE=$'\e[34m'
  C_BOLD=$'\e[1m'
  C_RESET=$'\e[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_BLUE=''; C_BOLD=''; C_RESET=''
fi

log_info()  { printf '%s[INFO]%s %s\n' "${C_BLUE}" "${C_RESET}" "$*"; }
log_ok()    { printf '%s[ OK ]%s %s\n' "${C_GREEN}" "${C_RESET}" "$*"; }
log_warn()  { printf '%s[WARN]%s %s\n' "${C_YELLOW}" "${C_RESET}" "$*" >&2; }
log_error() { printf '%s[ERR ]%s %s\n' "${C_RED}" "${C_RESET}" "$*" >&2; }

die() {
  log_error "$*"
  exit 1
}

# ---------- .env 安全读写 ----------
env_get() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    printf ''
    return 0
  fi
  awk -v k="$key" 'index($0, k "=") == 1 { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit }' "$ENV_FILE"
}

set_env_key() {
  local key="$1" value="$2" file="$ENV_FILE"
  if [[ ! -f "$file" ]]; then
    die ".env 不存在, 请先运行 scripts/generate_env.py"
  fi
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
  log_info "已更新 .env: ${key}=${value}"
}

# 校验 .env 必需的密钥类变量
require_env() {
  local missing=()
  for key in PERSEUS_SECURITY_SECRET_KEY POSTGRES_PASSWORD \
             PERSEUS_ADMIN_PASSWORD PERSEUS_COLLAB_INTERNAL_SECRET; do
    if [[ -z "$(env_get "$key")" ]]; then
      missing+=("$key")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "以下必需变量缺失: ${missing[*]}"
    die "请运行: python3 scripts/generate_env.py --prod"
  fi
}

# 补充升级后新增的「可选」配置字段（仅当键不存在时追加，保留用户已有的值）
# 用法: ensure_env_keys KEY1=default1 KEY2=default2 ...（来自 generate_env.py 的可选默认值）
ensure_env_keys() {
  local key value entry
  for entry in "$@"; do
    key="${entry%%=*}"
    value="${entry#*=}"
    if [[ ! -f "$ENV_FILE" ]]; then
      die ".env 不存在, 请先运行 scripts/generate_env.py"
    fi
    if ! grep -qE "^${key}=" "$ENV_FILE"; then
      set_env_key "$key" "$value"
    fi
  done
}

# ---------- compose 封装 ----------
# 生产编排默认使用仓库根目录 docker-compose.yml（其 include 基础设施层）
compose() { docker compose "$@"; }

# ---------- 必备组件检查 ----------
require_docker() {
  command -v docker >/dev/null 2>&1 || die "未找到 docker, 请先安装 Docker Engine 20.10+"
  if ! docker info >/dev/null 2>&1; then
    die "docker 守护进程不可用, 请确认服务已启动且当前用户有权限(常见: usermod -aG docker \$USER)"
  fi
}

require_compose_v2() {
  local ver
  ver="$(docker compose version 2>/dev/null || true)"
  if [[ -z "$ver" ]]; then
    die "未检测到 Docker Compose (docker compose 插件)"
  fi
  # 支持 v2.x 和 v5.x 等版本
  if ! [[ "$ver" =~ v[0-9]+\.[0-9]+ ]]; then
    die "需要 Docker Compose V2+ (docker compose 插件), 当前: ${ver}"
  fi
}

require_python() {
  command -v python3 >/dev/null 2>&1 || die "未找到 python3 (用于生成 .env 密钥), 请安装 Python 3.10+"
}

# ---------- 镜像构建模式 ----------
# PERSEUS_IMAGE_PREFIX 非空 => 使用私有仓库镜像（docker compose pull）
# 为空 (默认)           => 本地源码构建（docker compose build）
image_prefix() { env_get PERSEUS_IMAGE_PREFIX; }

images_are_remote() { [[ -n "$(image_prefix)" ]]; }

build_images() {
  if images_are_remote; then
    log_info "使用私有仓库镜像 ($(image_prefix)/*:$(env_get PERSEUS_IMAGE_TAG)), 执行 pull..."
    compose pull app collab git-cgi sshd init
  else
    log_info "本地源码构建业务镜像 (perseus-*:$(env_get PERSEUS_IMAGE_TAG))..."
    compose build app collab git-cgi sshd init
  fi
}

# ---------- 健康等待 ----------
container_health() { docker inspect -f '{{.State.Health.Status}}' "$1" 2>/dev/null || printf 'missing'; }

# wait_healthy <container_name> [timeout_seconds]
wait_healthy() {
  local name="$1"
  local timeout="${2:-120}"
  local waited=0
  log_info "等待容器健康: ${name} (上限 ${timeout}s)"
  while (( waited < timeout )); do
    local status
    status="$(container_health "$name")"
    case "$status" in
      healthy)   log_ok "容器健康: ${name}"; return 0 ;;
      unhealthy) die "容器进入 unhealthy 状态: ${name} (docker compose logs $1)" ;;
    esac
    sleep 3
    waited=$((waited + 3))
  done
  die "等待容器健康超时: ${name} (${timeout}s)"
}

# wait_running <container_name> [timeout_seconds]
# 适用于无 healthcheck 的容器（如 git-cgi）
wait_running() {
  local name="$1"
  local timeout="${2:-60}"
  local waited=0
  log_info "等待容器运行: ${name}"
  while (( waited < timeout )); do
    local state
    state="$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)"
    if [[ "$state" == "true" ]]; then
      log_ok "容器运行: ${name}"
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done
  die "等待容器运行超时: ${name} (${timeout}s)"
}

# ---------- 提示输入 ----------
confirm() {
  local prompt="$1"
  local answer
  read -r -p "${C_YELLOW}${prompt} [y/N]${C_RESET} " answer
  [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

# prompt_value <提示> <默认值> -> stdout 输出（直接回车取默认值）
prompt_value() {
  local prompt="$1" default="$2" answer=""
  read -r -p "${C_YELLOW}${prompt}${C_RESET} [${default}]: " answer || answer=""
  printf '%s' "${answer:-$default}"
}

# prompt_yes_no <提示> <默认 y|n> -> 0=是 1=否
prompt_yes_no() {
  local prompt="$1" default="${2:-n}" answer="" hint="[y/N]"
  [[ "$default" == "y" ]] && hint="[Y/n]"
  read -r -p "${C_YELLOW}${prompt}${C_RESET} ${hint}: " answer || answer=""
  answer="${answer:-$default}"
  [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

# interactive_prompt_or_default <秒数>
#   0 = 使用默认部署（超时 / 非交互环境）
#   1 = 进入自定义交互
interactive_prompt_or_default() {
  local timeout="${1:-5}"
  if [[ ! -t 0 ]]; then
    return 0
  fi
  local answer=""
  printf '%s按 Enter 进入自定义配置，%s 秒后自动使用默认部署...%s ' \
    "${C_YELLOW}" "$timeout" "${C_RESET}"
  if read -r -t "$timeout" answer; then
    printf '\n'
    return 1
  fi
  printf '\n'
  log_info "未检测到输入，使用默认部署"
  return 0
}

# ---------- 全局 CLI 安装 ----------
# 将 scripts/perseus.sh 软链为 PATH 中的 `perseus` 命令。
# 优先 /usr/local/bin（必要时 sudo），否则回退 ~/.local/bin。
install_global_cli() {
  local src="$PROJECT_ROOT/scripts/perseus.sh"
  [[ -f "$src" ]] || { log_warn "未找到 $src, 跳过全局命令安装"; return 1; }
  chmod +x "$src" 2>/dev/null || true

  local target="/usr/local/bin/perseus"
  local bin_dir
  bin_dir="$(dirname "$target")"

  if [[ -w "$bin_dir" ]]; then
    ln -sf "$src" "$target"
  elif command -v sudo >/dev/null 2>&1 && { sudo -n true 2>/dev/null || [[ -t 0 ]]; }; then
    sudo ln -sf "$src" "$target" || return 1
  else
    target="$HOME/.local/bin/perseus"
    mkdir -p "$(dirname "$target")"
    ln -sf "$src" "$target"
    log_warn "无 ${bin_dir} 写权限, 已安装到 ${target} (请确保 ~/.local/bin 在 PATH)"
  fi
  log_ok "全局命令已安装: perseus -> ${src}"
}