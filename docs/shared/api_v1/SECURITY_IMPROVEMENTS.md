# LanGit 安全改进总结

本文档总结了本次安全改进的所有内容，包括改进项、实现细节和使用说明。

## 📋 改进清单

### ✅ 已完成的高优先级改进

1. **客户端配置加密升级** - 将 XOR 加密替换为 AES-256-GCM
2. **Web 前端 Token 存储优化** - 内存存储 + 安全降级方案
3. **生产环境 CORS 配置收紧** - 可配置的跨域策略 + 安全默认值

### ✅ 已完成的中优先级改进

4. **密钥自动轮换机制** - 支持 JWT 密钥和本地 Token 轮换
5. **增强机器密钥安全性** - PBKDF2 密钥派生 + 多因素机器特征

---

## 🔐 1. 客户端配置加密升级

### 改进前
- **算法**: XOR 加密 + Base64 编码
- **安全性**: ⚠️ 弱，易被破解
- **密钥派生**: 简单的哈希组合

### 改进后
- **算法**: AES-256-GCM
- **安全性**: ✅ 强，业界标准
- **密钥派生**: PBKDF2-HMAC-SHA256，100,000 次迭代

### 实现文件
- `client/src-tauri/src/secure_config.rs`

### 关键特性
```rust
// 使用 AES-256-GCM 加密
fn aes_gcm_encrypt(plaintext: &[u8], key: &[u8], nonce: &[u8]) -> Result<Vec<u8>, String>

// PBKDF2 密钥派生
fn derive_key(key_material: &[u8], salt: &[u8]) -> Vec<u8> {
    pbkdf2_hmac::<Sha256>(key_material, salt, PBKDF2_ITERATIONS, &mut key)
}
```

### 向后兼容
- 自动检测旧版本加密配置
- 首次加载时自动迁移到新版本
- 保留旧版解密逻辑用于迁移

---

## 🌐 2. Web 前端 Token 存储优化

### 改进前
- **存储位置**: localStorage
- **风险**: ⚠️ XSS 攻击可窃取 Token

### 改进后
- **主要存储**: 内存（JavaScript 变量）
- **可选持久化**: localStorage（仅当用户选择"记住我"）
- **Token 过期**: 自动检测和清理

### 实现文件
- `frontend/src/utils/secureStorage.ts` (新增)
- `frontend/src/utils/api.ts` (更新)
- `frontend/src/stores/user.ts` (更新)

### 使用示例
```typescript
// 登录时选择是否记住我
const login = async (credentials, rememberMe = false) => {
  const response = await userApi.login(credentials, rememberMe);
  // Token 自动存储到内存或 localStorage
};

// 获取 Token（自动处理过期）
const token = getToken(); // 从内存或 localStorage 获取

// 检查 Token 是否即将过期
if (isTokenExpiringSoon(5)) { // 5分钟阈值
  console.warn('Token 即将过期');
}
```

### 安全特性
- ✅ Token 默认存储在内存中
- ✅ 页面刷新后 Token 丢失（更安全）
- ✅ 支持"记住我"选项（用户自主选择）
- ✅ 自动 Token 过期检测
- ✅ 敏感字段自动过滤

---

## 🛡️ 3. 生产环境 CORS 配置收紧

### 改进前
- **allow_origins**: `["*"]`（允许所有来源）
- **风险**: ⚠️ 生产环境使用通配符有安全风险

### 改进后
- **配置化**: 从配置文件读取 CORS 设置
- **安全默认值**: 生产环境强制使用安全默认值
- **警告日志**: 检测到不安全配置时发出警告

### 实现文件
- `config.py` - 新增 `CORSSettings` 配置类
- `app.py` - 使用配置的 CORS 设置
- `config.production.toml` - 生产环境配置示例

### 配置示例
```toml
[cors]
# 开发环境
allow_origins = ["*"]

# 生产环境（必须配置具体域名）
allow_origins = ["https://your-domain.com", "https://app.your-domain.com"]
allow_credentials = true
allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allow_headers = ["Content-Type", "Authorization", "X-Requested-With"]
max_age = 600
```

### 生产环境安全检查
```python
if not config.app.debug:
    if "*" in cors_config.allow_origins:
        logger.warning("生产环境检测到CORS allow_origins包含通配符'*'")
        # 强制使用安全默认值
        allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
```

---

## 🔄 4. 密钥自动轮换机制

### 功能说明
支持主动轮换 JWT 密钥和本地管理员 Token，增强安全性。

### 实现文件
- `client/src-tauri/src/secure_config.rs`
- `client/src-tauri/src/local_auth.rs`

### 使用方式
```rust
// 轮换密钥
pub fn rotate_keys() -> Result<SecureConfig, String> {
    let mut config = load_secure_config()?;
    
    // 生成新的 JWT 密钥
    config.jwt_secret_key = generate_jwt_secret_key();
    
    // 生成新的本地 Token
    config.local_token = generate_local_token();
    
    // 增加密钥版本
    config.key_version += 1;
    
    save_secure_config(&config)?;
    Ok(config)
}

// 获取当前密钥版本
pub fn get_key_version() -> Result<u32, String>
```

### 应用场景
- 定期安全维护
- 怀疑密钥泄露时
- 安全事件响应

---

## 🔑 5. 增强机器密钥安全性

### 改进前
- **机器特征**: 用户名 + 计算机名
- **密钥派生**: 简单哈希组合

### 改进后
- **机器特征**: 用户名 + 计算机名 + 临时目录路径
- **密钥派生**: PBKDF2-HMAC-SHA256，100,000 次迭代

### 实现细节
```rust
fn generate_machine_key_material() -> Vec<u8> {
    let username = std::env::var("USERNAME").unwrap_or_default();
    let computername = std::env::var("COMPUTERNAME").unwrap_or_default();
    let temp_dir = std::env::var("TEMP").unwrap_or_default();
    
    // 组合多个机器特征
    let key_material = format!(
        "{}@{}_{}_langit_secure_key_v2",
        username, computername, temp_dir
    );
    
    // 使用 SHA256 生成固定长度的密钥材料
    let mut hasher = Sha256::new();
    hasher.update(key_material.as_bytes());
    hasher.finalize().to_vec()
}
```

---

## 📦 依赖更新

### Rust 依赖 (`client/src-tauri/Cargo.toml`)
```toml
# 新增加密依赖
aes-gcm = "0.10"
sha2 = "0.10"
hmac = "0.12"
pbkdf2 = "0.12"
```

---

## 🚀 部署注意事项

### 1. 首次部署
```bash
# 1. 安装 Rust 依赖
cd client/src-tauri
cargo build

# 2. 前端依赖
cd frontend
npm install
```

### 2. 生产环境配置
1. 复制 `config.production.toml` 为 `config.toml`
2. 修改 `cors.allow_origins` 为您的实际域名
3. 通过环境变量设置 `LANGIT_SECURITY_SECRET_KEY`

### 3. 向后兼容
- ✅ 旧版本加密配置自动迁移
- ✅ 配置文件格式保持不变
- ✅ API 接口完全兼容

---

## 🧪 测试建议

### 1. 加密功能测试
```bash
cd client/src-tauri
cargo test secure_config
```

### 2. 安全存储测试
```bash
cd frontend
npm test
```

### 3. CORS 配置测试
```bash
# 启动服务端
cd backend
python app.py

# 测试跨域请求
curl -H "Origin: https://your-domain.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:8000/api/users/login
```

---

## 📊 安全改进对比

| 安全项 | 改进前 | 改进后 | 提升 |
|--------|--------|--------|------|
| 配置加密 | XOR | AES-256-GCM | ⬆️ 高 |
| 密钥派生 | 简单哈希 | PBKDF2 (100k) | ⬆️ 高 |
| Token 存储 | localStorage | 内存 + 可选持久化 | ⬆️ 中 |
| CORS 配置 | 通配符 | 可配置 + 安全默认值 | ⬆️ 中 |
| 密钥轮换 | 不支持 | 支持 | ⬆️ 中 |
| 机器绑定 | 2 因素 | 3 因素 | ⬆️ 低 |

---

## 📝 后续建议

### 高优先级
1. **启用 HTTPS**: 生产环境强制使用 HTTPS
2. **HSTS 头**: 已配置，确保生产环境启用
3. **Content Security Policy**: 审查并收紧 CSP 策略

### 中优先级
1. **双因素认证**: 为用户登录添加 2FA 支持
2. **会话管理**: 实现服务端会话存储和失效
3. **审计日志**: 增强安全事件监控

### 低优先级
1. **硬件安全模块**: 考虑使用 TPM 存储密钥
2. **证书固定**: 实现 SSL Pinning

---

## 📞 问题反馈

如遇到任何安全问题或需要进一步的安全加固，请联系开发团队。
