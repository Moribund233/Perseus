"""
出站 URL 安全校验（SSRF 防护）

用于校验用户提交、服务端会对外发请求的 URL（如 WebHook 回调地址），
防止服务端请求伪造（SSRF）：禁止向私网、回环、链路本地、保留或组播地址发起请求。

校验策略（静态 + 可选 DNS 解析）：
- 仅允许 http/https 协议；
- 禁止内嵌用户信息（user:pass@）；
- hostname 为 IP 字面量时，直接用 ipaddress 判定地址类别；
- hostname 为域名时，通过 resolver 解析后检查所有结果地址，
  解析失败视为「请求本身无法发出」，不做拒绝（无安全损害）。
"""
from typing import Callable, List, Optional
from urllib.parse import urlparse

from core.exception import ValidationException


def _ip_is_forbidden(ip_str: str) -> bool:
    """
    判断 IP 地址是否属于禁止出站访问的类别

    Args:
        ip_str: IP 地址字符串（IPv4 或 IPv6）

    Returns:
        bool: 是否禁止
    """
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _default_resolver(host: str) -> List[str]:
    """
    默认 DNS 解析器：解析 host 对应的所有 IP 地址

    Args:
        host: 主机名

    Returns:
        list: IP 地址列表；解析失败返回空列表
    """
    import socket

    try:
        infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, OSError):
        return []

    ips: List[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    return ips


def validate_outbound_url(
    url: str,
    resolver: Optional[Callable[[str], List[str]]] = None,
    error_code: str = "webhook_invalid_url",
) -> str:
    """
    校验出站 URL 是否安全（SSRF 防护）

    Args:
        url: 待校验的 URL
        resolver: DNS 解析函数，输入 hostname，返回 IP 字符串列表
        error_code: 校验失败时抛出的异常 error_code

    Returns:
        str: 校验通过的规范化 URL

    Raises:
        ValidationException: URL 不安全时抛出
    """
    if not url or not url.strip():
        raise ValidationException(detail="URL 不能为空", error_code=error_code)

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        raise ValidationException(
            detail="无效的 URL，仅支持 http/https 协议", error_code=error_code
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationException(detail="无效的 URL，缺少主机名", error_code=error_code)

    # 禁止 URL 内嵌用户信息（可被用于混淆真正的目标主机）
    if parsed.username or parsed.password:
        raise ValidationException(
            detail="无效的 URL，禁止内嵌用户信息", error_code=error_code
        )

    # 端口非法时 urlparse 的 port 属性会抛 ValueError
    try:
        port = parsed.port
    except ValueError:
        raise ValidationException(detail="无效的 URL，端口非法", error_code=error_code)

    if port is not None and not (1 <= port <= 65535):
        raise ValidationException(detail="无效的 URL，端口非法", error_code=error_code)

    import ipaddress

    try:
        ip = ipaddress.ip_address(hostname)
        if _ip_is_forbidden(hostname):
            raise ValidationException(
                detail=f"禁止访问内网或保留地址: {hostname}", error_code=error_code
            )
        return url.strip()
    except ValueError:
        pass  # 域名，走 DNS 解析检查

    hostname_lower = hostname.lower().rstrip(".")
    # 常见的本机/链路本地主机名，DNS 解析结果通常指向回环地址
    if hostname_lower in ("localhost", "localhost.localdomain", "ip6-localhost"):
        raise ValidationException(
            detail=f"禁止访问本机地址: {hostname}", error_code=error_code
        )

    resolve = resolver or _default_resolver
    ips = resolve(hostname) or []
    for candidate in ips:
        if _ip_is_forbidden(candidate):
            raise ValidationException(
                detail=f"禁止访问内网或保留地址: {candidate}（{hostname}）",
                error_code=error_code,
            )

    return url.strip()