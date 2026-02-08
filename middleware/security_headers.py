"""
安全响应头中间件

添加安全相关的 HTTP 响应头，防止常见的 Web 攻击
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import re


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件

    添加以下安全响应头：
    - X-Content-Type-Options: 防止 MIME 类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: 启用 XSS 过滤器
    - Strict-Transport-Security: 强制 HTTPS
    - Content-Security-Policy: 防止 XSS 和数据注入
    - Referrer-Policy: 控制 Referrer 信息
    - Permissions-Policy: 控制浏览器功能权限
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = False,
        hsts_max_age: int = 31536000,
        csp_policy: Optional[str] = None,
        allow_iframe: bool = False,
        add_security_headers: bool = True
    ):
        """
        初始化安全响应头中间件

        Args:
            app: FastAPI 应用实例
            enable_hsts: 是否启用 HSTS（生产环境建议启用）
            hsts_max_age: HSTS 最大年龄（秒）
            csp_policy: 自定义 CSP 策略
            allow_iframe: 是否允许在 iframe 中嵌入
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.allow_iframe = allow_iframe
        self.add_security_headers = add_security_headers

        # 默认 CSP 策略
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # 如果允许 iframe，修改 frame-ancestors
        if allow_iframe:
            self.csp_policy = re.sub(
                r"frame-ancestors 'none'",
                "frame-ancestors 'self'",
                self.csp_policy
            )

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并添加安全响应头

        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 带有安全响应头的 HTTP 响应
        """
        response: Response = await call_next(request)

        # 如果启用了 Nginx 反向代理，跳过添加这些头（由 Nginx 统一处理）
        if self.add_security_headers:
            # 防止 MIME 类型嗅探
            response.headers["X-Content-Type-Options"] = "nosniff"

            # 防止点击劫持
            if self.allow_iframe:
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
            else:
                response.headers["X-Frame-Options"] = "DENY"

            # 启用 XSS 过滤器
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Referrer 策略
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # 权限策略
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )

        # 强制 HTTPS (HSTS) - 始终由应用层控制
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # 注意：Content-Security-Policy 由 Nginx 统一添加，避免重复
        # 如果未使用 Nginx 反向代理，可以启用 add_security_headers
        # response.headers["Content-Security-Policy"] = self.csp_policy

        # 移除可能泄露信息的响应头
        for header in ["server", "x-powered-by"]:
            if header in response.headers:
                del response.headers[header]

        return response
