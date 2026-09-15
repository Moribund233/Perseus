#!/usr/bin/env bash
# =============================================================================
# Perseus 统一运维命令（雷池式 CLI）
#
# 用法: perseus <command> [参数]
#
#   install                 一键安装 / 升级（透传 scripts/install.sh 参数）
#   update                  升级到最新镜像（等价 install --upgrade / mgt upgrade）
#   doctor                  环境体检（依赖/配置/schema/健康/磁盘）
#   uninstall               彻底卸载（删除数据卷，二次确认）
#
#   start | stop | restart  生命周期
#   status                  容器状态与健康
#   logs [svc...]           跟踪日志
#   init [--check-only]     数据库迁移 / 只读就绪校验
#   backup | restore        备份 / 恢复
#   rollback                回滚到最近一次备份
#   reset-admin [新密码]    重设管理员密码
#
# 本脚本通过软链安装为 /usr/local/bin/perseus（见 install.sh）。
# 直接调用: bash scripts/perseus.sh <command>
# =============================================================================
set -euo pipefail

# 解析软链，定位脚本真实所在目录（支持 /usr/local/bin/perseus 软链）
_resolve_script_dir() {
  local src="${BASH_SOURCE[0]}"
  while [[ -L "$src" ]]; do
    local dir
    dir="$(cd "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd "$(dirname "$src")" && pwd
}

SCRIPT_DIR="$(_resolve_script_dir)"

usage() {
  cat <<'EOF'
Perseus 统一运维命令

用法: perseus <command> [参数]

命令:
  install                 一键安装 / 升级（透传 install.sh 参数）
  update                  升级到最新镜像（自动备份 → 构建 → 迁移 → 重启）
  doctor                  环境体检（依赖/配置/schema/健康/磁盘）
  uninstall               彻底卸载（删除数据卷，二次确认）

  start                   启动全部服务（schema 缺失时自动初始化）
  stop                    停止全部服务（保留数据卷）
  restart [svc...]        重启（默认全部）
  status                  查看容器状态与健康
  logs [svc...]           跟踪日志（默认全部）
  init [--check-only]     数据库迁移 / 只读就绪校验
  backup [--with-data]    备份数据库+配置
  restore <文件> [--with-data]   恢复备份（破坏性，需确认）
  rollback [文件]         回滚到最近一次备份
  reset-admin [新密码]    重设管理员密码

  help                    显示本帮助

示例:
  perseus update --tag v0.2.0
  perseus doctor
  perseus backup --with-data
  perseus uninstall
EOF
}

CMD="${1:-help}"
shift || true

case "$CMD" in
  install)   exec bash "$SCRIPT_DIR/install.sh" "$@" ;;
  update|upgrade) exec bash "$SCRIPT_DIR/mgt.sh" upgrade "$@" ;;
  doctor|check)   exec bash "$SCRIPT_DIR/mgt.sh" doctor "$@" ;;
  uninstall)      exec bash "$SCRIPT_DIR/mgt.sh" uninstall "$@" ;;
  start|stop|restart|status|ps|logs|init|migrate|backup|restore|rollback|reset-admin)
    exec bash "$SCRIPT_DIR/mgt.sh" "$CMD" "$@" ;;
  help|--help|-h) usage ;;
  *)
    echo "未知命令: $CMD" >&2
    echo "" >&2
    usage >&2
    exit 1
    ;;
esac
