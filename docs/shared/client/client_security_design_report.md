# 客户端安全设计分析报告

**生成日期**: 2026-02-22  
**分析范围**: Tauri 客户端安全架构（Rust 层 + 前端）  
**分析目的**: 评估安全设计的合理性，识别潜在风险

---

## 一、安全架构概述

### 1.1 整体安全架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue3)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  无直接访问敏感数据权限                                  │   │
│  │  - 通过 Tauri Command 调用 Rust API                     │   │
│  │  - 数据库 URL 由 Rust 层注入环境变量                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Tauri Rust 中间层                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐   │
│  │   secure_config.rs  │    │      local_auth.rs          │   │
│  │  ┌───────────────┐  │    │  ┌─────────────────────┐    │   │
│  │  │ AES-256-GCM   │  │    │  │ JWT Secret Key      │    │   │
│  │  │ 加密存储       │  │    │  │ Local Token         │    │   │
│  │  │               │  │    │  │ X-LanGit-Local 头   │    │   │
│  │  │ client-config │  │    │  └─────────────────────┘    │   │
│  │  │ .json         │  │    │                             │   │
│  │  └───────────────┘  │    │  本地认证管理               │   │
│  └─────────────────────┘    └─────────────────────────────┘   │
│  ┌─────────────────────┐    ┌─────────────────────────────┐   │
│  │     config.rs       │    │      api_client.rs          │   │
│  │  ┌───────────────┐  │    │                             │   │
│  │  │ client.toml   │  │    │  HTTP 客户端 + 认证头注入   │   │
│  │  │ 非敏感配置     │  │    │                             │   │
│  │  └───────────────┘  │    └─────────────────────────────┘   │
│  └─────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      服务端 (FastAPI)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  本地认证验证                                           │   │
│  │  - 验证 X-LanGit-Local 头                               │   │
│  │  - 验证 JWT Token（使用 LANGIT_SECURITY_SECRET_KEY）    │   │
│  │  - 无需用户登录（本地可信环境）                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 安全设计原则

| 原则 | 实现方式 |
|------|----------|
| **敏感数据不落地前端** | 数据库 URL、JWT 密钥等存储在 Rust 加密配置中 |
| **分层存储** | 敏感配置（加密 JSON）与非敏感配置（TOML）分离 |
| **机器绑定加密** | 使用机器特征生成密钥，配置文件无法跨机器使用 |
| **本地可信认证** | 本地客户端与服务端通过共享密钥认证，无需用户交互 |
| **环境变量注入** | 敏感数据通过环境变量传递给子进程（服务端） |

---

## 二、核心安全机制详解

### 2.1 加密存储机制（secure_config.rs）

#### 2.1.1 加密方案

```rust
// 加密算法: AES-256-GCM
// 密钥派生: PBKDF2-HMAC-SHA256 (100,000 次迭代)
// 密钥材料: 机器特征（用户名 + 计算机名 + 临时目录）

加密流程:
1. 生成机器相关密钥材料
   key_material = SHA256("{username}@{computername}_{temp_dir}_langit_secure_key_v2")

2. 派生加密密钥
   key = PBKDF2(key_material, salt, iterations=100000)

3. AES-256-GCM 加密
   ciphertext = AES-GCM-Encrypt(plaintext, key, nonce)

4. 存储格式
   {
     "version": 2,
     "encrypted": true,
     "data": "base64(ciphertext)",
     "salt": "base64(salt)",
     "nonce": "base64(nonce)"
   }
```

#### 2.1.2 向后兼容

支持自动迁移旧版加密配置：
- **Version 0/1**: XOR 加密（已废弃，用于迁移）
- **Version 2**: AES-256-GCM（当前版本）

```rust
if encrypted.version == CURRENT_ENCRYPTION_VERSION {
    decrypt_config(&encrypted)           // AES-256-GCM
} else if encrypted.version == 0 || encrypted.version == 1 {
    decrypt_config_legacy(&encrypted)    // XOR (迁移后保存为新版本)
}
```

#### 2.1.3 存储的敏感数据

```rust
pub struct SecureConfig {
    pub jwt_secret_key: String,          // JWT 签名密钥
    pub local_token: String,             // 本地管理员 Token
    pub debug_mode: bool,                // 调试模式
    pub security_password: String,       // 客户端安全密码
    pub key_version: u32,                // 密钥版本（轮换用）
    pub stress_test: bool,               // 压力测试模式
    pub database_urls: HashMap<String, String>, // 数据库 URL 钥匙串
}
```

### 2.2 本地认证机制（local_auth.rs）

#### 2.2.1 认证流程

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────→│  Tauri Rust  │────→│   Server    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. 生成密钥对      │                    │
      │     (JWT Secret    │                    │
      │      + Local Token)│                    │
      │                    │                    │
      │  2. 保存到加密配置  │                    │
      │                    │                    │
      │  3. 启动服务端      │                    │
      │     注入环境变量    │                    │
      │     - LANGIT_SECURITY_SECRET_KEY
      │     - LANGIT_LOCAL_TOKEN           │
      │                    │  4. HTTP 请求     │
      │                    │  注入认证头       │
      │                    │  - Authorization: Bearer {token}
      │                    │  - X-LanGit-Local: 1            │
      │                    │──────────────────→│
      │                    │                    │ 5. 验证
      │                    │                    │    - X-LanGit-Local 头存在
      │                    │                    │    - JWT Token 签名有效
      │                    │  6. 返回响应      │
      │                    │←──────────────────│
```

#### 2.2.2 认证头格式

```rust
// 本地认证请求头
LOCAL_AUTH_HEADER: "X-LanGit-Local"
LOCAL_AUTH_HEADER_VALUE: "1"

// 生成的请求头
[
    ("Authorization", "Bearer langit_local_{timestamp}_{random}"),
    ("X-LanGit-Local", "1")
]
```

#### 2.2.3 Token 格式

```
格式: langit_local_{timestamp}_{random_base64url}
示例: langit_local_1708608000_aB3dE5fG7hI9jK0

- timestamp: Unix 时间戳（秒）
- random: 32 字节随机数（Base64 URL Safe 编码）
```

### 2.3 配置分离策略

#### 2.3.1 敏感配置（client-config.json）

| 配置项 | 说明 | 加密存储 |
|--------|------|----------|
| `jwt_secret_key` | JWT 签名密钥 | ✅ AES-256-GCM |
| `local_token` | 本地管理员 Token | ✅ AES-256-GCM |
| `database_urls` | 数据库连接 URL | ✅ AES-256-GCM |
| `security_password` | 客户端安全密码 | ✅ AES-256-GCM |
| `debug_mode` | 调试模式开关 | ✅ AES-256-GCM |
| `stress_test` | 压力测试模式 | ✅ AES-256-GCM |

#### 2.3.2 非敏感配置（client.toml）

| 配置项 | 说明 | 明文存储 |
|--------|------|----------|
| `server.url` | 服务端地址 | ✅ TOML |
| `appearance.theme` | 主题设置 | ✅ TOML |
| `notification.enabled` | 通知开关 | ✅ TOML |
| `db_type` | 当前选择的数据库类型 | ✅ TOML |
| `advanced.*` | 高级设置 | ✅ TOML |

---

## 三、安全优势分析

### 3.1 设计亮点

| 亮点 | 说明 |
|------|------|
| **机器绑定** | 配置文件使用机器特征加密，复制到其他机器无法解密 |
| **分层存储** | 敏感与非敏感配置分离，降低攻击面 |
| **自动密钥轮换** | 支持 `rotate_keys()` 更新密钥和 Token |
| **向后兼容** | 自动迁移旧版加密配置，平滑升级 |
| **无密码本地认证** | 本地环境无需用户登录，体验友好且安全 |
| **环境变量隔离** | 敏感数据通过环境变量传递，不写入日志 |

### 3.2 安全边界

```
┌────────────────────────────────────────────────────────────┐
│  攻击者获取 client-config.json                              │
│  └──→ 无法解密（需要相同机器特征）                           │
│                                                            │
│  攻击者获取 client.toml                                     │
│  └──→ 仅获得非敏感配置（服务端地址等）                       │
│                                                            │
│  攻击者获取内存中的环境变量                                 │
│  └──→ 需要本地代码执行权限（已控制机器）                     │
│                                                            │
│  攻击者网络嗅探 HTTP 请求                                   │
│  └──→ 获得临时 Token（可配合 HTTPS 增强）                    │
└────────────────────────────────────────────────────────────┘
```

---

## 四、发现的问题与风险

### 4.1 【中优先级】机器特征不够稳定

**问题描述**:
密钥材料依赖环境变量（USERNAME, COMPUTERNAME, TEMP），这些变量可能被修改。

```rust
fn generate_machine_key_material() -> Vec<u8> {
    let username = std::env::var("USERNAME")  // 可被修改
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "default_user".to_string());

    let computername = std::env::var("COMPUTERNAME")  // 可被修改
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "default_host".to_string());

    let temp_dir = std::env::var("TEMP")  // 可被修改
        .or_else(|_| std::env::var("TMP"))
        .unwrap_or_else(|_| "/tmp".to_string());
    // ...
}
```

**风险场景**:
- 用户修改环境变量后，无法读取原有配置
- 需要重新初始化，导致数据丢失

**风险等级**: 🟡 中

**改进建议**:
```rust
// 使用更稳定的机器特征
use machine_uid::get_machine_id;  // 或使用硬件信息

fn generate_machine_key_material() -> Vec<u8> {
    // 优先使用硬件 ID
    let machine_id = get_machine_id()
        .unwrap_or_else(|| {
            // 回退到环境变量
            format!("{}@{}", username, computername)
        });
    
    // 或使用多因素组合
    let key_material = format!(
        "{}_{}_{}_langit_secure_key_v2",
        machine_id, username, computername
    );
    // ...
}
```

### 4.2 【中优先级】缺少配置完整性校验

**问题描述**:
配置文件可能被篡改，但系统未检测完整性。

**风险场景**:
- 攻击者修改 `debug_mode` 或 `stress_test` 开关
- 恶意替换 `database_urls` 中的 URL

**风险等级**: 🟡 中

**改进建议**:
```rust
// 添加 HMAC 签名
pub struct EncryptedConfig {
    // ... 现有字段
    hmac: String,  // HMAC-SHA256(data + salt + nonce)
}

fn encrypt_config(config: &SecureConfig) -> Result<EncryptedConfig, String> {
    // ... 加密逻辑
    
    // 计算 HMAC
    let hmac = compute_hmac(&encrypted_data, &salt, &nonce, &key);
    
    Ok(EncryptedConfig {
        // ...
        hmac,
    })
}

fn decrypt_config(encrypted: &EncryptedConfig) -> Result<SecureConfig, String> {
    // 验证 HMAC
    let expected_hmac = compute_hmac(&data, &salt, &nonce, &key);
    if !constant_time_eq(&encrypted.hmac, &expected_hmac) {
        return Err("配置完整性校验失败".to_string());
    }
    // ... 解密逻辑
}
```

### 4.3 【低优先级】Token 格式可预测

**问题描述**:
Token 包含时间戳，格式相对固定。

```
langit_local_{timestamp}_{random}
```

**风险场景**:
- 攻击者知道 Token 生成时间，缩小暴力破解范围
- 但随机部分有 32 字节，实际风险较低

**风险等级**: 🟢 低

**改进建议**:
```rust
// 使用纯随机格式
pub fn generate_local_token() -> String {
    let token_bytes: Vec<u8> = (0..48)  // 增加长度
        .map(|_| rand::thread_rng().gen::<u8>())
        .collect();
    
    // 不包含时间戳
    URL_SAFE_NO_PAD.encode(&token_bytes)
}
```

### 4.4 【低优先级】缺少访问控制

**问题描述**:
任何前端代码都可以调用 Tauri Command 读取敏感配置。

**风险场景**:
- 恶意前端代码可以读取 `database_urls`
- 虽然需要打包进应用，但仍存在风险

**风险等级**: 🟢 低

**改进建议**:
```rust
// 添加调用者验证
#[tauri::command]
pub fn get_database_url(
    db_type: String,
    app_handle: tauri::AppHandle,
) -> Result<String, String> {
    // 验证调用者是否来自受信任的窗口
    if !is_trusted_window(&app_handle) {
        return Err("未授权的访问".to_string());
    }
    
    crate::secure_config::get_database_url(&db_type)
}
```

### 4.5 【低优先级】环境变量残留

**问题描述**:
服务端进程结束后，环境变量可能残留在内存中。

**风险场景**:
- 其他进程可能读取到 `DATABASE_URL` 等敏感信息
- 系统崩溃时可能写入转储文件

**风险等级**: 🟢 低

**改进建议**:
```rust
// 使用内存文件或管道传递敏感数据
// 替代环境变量方案
pub fn start_server_with_secure_config(config: &SecureConfig) -> Result<Child, String> {
    // 创建临时内存文件
    let temp_file = create_secure_temp_file()?;
    write_encrypted_config(&temp_file, config)?;
    
    // 只传递文件路径（权限限制为仅当前用户可读）
    let child = Command::new("langit-server")
        .env("LANGIT_CONFIG_PATH", temp_file.path())
        .spawn()?;
    
    // 启动后删除文件（服务端已读取）
    temp_file.close()?;
    
    Ok(child)
}
```

---

## 五、文件位置汇总

### 5.1 Rust 安全模块

| 文件 | 职责 | 关键函数/结构体 |
|------|------|-----------------|
| `secure_config.rs` | 加密配置管理 | `SecureConfig`, `encrypt_config()`, `decrypt_config()` |
| `local_auth.rs` | 本地认证管理 | `generate_jwt_secret_key()`, `generate_local_token()`, `get_auth_headers()` |
| `config.rs` | 非敏感配置管理 | `ClientConfig`, `load_config()`, `save_config()` |
| `api_client.rs` | HTTP 客户端 + 认证注入 | `ApiClient`, `build_headers()` |
| `commands.rs` | Tauri Command 接口 | `get_database_url()`, `get_jwt_secret_key()` |

### 5.2 前端安全相关

| 文件 | 职责 | 说明 |
|------|------|------|
| `services/api.ts` | API 封装 | 调用 Tauri Command 获取敏感数据 |
| `stores/database.ts` | 数据库状态管理 | 通过 API 获取 URL，不直接存储 |
| `components/settings/DeveloperOptions.vue` | 开发者选项 | 显示/修改敏感配置（需要权限） |

### 5.3 配置文件位置

| 文件 | 位置 | 说明 |
|------|------|------|
| `client-config.json` | `%APPDATA%/langit-client/` (Windows)<br>`~/.config/langit-client/` (Linux) | 加密敏感配置 |
| `client.toml` | 同上 | 非敏感配置 |

---

## 六、改进优先级建议

### 6.1 第一阶段（稳定性提升）

1. **使用更稳定的机器特征**
   - 引入硬件 ID 或系统 UUID
   - 提供配置恢复机制
   - 预计工作量: 1 天

### 6.2 第二阶段（完整性保护）

2. **添加配置完整性校验**
   - HMAC-SHA256 签名
   - 防篡改检测
   - 预计工作量: 0.5 天

### 6.3 第三阶段（增强防护）

3. **Token 格式改进**
   - 移除时间戳，使用纯随机格式
   - 增加 Token 长度
   - 预计工作量: 0.5 天

4. **访问控制增强**
   - 验证调用者身份
   - 添加操作审计日志
   - 预计工作量: 1 天

---

## 七、总结

### 7.1 优势

1. **加密强度高**: AES-256-GCM + PBKDF2-HMAC-SHA256，符合行业标准
2. **架构合理**: 敏感与非敏感配置分离，职责清晰
3. **用户体验好**: 本地认证无需用户输入密码
4. **向后兼容**: 自动迁移旧版配置，平滑升级
5. **机器绑定**: 配置文件无法跨机器使用

### 7.2 待改进

1. **稳定性**: 机器特征依赖环境变量，不够稳定
2. **完整性**: 缺少配置防篡改机制
3. **可预测性**: Token 格式包含时间戳
4. **访问控制**: 前端可以无限制调用安全 API

### 7.3 总体评价

客户端安全设计**整体优秀**，采用了业界标准的加密算法和合理的架构设计。主要问题在于**稳定性**（机器特征）和**完整性保护**（防篡改），建议按照优先级逐步改进。

---

**报告完成**
