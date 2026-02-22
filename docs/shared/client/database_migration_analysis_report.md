# 数据库切换与迁移机制分析报告

**生成日期**: 2026-02-22  
**分析范围**: 客户端、Tauri 中间层、服务端全流程  
**分析目的**: 评估数据库切换与迁移机制的清晰度，识别潜在问题

---

## 一、架构概述

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          客户端 (Vue3)                           │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ Home.vue    │───→│ DatabaseStore│───→│ databaseApi.ts   │   │
│  │ 启动检测    │    │ 状态管理     │    │ API 封装         │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Tauri Rust 中间层                           │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ commands.rs │───→│ api_client.rs│───→│ HTTP Client      │   │
│  │ 命令分发    │    │ API 封装     │    │ 请求服务端       │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       服务端 (FastAPI)                           │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ lifespan.py │───→│ app_controller│───→│ utils/migration │   │
│  │ 启动检测    │    │ API 端点     │    │ 迁移执行         │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心数据流

```
环境变量 DATABASE_URL ──┐
                        ├──→ 解析 db_type ──→ 与 current_db_type 对比
配置文件 current_db_type ┘                        ↓
                                        migration_required?
                                        ↙          ↘
                                    是 /            \ 否
                                     ↓              ↓
                            前端显示迁移对话框    正常启动
                                     ↓
                            用户确认后执行迁移
                                     ↓
                            更新 current_db_type
```

---

## 二、机制详解

### 2.1 数据库类型检测机制

**检测时机**: 应用启动时 (`lifespan.py::startup()`)

**检测逻辑**:
1. 从环境变量 `DATABASE_URL` 解析目标数据库类型
2. 从配置文件读取上次记录的数据库类型 `current_db_type`
3. 对比两者，判断是否需要进行迁移

**关键代码位置**:
- `lifespan.py:43-136` - `_check_database_migration()`
- `app_controller.py:447-510` - `get_database_status_endpoint()`

### 2.2 迁移触发机制

**触发条件**:
```python
if actual_type != recorded_type:
    migration_required = True
```

**触发场景**:
| 场景 | 当前类型 | 目标类型 | 处理方式 |
|------|----------|----------|----------|
| 首次启动 | None | 任意 | 记录类型，无需迁移 |
| SQLite → PostgreSQL | sqlite | postgresql | 触发迁移 |
| PostgreSQL → MySQL | postgresql | mysql | 触发迁移 |
| MySQL → SQLite | mysql | sqlite | 触发迁移 |
| 配置未变更 | X | X | 正常启动 |

### 2.3 迁移执行流程

**执行步骤**:
1. **导出数据**: 从源数据库导出所有表数据到 JSON 文件
2. **创建表结构**: 在目标数据库创建表结构
3. **导入数据**: 将 JSON 数据导入目标数据库
4. **更新记录**: 更新 `current_db_type` 为新类型
5. **清理**: 删除临时导出文件

**关键代码位置**:
- `utils/migration.py` - 核心迁移逻辑
- `app_controller.py:512-577` - 迁移 API 端点
- `services/app_service.py` - 迁移服务层

---

## 三、发现的问题

### 3.1 【高优先级】缺少事务回滚机制

**问题描述**:
迁移过程中任一步骤失败，已执行的操作无法自动回滚，可能导致数据不一致。

**影响场景**:
- 导出成功，导入失败 → 源数据已导出但目标未导入
- 部分表导入成功，后续表失败 → 目标库数据不完整
- 导入成功但更新记录失败 → 类型记录与实际不匹配

**风险等级**: 🔴 高

**建议改进**:
```python
# 建议添加事务包装
async def migrate_with_rollback(params):
    backup_id = None
    try:
        # 1. 创建备份点
        backup_id = await create_backup()
        
        # 2. 执行迁移
        result = await execute_migration(params)
        
        # 3. 验证数据完整性
        if not await verify_data_integrity():
            raise MigrationError("数据完整性验证失败")
        
        # 4. 提交（删除备份）
        await delete_backup(backup_id)
        
    except Exception as e:
        # 回滚到备份点
        if backup_id:
            await rollback_to_backup(backup_id)
        raise
```

### 3.2 【高优先级】大表迁移无进度反馈

**问题描述**:
迁移大表时，前端无法获取实时进度，用户体验差，可能误以为程序卡死。

**影响场景**:
- 百万级数据表迁移可能需要数分钟
- 用户无法判断是正常处理还是出错
- 可能误操作关闭应用

**风险等级**: 🔴 高

**建议改进**:
```python
# 使用 WebSocket 推送进度
class MigrationProgressTracker:
    async def update_progress(self, table: str, current: int, total: int):
        progress = {
            "table": table,
            "current": current,
            "total": total,
            "percent": (current / total) * 100
        }
        await websocket_manager.broadcast(progress)
```

### 3.3 【中优先级】目标库数据冲突处理不明确

**问题描述**:
当目标数据库已存在数据时，迁移逻辑未定义冲突处理策略。

**影响场景**:
- 目标库有旧数据 → 可能产生主键冲突
- 部分表存在 → 表结构可能不兼容
- 用户无法选择覆盖或跳过策略

**风险等级**: 🟡 中

**建议改进**:
- 迁移前检查目标库状态
- 提供冲突解决选项：
  - `skip` - 跳过已存在的表
  - `overwrite` - 删除并重新创建
  - `merge` - 尝试合并数据（需处理主键冲突）

### 3.4 【中优先级】类型检测硬编码

**问题描述**:
`_parse_db_type()` 使用字符串前缀匹配，不够健壮。

**当前实现**:
```python
def _parse_db_type(self, url: str) -> str:
    url_lower = url.lower()
    if url_lower.startswith("sqlite"):
        return "sqlite"
    elif url_lower.startswith("postgresql"):
        return "postgresql"
    # ...
```

**潜在问题**:
- 不支持 `postgres://` 简写形式
- 无法处理特殊 URL 格式
- 新增数据库类型需要修改代码

**风险等级**: 🟡 中

**建议改进**:
```python
from sqlalchemy.engine import make_url

def _parse_db_type(self, url: str) -> str:
    try:
        parsed = make_url(url)
        return parsed.get_backend_name()
    except Exception:
        return "unknown"
```

### 3.5 【中优先级】强依赖前端触发迁移

**问题描述**:
如果用户不启动前端界面，服务端检测到迁移需求也无法自动执行。

**影响场景**:
- 服务端独立部署时无法完成迁移
- 自动化部署场景需要人工干预
- 远程服务器管理困难

**风险等级**: 🟡 中

**建议改进**:
- 添加配置项 `AUTO_MIGRATE=true/false`
- 支持命令行迁移模式
- 提供迁移状态查询 API

### 3.6 【低优先级】URL 安全性处理不一致

**问题描述**:
数据库 URL 在多处传递，存在敏感信息泄露风险。

**当前处理**:
- 服务端不存储 URL（安全）
- 前端从加密配置读取（安全）
- 但迁移 API 请求体中明文传输 URL（风险）

**风险等级**: 🟢 低

**建议改进**:
- 使用临时令牌代替明文 URL
- 或确保 HTTPS 传输
- 日志中脱敏处理 URL

### 3.7 【低优先级】缺少迁移历史记录

**问题描述**:
系统未记录迁移历史，无法追溯数据变更。

**风险等级**: 🟢 低

**建议改进**:
- 添加迁移日志表
- 记录每次迁移的时间、源类型、目标类型、数据量
- 支持迁移回滚到指定版本

---

## 四、文件位置汇总

### 4.1 服务端相关文件

| 文件 | 职责 | 关键函数/类 |
|------|------|-------------|
| `lifespan.py` | 启动时迁移检测 | `_check_database_migration()` |
| `controller/app_controller.py` | 迁移 API 端点 | `get_database_status_endpoint()`, `migrate_database_endpoint()` |
| `services/app_service.py` | 迁移服务逻辑 | `migrate_database()` |
| `utils/migration.py` | 核心迁移工具 | `DatabaseMigration` 类 |
| `config.py` | 配置管理 | `DatabaseConfig.current_db_type` |

### 4.2 客户端相关文件

| 文件 | 职责 | 关键函数/组件 |
|------|------|---------------|
| `client/src/views/Home.vue` | 迁移检测触发 | `checkMigrationAfterStart()` |
| `client/src/stores/database.ts` | 状态管理 | `checkMigrationStatus()`, `executeMigration()` |
| `client/src/services/databaseApi.ts` | API 封装 | `getDatabaseStatusFromApi()`, `migrateDatabase()` |
| `client/src/components/database/MigrationProgressModal.vue` | 迁移 UI | 进度展示模态框 |

### 4.3 Tauri 中间层文件

| 文件 | 职责 | 关键函数 |
|------|------|----------|
| `client/src-tauri/src/commands.rs` | 命令分发 | `get_database_status_from_api()`, `migrate_database()` |
| `client/src-tauri/src/api_client.rs` | HTTP 客户端 | `get_database_status()`, `migrate_database()` |

---

## 五、改进优先级建议

### 5.1 第一阶段（关键修复）

1. **添加事务回滚机制**
   - 实现备份/回滚逻辑
   - 添加数据完整性验证
   - 预计工作量: 2-3 天

2. **实现迁移进度反馈**
   - WebSocket 实时推送
   - 前端进度条展示
   - 预计工作量: 1-2 天

### 5.2 第二阶段（体验优化）

3. **冲突处理策略**
   - 目标库预检查
   - 用户选择界面
   - 预计工作量: 1-2 天

4. **类型检测改进**
   - 使用 SQLAlchemy 标准解析
   - 支持更多数据库类型
   - 预计工作量: 0.5 天

### 5.3 第三阶段（功能增强）

5. **服务端自动迁移**
   - 配置项支持
   - 命令行模式
   - 预计工作量: 1 天

6. **迁移历史记录**
   - 迁移日志表设计
   - 历史查询接口
   - 预计工作量: 1 天

---

## 六、总结

### 6.1 优势

1. **架构清晰**: 职责分层明确，服务端/中间层/前端分离合理
2. **安全考虑**: 敏感 URL 不存储在服务端，由前端提供
3. **工具独立**: `utils/migration.py` 可独立使用，支持命令行
4. **状态管理**: 使用 `current_db_type` 记录状态，避免重复迁移

### 6.2 待改进

1. **健壮性**: 缺少回滚机制和冲突处理
2. **用户体验**: 大表迁移无进度反馈
3. **自动化**: 强依赖前端，不支持服务端自主迁移
4. **可维护性**: 类型检测硬编码，扩展性不足

### 6.3 总体评价

数据库切换与迁移机制的**整体设计是合理的**，核心流程清晰，能够满足基本需求。主要问题在于**边界情况处理不足**和**用户体验待优化**。建议按照优先级逐步改进，重点关注事务回滚和进度反馈两个高优先级问题。

---

**报告完成**
