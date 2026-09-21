-- =============================================================================
-- Admin 控制台来源白名单（OpenResty access_by_lua_file）
--
-- 供 /api/app/* 与 /grafana/* 两个网关 location 复用：
-- 仅允许 PERSEUS_ADMIN_ALLOWED_SOURCES 中列出的部署终端来源访问。
-- 列表以逗号/分号/空格分隔，支持精确 IP 与 IPv4 CIDR；
-- 留空 = 拒绝一切来源（安全优先，部署时在 .env 里配置）。
-- =============================================================================
local allowed = os.getenv("PERSEUS_ADMIN_ALLOWED_SOURCES") or ""
local ip = ngx.var.remote_addr

if allowed == "" then
    ngx.log(ngx.WARN, "admin console: 白名单为空, 拒绝 ", ip)
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

local bit = require("bit")

local function parse_ipv4(s)
    local a, b, c, d = s:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if not a then return nil end
    return tonumber(a) * 16777216 + tonumber(b) * 65536 + tonumber(c) * 256 + tonumber(d)
end

local function ip_allowed(ip_addr)
    for part in string.gmatch(allowed, "[^,;%s]+") do
        if part == ip_addr then return true end
        local base, bits = part:match("^(.*)/(%d+)$")
        if base then
            local want = parse_ipv4(base)
            local have = parse_ipv4(ip_addr)
            if want and have then
                local n = tonumber(bits)
                if n and n >= 0 and n <= 32 then
                    local mask
                    if n == 0 then mask = 0 else mask = bit.band(bit.lshift(0xFFFFFFFF, 32 - n), 0xFFFFFFFF) end
                    if bit.band(want, mask) == bit.band(have, mask) then return true end
                end
            end
        end
    end
    return false
end

if not ip_allowed(ip) then
    ngx.log(ngx.WARN, "admin console: 拒绝未授权来源 ", ip)
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end