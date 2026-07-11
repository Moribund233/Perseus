# Git LFS 实现设计

> **日期**: 2026-06-22
> **阶段**: Phase 3 — 后端高级功能
> **任务 ID**: F-034 ~ F-036
> **开发方针**: TDD（测试驱动开发）

---

## 概述

为 Perseus 平台实现 Git Large File Storage (LFS) 支持，允许用户存储大文件（二进制、媒体文件等）而不会使 Git 仓库膨胀。

## 设计目标

1. **存储后端可切换**：支持本地文件系统（MVP）和 S3/MinIO（可选）
2. **符合 LFS 规范**：实现 Batch API 基础操作（upload/download）
3. **TDD 驱动**：所有功能先写测试，再实现
4. **与现有架构一致**：遵循 Model → Service → Controller 分层

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Git LFS 模块                          │
├─────────────────────────────────────────────────────────┤
│  Controller          Service           Storage Backend   │
│  ┌──────────┐       ┌──────────┐      ┌──────────────┐ │
│  │LFS API   │──────→│LFSService│─────→│ LocalFS      │ │
│  │(batch)   │       │          │      │ (MVP)        │ │
│  └──────────┘       │          │      └──────────────┘ │
│                     │          │      ┌──────────────┐ │
│                     │          │─────→│ S3/MinIO     │ │
│                     └──────────┘      │ (可选)        │ │
│                           │           └──────────────┘ │
│                     ┌──────────┐                        │
│                     │LFSUtils  │ ← 指针文件解析/生成     │
│                     └──────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
perseus/
├── utils/lfs_utils.py           # LFS 指针文件解析/生成
├── services/lfs_storage.py      # 存储抽象层
├── services/lfs_service.py      # LFS 业务逻辑
├── controller/lfs_controller.py # LFS API 端点
├── models/lfs.py                # LFS 模型（可选）
└── tests/test_lfs_*.py          # TDD 测试
```

## 核心组件

### 1. LFS Utils (`utils/lfs_utils.py`)

负责 LFS 指针文件的解析和生成。

```python
# 指针文件格式
version https://git-lfs.github.com/spec/v1
oid sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393
size 1234567
```

**方法：**
- `parse_pointer(content: str) -> LFSPointer` — 解析指针文件
- `create_pointer(oid: str, size: int) -> str` — 生成指针文件内容
- `is_lfs_pointer(content: str) -> bool` — 判断是否为 LFS 指针

### 2. LFS Storage (`services/lfs_storage.py`)

存储抽象层，支持后端切换。

```python
class LFSStorageBackend(ABC):
    @abstractmethod
    async def upload(self, oid: str, data: bytes) -> str: ...
    @abstractmethod
    async def download(self, oid: str) -> bytes: ...
    @abstractmethod
    async def delete(self, oid: str) -> bool: ...
    @abstractmethod
    async def exists(self, oid: str) -> bool: ...

class LocalFSStorage(LFSStorageBackend):
    """本地文件系统存储"""
    def __init__(self, base_path: str): ...

class S3Storage(LFSStorageBackend):
    """S3/MinIO 存储"""
    def __init__(self, bucket: str, endpoint: str, ...): ...
```

### 3. LFS Service (`services/lfs_service.py`)

业务逻辑层。

**方法：**
- `batch(operation: str, objects: list) -> dict` — 批量操作
- `upload(oid: str, data: bytes) -> dict` — 上传对象
- `download(oid: str) -> bytes` — 下载对象
- `delete(oid: str) -> bool` — 删除对象
- `verify(oid: str, data: bytes) -> bool` — 验证对象完整性

### 4. LFS Controller (`controller/lfs_controller.py`)

API 端点。

```
POST   /api/v1/repositories/{repo_id}/lfs/objects/batch   # 批量操作
POST   /api/v1/repositories/{repo_id}/lfs/objects/{oid}   # 上传
GET    /api/v1/repositories/{repo_id}/lfs/objects/{oid}   # 下载
DELETE /api/v1/repositories/{repo_id}/lfs/objects/{oid}   # 删除
```

## TDD 测试用例

### F-034: LFS 指针文件管理

| 测试 | 场景 |
|------|------|
| `test_parse_lfs_pointer()` | 解析有效指针文件 |
| `test_parse_lfs_pointer_invalid()` | 无效指针文件格式 |
| `test_create_lfs_pointer()` | 生成指针文件内容 |
| `test_is_lfs_pointer()` | 判断文件是否为 LFS 指针 |

### F-035: LFS 存储后端

| 测试 | 场景 |
|------|------|
| `test_local_fs_upload_and_download()` | 本地存储上传下载 |
| `test_local_fs_delete()` | 本地存储删除 |
| `test_local_fs_exists()` | 本地存储存在检查 |
| `test_storage_backend_switch()` | 通过配置切换存储后端 |

### F-036: LFS API 端点

| 测试 | 场景 |
|------|------|
| `test_lfs_batch_upload()` | 批量上传请求 |
| `test_lfs_batch_download()` | 批量下载请求 |
| `test_lfs_upload_object()` | 上传单个对象 |
| `test_lfs_download_object()` | 下载单个对象 |
| `test_lfs_upload_auth()` | 上传需要认证 |
| `test_lfs_download_public()` | 公开仓库下载无需认证 |
| `test_lfs_delete_object()` | 删除对象 |
| `test_lfs_verify_object()` | 验证对象完整性 |

## 配置

```toml
[lfs]
enabled = true
storage_backend = "local"  # local | s3
local_path = "/data/lfs"

[lfs.s3]
bucket = "perseus-lfs"
endpoint = "http://minio:9000"
access_key = ""
secret_key = ""
```

## 依赖

- 新增依赖 `aiofiles` — 异步文件操作（本地存储）
- S3 存储可选依赖 `boto3`
- 需在 `pyproject.toml` 中添加 `aiofiles` 到 dependencies

## 实施顺序

1. **TDD RED**: 编写所有测试用例
2. **TDD GREEN**: 实现 LFS Utils → Storage → Service → Controller
3. **TDD REFACTOR**: 优化代码结构，消除重复
4. **验证**: 运行全部测试确认通过
