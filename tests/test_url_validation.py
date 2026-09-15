"""
URL 出站安全校验（SSRF 防护）测试

覆盖 validate_outbound_url 的协议、凭据、内网/回环/保留地址拦截与放行场景。
所有 DNS 解析均通过注入的 resolver 控制，不产生真实网络请求。
"""
import pytest

from core.exception import ValidationException
from utils.url_validation import validate_outbound_url


# 公网 IP 与内网 IP 的固定 resolver 映射
PUBLIC_IPS = ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"]
PRIVATE_IPS = ["192.168.1.10", "10.0.0.5", "172.16.0.7"]


def resolver_for(ips=None):
    """构造一个固定返回指定 IP 列表的 resolver"""
    ips = ips or PUBLIC_IPS

    def _resolver(host: str):
        return list(ips)

    return _resolver


def assert_forbidden(url, resolver=None):
    with pytest.raises(ValidationException) as exc_info:
        validate_outbound_url(url, resolver=resolver)
    assert exc_info.value.error_code == "webhook_invalid_url"


def test_accept_public_domain():
    assert (
        validate_outbound_url("https://example.com/hook", resolver=resolver_for())
        == "https://example.com/hook"
    )


def test_accept_public_ipv4():
    assert (
        validate_outbound_url("http://93.184.216.34/hook", resolver=resolver_for())
        == "http://93.184.216.34/hook"
    )


def test_accept_public_ipv6():
    assert (
        validate_outbound_url(
            "http://[2606:2800:220:1:248:1893:25c8:1946]/hook",
            resolver=resolver_for(),
        )
        == "http://[2606:2800:220:1:248:1893:25c8:1946]/hook"
    )


def test_reject_loopback_literal():
    assert_forbidden("http://127.0.0.1/hook")
    assert_forbidden("http://localhost/hook")
    assert_forbidden("http://[::1]/hook")


def test_reject_private_ip_literals():
    for ip in ["10.0.0.1", "172.16.0.1", "172.31.255.254", "192.168.0.1"]:
        assert_forbidden(f"http://{ip}/hook")


def test_reject_link_local_and_metadata():
    for ip in ["169.254.169.254", "169.254.1.2"]:
        assert_forbidden(f"http://{ip}/latest/meta-data/")


def test_reject_reserved_and_unspecified():
    assert_forbidden("http://0.0.0.0/x")
    assert_forbidden("http://255.255.255.255/x")


def test_reject_domain_resolving_to_private():
    assert_forbidden("https://internal.example.net/hook", resolver=resolver_for(PRIVATE_IPS))


def test_reject_domain_resolving_to_loopback():
    assert_forbidden("http://metadata.example.local/hook", resolver=resolver_for(["127.0.0.1"]))


def test_reject_non_http_scheme():
    for scheme in ["ftp://example.com/x", "file:///etc/passwd", "gopher://example.com", ""]:
        assert_forbidden(scheme)


def test_reject_missing_or_empty_url():
    assert_forbidden("")
    assert_forbidden("   ")
    assert_forbidden(None)


def test_reject_embedded_credentials():
    assert_forbidden("http://user:pass@example.com/hook")
    assert_forbidden("http://user@example.com/hook")


def test_reject_invalid_port():
    assert_forbidden("https://example.com:99999/hook", resolver=resolver_for())


def test_accept_valid_port():
    assert (
        validate_outbound_url("https://example.com:8443/hook", resolver=resolver_for())
        == "https://example.com:8443/hook"
    )


def test_resolver_failure_allows_request_to_fail_naturally():
    # DNS 解析失败 => 请求本身无法发出，视为可接受
    def _dead_resolver(host: str):
        return []

    assert (
        validate_outbound_url("https://no-such-host.invalid/hook", resolver=_dead_resolver)
        == "https://no-such-host.invalid/hook"
    )


def test_reject_when_any_resolved_ip_is_private():
    # 解析结果同时含公网与内网地址时必须拦截
    resolver = resolver_for(["1.2.3.4", "10.10.10.10", "8.8.8.8"])
    assert_forbidden("https://hybrid.example.com/hook", resolver=resolver)