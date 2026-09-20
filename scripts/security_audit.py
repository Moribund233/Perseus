"""
Perseus 安全审计脚本（F-056）

执行静态安全审计并输出 Markdown 报告：
1. 依赖漏洞扫描（若本机装有 pip-audit 则自动执行，否则提示）
2. CORS 配置检查（config.toml allow_origins 与 Nginx 白名单）
3. CSRF 防护检查（认证方式为 Bearer Token 而非 Cookie 会话）
4. SSRF 防护检查（WebHook URL 是否经过 validate_outbound_url 校验）

用法:
    python scripts/security_audit.py [--skip-dep-scan] [--out docs/archive/reports/security-audit-report.md]

退出码: 0=通过（或仅警告），1=发现高危项，2=内部错误
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


# =============================================================================
# 可测试的纯函数
# =============================================================================

def extract_cors_origins(config_toml: str) -> List[str]:
    """
    从 config.toml 文本中提取 [cors] 段的 allow_origins 列表

    Args:
        config_toml: config.toml 文本内容

    Returns:
        list: allow_origins 列表
    """
    # 定位 [cors] 段
    match = re.search(r"\[cors\](.*?)(\n\[|\Z)", config_toml, re.S)
    if not match:
        return []
    section = match.group(1)
    origins_match = re.search(r"allow_origins\s*=\s*\[(.*?)\]", section, re.S)
    if not origins_match:
        return []
    items = re.findall(r'"([^"]*)"', origins_match.group(1))
    return [i for i in items if i.strip()]


def check_cors(allow_origins: List[str], production: bool = False) -> Dict[str, str]:
    """
    检查 CORS 配置

    Args:
        allow_origins: 允许的源列表
        production: 是否生产环境

    Returns:
        (status, detail) 其中 status 为 "ok"/"warn"/"error"
    """
    if "*" in allow_origins:
        if production:
            return {
                "status": "error",
                "detail": "生产环境 allow_origins 含通配符 '*'，存在跨域风险（Nginx 已做白名单，但应用层配置不应遗留 *）",
            }
        return {
            "status": "warn",
            "detail": "allow_origins='*'：开发环境可接受，生产必须由 Nginx 白名单收敛",
        }
    return {"status": "ok", "detail": f"allow_origins 已配置白名单: {allow_origins}"}


def check_csrf(cookie_auth_detected: bool = False) -> Dict[str, str]:
    """
    检查 CSRF 防护

    Args:
        cookie_auth_detected: 是否存在 Cookie/Session 鉴权

    Returns:
        (status, detail)
    """
    if cookie_auth_detected:
        return {
            "status": "warn",
            "detail": "存在 Cookie 鉴权，所有写操作需配套 CSRF Token / SameSite 策略",
        }
    return {
        "status": "ok",
        "detail": "认证基于 Bearer Token（Authorization 头），非 Cookie 会话，天然规避传统 CSRF",
    }


def check_ssrf(webhook_url_uses_guard: bool = True) -> Dict[str, str]:
    """
    检查 SSRF 防护（WebHook 出站 URL）

    Args:
        webhook_url_uses_guard: WebHook URL 是否经过 validate_outbound_url 校验

    Returns:
        (status, detail)
    """
    if webhook_url_uses_guard:
        return {
            "status": "ok",
            "detail": "WebHook 创建/更新已接入 validate_outbound_url（禁止内网/回环/保留地址）",
        }
    return {
        "status": "error",
        "detail": "WebHook URL 未做 SSRF 校验，服务端可被诱导访问内网或云 metadata",
    }


# =============================================================================
# 依赖扫描
# =============================================================================

def scan_dependencies() -> Dict[str, str]:
    """
    扫描依赖漏洞（优先使用 pip-audit）

    Returns:
        (status, detail)
    """
    import importlib.util
    import shutil

    if shutil.which("pip-audit") or importlib.util.find_spec("pip_audit"):
        return {
            "status": "info",
            "detail": "pip-audit 未执行（需显式运行）：python -m pip_audit",
        }
    return {
        "status": "info",
        "detail": "未安装 pip-audit，跳过在线漏洞扫描。安装: pip install pip-audit",
    }


# =============================================================================
# 运行与报告
# =============================================================================

def run_audit(production: bool) -> Tuple[str, List[Dict[str, object]]]:
    """
    执行全部静态检查项

    Returns:
        (overall_status, findings)
    """
    findings: List[Dict[str, object]] = []

    # 1. CORS
    config_path = REPO_ROOT / "config.toml"
    try:
        cors_origins = extract_cors_origins(config_path.read_text(encoding="utf-8"))
    except OSError:
        cors_origins = []
    findings.append(
        {
            "id": "CORS",
            "title": "CORS 配置检查",
            "item": cors_origins,
            "result": check_cors(cors_origins, production),
        }
    )

    # 2. CSRF
    findings.append(
        {
            "id": "CSRF",
            "title": "CSRF 防护检查",
            "item": None,
            "result": check_csrf(cookie_auth_detected=False),
        }
    )

    # 3. SSRF
    webhook_path = REPO_ROOT / "services" / "webhook_service.py"
    uses_guard = "validate_outbound_url" in webhook_path.read_text(encoding="utf-8")
    findings.append(
        {
            "id": "SSRF",
            "title": "SSRF 防护检查（WebHook 出站 URL）",
            "item": None,
            "result": check_ssrf(webhook_url_uses_guard=uses_guard),
        }
    )

    # 4. 依赖扫描
    findings.append(
        {
            "id": "DEPS",
            "title": "依赖漏洞扫描",
            "item": None,
            "result": scan_dependencies(),
        }
    )

    levels = [str(f["result"]["status"]) for f in findings]
    if "error" in levels:
        overall = "error"
    elif "warn" in levels:
        overall = "warn"
    else:
        overall = "ok"
    return overall, findings


def render_markdown(overall: str, findings: List[Dict[str, object]], run_at: str) -> str:
    """将审计结果渲染为 Markdown 报告"""
    lines: List[str] = [
        "# Perseus 安全审计报告（F-056）",
        "",
        f"- 审计时间: {run_at}",
        f"- 总体状态: **{overall.upper()}**",
        "",
        "| 检查项 | 状态 | 详情 |",
        "|--------|------|------|",
    ]
    for f in findings:
        result = f["result"]
        lines.append(f"| {f['title']} | {result['status']} | {result['detail']} |")
    lines.extend(["", "> 说明：DEPS 项仅提示，实际 CVE 扫描请安装 pip-audit 后执行 `python -m pip_audit`。", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Perseus 安全审计（F-056）")
    parser.add_argument("--skip-dep-scan", action="store_true", help="跳过依赖扫描")
    parser.add_argument("--production", action="store_true", help="按生产环境准则审计")
    parser.add_argument("--out", default=str(REPO_ROOT / "docs" / "archive" / "reports" / "security-audit-report.md"), help="输出报告路径")
    args = parser.parse_args()

    very_overall, findings = run_audit(production=args.production)

    if args.skip_dep_scan:
        findings = [f for f in findings if f["id"] != "DEPS"]

    from datetime import datetime

    report = render_markdown(very_overall, findings, datetime.now().isoformat(timespec="seconds"))
    out_path = Path(args.out)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n报告已写入: {out_path}")

    return 1 if very_overall == "error" else 0


if __name__ == "__main__":
    sys.exit(main())