/**
 * 配置生成模块
 *
 * 生成Nginx配置文件内容
 */
use crate::models::NginxProxyConfig;

/**
 * 从后端URL提取主机地址
 *
 * @param backend_url 后端URL，如 http://127.0.0.1:8000
 * @return 主机地址，如 127.0.0.1:8000
 */
fn extract_backend_host(backend_url: &str) -> String {
    backend_url
        .trim_start_matches("http://")
        .trim_start_matches("https://")
        .to_string()
}

/**
 * 生成代理配置块
 *
 * @param config 代理配置
 * @param indent 缩进空格数
 * @return 代理配置字符串
 */
fn generate_proxy_config(config: &NginxProxyConfig, indent: usize) -> String {
    let spaces = " ".repeat(indent);
    let mut proxy_conf = String::new();

    if config.enable_keepalive {
        proxy_conf.push_str(&format!("{}proxy_pass http://langit_backend;\n", spaces));
    } else {
        proxy_conf.push_str(&format!("{}proxy_pass {};\n", spaces, config.backend_url));
    }

    proxy_conf.push_str(&format!("{}proxy_set_header Host $http_host;\n", spaces));
    proxy_conf.push_str(&format!(
        "{}proxy_set_header X-Real-IP $remote_addr;\n",
        spaces
    ));
    proxy_conf.push_str(&format!(
        "{}proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n",
        spaces
    ));
    proxy_conf.push_str(&format!(
        "{}proxy_set_header X-Forwarded-Proto $scheme;\n",
        spaces
    ));
    proxy_conf.push_str(&format!("{}proxy_pass_request_headers on;\n", spaces));
    proxy_conf.push_str(&format!(
        "{}proxy_redirect ~^http://[^/]+(/.+)$ $scheme://$http_host$1;\n",
        spaces
    ));
    proxy_conf.push_str(&format!(
        "{}proxy_connect_timeout {}s;\n",
        spaces, config.connect_timeout
    ));
    proxy_conf.push_str(&format!(
        "{}proxy_send_timeout {}s;\n",
        spaces, config.send_timeout
    ));
    proxy_conf.push_str(&format!(
        "{}proxy_read_timeout {}s;\n",
        spaces, config.read_timeout
    ));

    if config.enable_keepalive {
        proxy_conf.push_str(&format!("{}proxy_http_version 1.1;\n", spaces));
        proxy_conf.push_str(&format!("{}proxy_set_header Connection \"\";\n", spaces));
    }

    if config.enable_performance {
        proxy_conf.push_str(&format!("{}proxy_buffering on;\n", spaces));
        proxy_conf.push_str(&format!("{}proxy_buffer_size 4k;\n", spaces));
        proxy_conf.push_str(&format!("{}proxy_buffers 8 4k;\n", spaces));
    }

    proxy_conf
}

/**
 * 生成CORS预检响应配置
 *
 * @param config 代理配置
 * @param indent 缩进空格数
 * @param methods 允许的HTTP方法
 * @return CORS配置字符串
 */
fn generate_cors_preflight_config(
    config: &NginxProxyConfig,
    indent: usize,
    methods: &str,
) -> String {
    let spaces = " ".repeat(indent);
    let inner_spaces = " ".repeat(indent + 4);
    let mut cors_conf = String::new();

    cors_conf.push_str(&format!("{}if ($request_method = 'OPTIONS') {{\n", spaces));
    cors_conf.push_str(&format!(
        "{}add_header 'Access-Control-Allow-Origin' '{}';\n",
        inner_spaces, config.cors_origins
    ));
    cors_conf.push_str(&format!(
        "{}add_header 'Access-Control-Allow-Credentials' 'true';\n",
        inner_spaces
    ));
    cors_conf.push_str(&format!(
        "{}add_header 'Access-Control-Allow-Methods' '{}';\n",
        inner_spaces, methods
    ));
    cors_conf.push_str(&format!(
        "{}add_header 'Access-Control-Allow-Headers' '{}';\n",
        inner_spaces, config.cors_headers
    ));
    cors_conf.push_str(&format!(
        "{}add_header 'Access-Control-Max-Age' 1728000;\n",
        inner_spaces
    ));
    cors_conf.push_str(&format!("{}add_header 'Content-Length' 0;\n", inner_spaces));
    cors_conf.push_str(&format!("{}return 204;\n", inner_spaces));
    cors_conf.push_str(&format!("{}}}\n", spaces));

    cors_conf
}

/**
 * 将路径转换为Nginx配置兼容格式
 * 在Windows上将反斜杠转换为正斜杠
 *
 * @param path 原始路径
 * @return 转换后的路径
 */
fn to_nginx_path(path: &str) -> String {
    path.replace('\\', "/")
}

/**
 * 生成Nginx配置文件内容
 *
 * @param config 代理配置
 * @param config_dir 配置目录
 * @return nginx.conf内容
 */
pub fn generate_nginx_config(config: &NginxProxyConfig, config_dir: &str) -> String {
    let mut nginx_conf = String::new();
    let nginx_path = to_nginx_path(config_dir);

    nginx_conf.push_str(&format!(
        "worker_processes {};\n\n",
        config.worker_processes
    ));
    nginx_conf.push_str("# PID文件路径\n");
    nginx_conf.push_str(&format!("pid {}/logs/nginx.pid;\n\n", nginx_path));

    nginx_conf.push_str("events {\n");
    nginx_conf.push_str("    worker_connections 1024;\n");
    if config.enable_performance && cfg!(target_os = "linux") {
        nginx_conf.push_str("    use epoll;\n");
        nginx_conf.push_str("    multi_accept on;\n");
    }
    nginx_conf.push_str("}\n\n");

    nginx_conf.push_str("http {\n");
    nginx_conf.push_str(&format!("    include       {}/mime.types;\n", nginx_path));
    nginx_conf.push_str("    default_type  application/octet-stream;\n\n");
    nginx_conf.push_str(&format!(
        "    access_log    {}/logs/access.log;\n",
        nginx_path
    ));
    nginx_conf.push_str(&format!(
        "    error_log     {}/logs/error.log;\n\n",
        nginx_path
    ));
    nginx_conf.push_str("    sendfile        on;\n");

    if config.enable_performance {
        nginx_conf.push_str("    tcp_nopush      on;\n");
        nginx_conf.push_str("    tcp_nodelay     on;\n");
        nginx_conf.push_str("    client_body_buffer_size 128k;\n");
        nginx_conf.push_str("    client_max_body_size 50m;\n");
    }

    nginx_conf.push_str("    keepalive_timeout  65;\n\n");

    if config.enable_keepalive {
        nginx_conf.push_str("    # 上游服务器配置\n");
        nginx_conf.push_str("    upstream langit_backend {\n");
        nginx_conf.push_str(&format!(
            "        server {};\n",
            extract_backend_host(&config.backend_url)
        ));
        nginx_conf.push_str(&format!(
            "        keepalive {};\n",
            config.keepalive_connections
        ));
        nginx_conf.push_str("    }\n\n");
    }

    nginx_conf.push_str("    server {\n");
    // 根据监听地址生成listen指令
    let listen_addr = if config.listen_address.is_empty() || config.listen_address == "0.0.0.0" {
        config.listen_port.to_string()
    } else {
        format!("{}:{}", config.listen_address, config.listen_port)
    };
    nginx_conf.push_str(&format!("        listen {};\n", listen_addr));
    nginx_conf.push_str(&format!("        server_name {};\n\n", config.server_name));

    if config.add_security_headers {
        nginx_conf.push_str("        # 安全头\n");
        nginx_conf.push_str("        add_header X-Frame-Options \"SAMEORIGIN\" always;\n");
        nginx_conf.push_str("        add_header X-Content-Type-Options \"nosniff\" always;\n");
        nginx_conf.push_str("        add_header X-XSS-Protection \"1; mode=block\" always;\n");
        nginx_conf.push_str(
            "        add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;\n",
        );

        if config.enable_hsts {
            nginx_conf.push_str(&format!(
                "        add_header Strict-Transport-Security \"max-age={}; includeSubDomains\" always;\n",
                config.hsts_max_age
            ));
        }
        nginx_conf.push('\n');
    }

    if config.add_cors_headers {
        nginx_conf.push_str("        # CORS配置\n");
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Origin' '{}' always;\n",
            config.cors_origins
        ));
        nginx_conf
            .push_str("        add_header 'Access-Control-Allow-Credentials' 'true' always;\n");
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Methods' '{}' always;\n",
            config.cors_methods
        ));
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Headers' '{}' always;\n",
            config.cors_headers
        ));

        nginx_conf.push('\n');
        nginx_conf.push_str("        # CORS预检请求处理\n");
        nginx_conf.push_str("        location = /api/v1/auth/login {\n");
        nginx_conf.push_str("            # 处理OPTIONS预检请求\n");
        nginx_conf.push_str(&generate_cors_preflight_config(config, 12, "POST, OPTIONS"));
        nginx_conf.push('\n');
        nginx_conf.push_str(&generate_proxy_config(config, 12));
        nginx_conf.push_str("        }\n\n");

        // API请求代理到后端
        nginx_conf.push_str("        # API请求代理\n");
        nginx_conf.push_str("        location /api/ {\n");
        nginx_conf.push_str(&generate_cors_preflight_config(
            config,
            12,
            &config.cors_methods,
        ));
        nginx_conf.push('\n');
        nginx_conf.push_str(&generate_proxy_config(config, 12));
        nginx_conf.push_str("        }\n\n");

        // Git HTTP协议代理
        nginx_conf.push_str("        # Git HTTP协议代理\n");
        nginx_conf.push_str("        location ~* ^/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\\.git/ {\n");
        nginx_conf.push_str(&generate_cors_preflight_config(
            config,
            12,
            &config.cors_methods,
        ));
        nginx_conf.push('\n');
        nginx_conf.push_str(&generate_proxy_config(config, 12));
        nginx_conf.push_str("        }\n\n");

        // 如果配置了前端静态文件路径，添加静态文件服务
        if !config.frontend_path.is_empty() {
            nginx_conf.push_str("        # 前端静态文件服务\n");
            nginx_conf.push_str("        location / {\n");
            // 确保路径末尾有斜杠
            let frontend_path = to_nginx_path(&config.frontend_path);
            let frontend_path = if frontend_path.ends_with('/') {
                frontend_path
            } else {
                format!("{}/", frontend_path)
            };
            nginx_conf.push_str(&format!("            alias {};\n", frontend_path));
            nginx_conf.push_str("            index index.html;\n");
            nginx_conf.push_str("            try_files $uri $uri/ =404;\n");
            nginx_conf.push_str("            add_header Cache-Control \"no-cache\";\n");
            nginx_conf.push_str("        }\n\n");
        } else {
            nginx_conf.push_str("        # 默认代理所有请求\n");
            nginx_conf.push_str("        location / {\n");
            nginx_conf.push_str(&generate_cors_preflight_config(
                config,
                12,
                &config.cors_methods,
            ));
            nginx_conf.push('\n');
            nginx_conf.push_str(&generate_proxy_config(config, 12));
            nginx_conf.push_str("        }\n");
        }
    } else {
        // API请求代理到后端
        nginx_conf.push_str("        # API请求代理\n");
        nginx_conf.push_str("        location /api/ {\n");
        nginx_conf.push_str(&generate_proxy_config(config, 12));
        nginx_conf.push_str("        }\n\n");

        // Git HTTP协议代理
        nginx_conf.push_str("        # Git HTTP协议代理\n");
        nginx_conf.push_str("        location ~* ^/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\\.git/ {\n");
        nginx_conf.push_str(&generate_proxy_config(config, 12));
        nginx_conf.push_str("        }\n\n");

        // 如果配置了前端静态文件路径，添加静态文件服务
        if !config.frontend_path.is_empty() {
            nginx_conf.push_str("        # 前端静态文件服务\n");
            nginx_conf.push_str("        location / {\n");
            // 确保路径末尾有斜杠
            let frontend_path = to_nginx_path(&config.frontend_path);
            let frontend_path = if frontend_path.ends_with('/') {
                frontend_path
            } else {
                format!("{}/", frontend_path)
            };
            nginx_conf.push_str(&format!("            alias {};\n", frontend_path));
            nginx_conf.push_str("            index index.html;\n");
            nginx_conf.push_str("            try_files $uri $uri/ =404;\n");
            nginx_conf.push_str("            add_header Cache-Control \"no-cache\";\n");
            nginx_conf.push_str("        }\n\n");
        } else {
            nginx_conf.push_str("        # 默认代理所有请求\n");
            nginx_conf.push_str("        location / {\n");
            nginx_conf.push_str(&generate_proxy_config(config, 12));
            nginx_conf.push_str("        }\n");
        }
    }

    nginx_conf.push_str("    }\n");
    nginx_conf.push_str("}\n");

    nginx_conf
}
