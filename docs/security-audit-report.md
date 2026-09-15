# Perseus 安全审计报告（F-056）

- 审计时间: 2026-09-15T11:17:30
- 总体状态: **WARN**

| 检查项 | 状态 | 详情 |
|--------|------|------|
| CORS 配置检查 | warn | allow_origins='*'：开发环境可接受，生产必须由 Nginx 白名单收敛 |
| CSRF 防护检查 | ok | 认证基于 Bearer Token（Authorization 头），非 Cookie 会话，天然规避传统 CSRF |
| SSRF 防护检查（WebHook 出站 URL） | ok | WebHook 创建/更新已接入 validate_outbound_url（禁止内网/回环/保留地址） |
| 依赖漏洞扫描 | info | 未安装 pip-audit，跳过在线漏洞扫描。安装: pip install pip-audit |

> 说明：DEPS 项仅提示，实际 CVE 扫描请安装 pip-audit 后执行 `python -m pip_audit`。
