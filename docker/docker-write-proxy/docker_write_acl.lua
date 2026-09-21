-- docker_write_acl.lua — 窄写 Docker 代理 ACL（静态白名单）
--
-- 放行规则（全部满足才允许，其余一律 403）：
--   1. 方法必须为 POST；
--   2. URI 形如 /containers/{id}/{start|stop|restart}。
--
-- 背景: 内网部署，威胁面为本 compose 网络内可能被攻破的应用容器。
-- 由此代理只开放上述最小写窗口：无法 create/exec/pull/remove 等控制面操作，
-- 读操作不经过本代理（只读 docker-socket-proxy POST=0 承担）。
-- 「目标容器归属本项目」的表达式运算在应用层完成: 后端只会对监控栈的两个
-- 容器 ID 发起启停请求，代理无需也无法得知具体 ID 的归属，故本文件不再依赖
-- docker socket，保持纯静态检查，便于维护。
--
-- 挂载:
--   ./nginx.conf               -> /usr/local/openresty/nginx/conf/nginx.conf:ro
--   ./docker_write_acl.lua     -> /etc/nginx/docker_write_acl.lua:ro

local method = ngx.req.get_method() or ""
local uri = ngx.var.uri or ""

if method ~= "POST" then
    return ngx.exit(403)
end

local m, err = ngx.re.match(uri, "^/containers/([0-9a-f]{6,64})/(start|stop|restart)$", "ijo")
if not m then
    return ngx.exit(403)
end

-- 校验通过: 交由 proxy_pass 转交 Docker daemon