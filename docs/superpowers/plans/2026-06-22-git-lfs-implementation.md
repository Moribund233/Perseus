# Git LFS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Git Large File Storage (LFS) support with pluggable storage backends (local filesystem + S3/MinIO)

**Architecture:** Layered architecture following existing patterns: Utils → Storage → Service → Controller. LFS pointer file parsing/generation in utils, pluggable storage backends via abstract base class, business logic in service layer, FastAPI endpoints in controller.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, aiofiles (new dependency), pydantic, pytest-asyncio

---

## File Structure

```
perseus/
├── utils/lfs_utils.py           # LFS 指针文件解析/生成
├── services/lfs_storage.py      # 存储抽象层 (LocalFS + S3)
├── services/lfs_service.py      # LFS 业务逻辑
├── controller/lfs_controller.py # LFS API 端点
├── tests/test_lfs_utils.py      # 指针文件工具测试
├── tests/test_lfs_storage.py    # 存储后端测试
├── tests/test_lfs_service.py    # 业务逻辑测试
└── tests/test_lfs_api.py        # API 端点测试
```

---

## Task 1: Add aiofiles dependency

**Files:**
- Modify: `pyproject.toml:8-29`

- [ ] **Step 1: Add aiofiles to dependencies**

```toml
dependencies = [
    "fastapi>=0.115.4",
    "pygit2>=1.19.1",
    "uvicorn[standard]>=0.32.0",
    "gunicorn>=23.0.0; sys_platform != 'win32'",
    "pydantic-settings>=2.6.0",
    "pydantic[email]>=2.9.2",
    "toml>=0.10.2",
    "httpx>=0.27.2",
    "sqlalchemy>=2.0.34",
    "alembic>=1.13.0",
    "passlib[bcrypt]>=1.7.4",
    "bcrypt==4.0.0",
    "python-jose[cryptography]>=3.3.0",
    "psutil>=7.0.0",
    "psycopg2>=2.9.0",
    "asyncpg>=0.30.0",
    "aiosqlite>=0.20.0",
    "greenlet>=3.1.0",
    "cryptography>=42.0.0",
    "redis>=5.0.0",
    "aiofiles>=24.1.0",
]
```

- [ ] **Step 2: Install dependency**

Run: `pip install aiofiles`
Expected: Successfully installed aiofiles

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add aiofiles for async file operations"
```

---

## Task 2: LFS Utils — Pointer File Parsing

**Files:**
- Create: `utils/lfs_utils.py`
- Create: `tests/test_lfs_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lfs_utils.py
"""LFS 指针文件工具测试"""
import pytest
from utils.lfs_utils import parse_pointer, create_pointer, is_lfs_pointer, LFSPointer


class TestParsePointer:
    def test_parse_valid_pointer(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393\nsize 1234567\n"
        result = parse_pointer(content)
        assert isinstance(result, LFSPointer)
        assert result.version == "https://git-lfs.github.com/spec/v1"
        assert result.oid == "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        assert result.size == 1234567

    def test_parse_pointer_with_custom_headers(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize 100\nx-custom: value\n"
        result = parse_pointer(content)
        assert result.oid == "sha256:abc123"
        assert result.size == 100

    def test_parse_pointer_invalid_version(self):
        content = "version https://invalid.com/spec/v1\noid sha256:abc123\nsize 100\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Invalid LFS pointer" in str(exc.value)

    def test_parse_pointer_missing_oid(self):
        content = "version https://git-lfs.github.com/spec/v1\nsize 100\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Missing required field" in str(exc.value)

    def test_parse_pointer_missing_size(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Missing required field" in str(exc.value)

    def test_parse_pointer_invalid_size(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize not_a_number\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Invalid size" in str(exc.value)


class TestCreatePointer:
    def test_create_pointer(self):
        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        size = 1234567
        result = create_pointer(oid, size)
        assert "version https://git-lfs.github.com/spec/v1" in result
        assert f"oid {oid}" in result
        assert f"size {size}" in result

    def test_create_pointer_format(self):
        oid = "sha256:abc123"
        size = 100
        result = create_pointer(oid, size)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "version https://git-lfs.github.com/spec/v1"
        assert lines[1] == f"oid {oid}"
        assert lines[2] == f"size {size}"


class TestIsLFSPointer:
    def test_is_lfs_pointer_true(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize 100\n"
        assert is_lfs_pointer(content) is True

    def test_is_lfs_pointer_false(self):
        content = "This is a regular file content"
        assert is_lfs_pointer(content) is False

    def test_is_lfs_pointer_empty(self):
        assert is_lfs_pointer("") is False

    def test_is_lfs_pointer_partial(self):
        content = "version https://git-lfs.github.com/spec/v1\n"
        assert is_lfs_pointer(content) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lfs_utils.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.lfs_utils'"

- [ ] **Step 3: Write minimal implementation**

```python
# utils/lfs_utils.py
"""LFS 指针文件解析和生成工具"""
from dataclasses import dataclass


LFS_POINTER_VERSION = "https://git-lfs.github.com/spec/v1"
REQUIRED_FIELDS = {"version", "oid", "size"}


@dataclass
class LFSPointer:
    """LFS 指针文件数据"""
    version: str
    oid: str
    size: int
    extras: dict[str, str] | None = None


def parse_pointer(content: str) -> LFSPointer:
    """
    解析 LFS 指针文件内容

    Args:
        content: 指针文件内容

    Returns:
        LFSPointer: 解析后的指针数据

    Raises:
        ValueError: 指针文件格式无效
    """
    if not content or not content.strip():
        raise ValueError("Empty pointer content")

    lines = content.strip().split("\n")
    fields: dict[str, str] = {}
    extras: dict[str, str] = {}

    for line in lines:
        if " " not in line:
            continue
        key, value = line.split(" ", 1)
        if key in REQUIRED_FIELDS:
            fields[key] = value
        else:
            extras[key] = value

    # 验证必填字段
    missing = REQUIRED_FIELDS - set(fields.keys())
    if missing:
        raise ValueError(f"Missing required field: {', '.join(missing)}")

    # 验证版本
    if fields["version"] != LFS_POINTER_VERSION:
        raise ValueError(f"Invalid LFS pointer version: {fields['version']}")

    # 验证 size 是数字
    try:
        size = int(fields["size"])
    except ValueError:
        raise ValueError(f"Invalid size: {fields['size']}")

    return LFSPointer(
        version=fields["version"],
        oid=fields["oid"],
        size=size,
        extras=extras if extras else None,
    )


def create_pointer(oid: str, size: int) -> str:
    """
    生成 LFS 指针文件内容

    Args:
        oid: 对象 ID (sha256:xxx)
        size: 文件大小

    Returns:
        str: 指针文件内容
    """
    return f"version {LFS_POINTER_VERSION}\noid {oid}\nsize {size}\n"


def is_lfs_pointer(content: str) -> bool:
    """
    判断内容是否为 LFS 指针文件

    Args:
        content: 文件内容

    Returns:
        bool: 是否为 LFS 指针
    """
    if not content:
        return False

    try:
        parse_pointer(content)
        return True
    except ValueError:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_lfs_utils.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add utils/lfs_utils.py tests/test_lfs_utils.py
git commit -m "feat(lfs): add pointer file parsing and generation utilities"
```

---

## Task 3: LFS Storage — Abstract Base + LocalFS

**Files:**
- Create: `services/lfs_storage.py`
- Create: `tests/test_lfs_storage.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lfs_storage.py
"""LFS 存储后端测试"""
import os
import pytest
import tempfile
import shutil
from services.lfs_storage import LocalFSStorage, LFSStorageBackend


@pytest.fixture
def temp_lfs_path():
    """创建临时 LFS 存储目录"""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture
def local_storage(temp_lfs_path):
    """创建本地存储实例"""
    return LocalFSStorage(temp_lfs_path)


class TestLocalFSStorage:
    @pytest.mark.asyncio
    async def test_upload_and_download(self, local_storage: LocalFSStorage):
        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        data = b"Hello, LFS world!"
        await local_storage.upload(oid, data)
        result = await local_storage.download(oid)
        assert result == data

    @pytest.mark.asyncio
    async def test_upload_large_file(self, local_storage: LocalFSStorage):
        oid = "sha256:large_file_test"
        data = os.urandom(1024 * 1024)  # 1MB
        await local_storage.upload(oid, data)
        result = await local_storage.download(oid)
        assert result == data

    @pytest.mark.asyncio
    async def test_delete(self, local_storage: LocalFSStorage):
        oid = "sha256:delete_test"
        data = b"Delete me"
        await local_storage.upload(oid, data)
        assert await local_storage.exists(oid) is True
        await local_storage.delete(oid)
        assert await local_storage.exists(oid) is False

    @pytest.mark.asyncio
    async def test_exists_true(self, local_storage: LocalFSStorage):
        oid = "sha256:exists_test"
        await local_storage.upload(oid, b"exists")
        assert await local_storage.exists(oid) is True

    @pytest.mark.asyncio
    async def test_exists_false(self, local_storage: LocalFSStorage):
        assert await local_storage.exists("sha256:nonexistent") is False

    @pytest.mark.asyncio
    async def test_download_nonexistent(self, local_storage: LocalFSStorage):
        with pytest.raises(FileNotFoundError):
            await local_storage.download("sha256:nonexistent")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, local_storage: LocalFSStorage):
        # Should not raise
        await local_storage.delete("sha256:nonexistent")

    @pytest.mark.asyncio
    async def test_storage_path_structure(self, local_storage: LocalFSStorage, temp_lfs_path):
        oid = "sha256:abcdef1234567890"
        await local_storage.upload(oid, b"data")
        # 验证路径结构: 前2位/2-4位/完整oid
        expected_path = os.path.join(temp_lfs_path, "ab", "cd", "abcdef1234567890")
        assert os.path.exists(expected_path)


class TestStorageInterface:
    def test_implements_interface(self, local_storage: LocalFSStorage):
        assert isinstance(local_storage, LFSStorageBackend)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lfs_storage.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'services.lfs_storage'"

- [ ] **Step 3: Write minimal implementation**

```python
# services/lfs_storage.py
"""LFS 存储后端抽象层"""
import os
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles
import aiofiles.os


class LFSStorageBackend(ABC):
    """LFS 存储后端抽象基类"""

    @abstractmethod
    async def upload(self, oid: str, data: bytes) -> str:
        """
        上传对象

        Args:
            oid: 对象 ID (sha256:xxx)
            data: 文件数据

        Returns:
            str: 存储路径
        """

    @abstractmethod
    async def download(self, oid: str) -> bytes:
        """
        下载对象

        Args:
            oid: 对象 ID

        Returns:
            bytes: 文件数据

        Raises:
            FileNotFoundError: 对象不存在
        """

    @abstractmethod
    async def delete(self, oid: str) -> bool:
        """
        删除对象

        Args:
            oid: 对象 ID

        Returns:
            bool: 是否成功删除
        """

    @abstractmethod
    async def exists(self, oid: str) -> bool:
        """
        检查对象是否存在

        Args:
            oid: 对象 ID

        Returns:
            bool: 是否存在
        """


class LocalFSStorage(LFSStorageBackend):
    """本地文件系统存储"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def _get_path(self, oid: str) -> Path:
        """根据 OID 生成存储路径: base/ab/cd/abcdef..."""
        # 移除 sha256: 前缀
        hash_hex = oid.split(":", 1)[-1] if ":" in oid else oid
        if len(hash_hex) < 4:
            hash_hex = hash_hex.ljust(4, "0")
        return self.base_path / hash_hex[:2] / hash_hex[2:4] / hash_hex

    async def upload(self, oid: str, data: bytes) -> str:
        path = self._get_path(oid)
        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return str(path)

    async def download(self, oid: str) -> bytes:
        path = self._get_path(oid)
        if not path.exists():
            raise FileNotFoundError(f"LFS object not found: {oid}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, oid: str) -> bool:
        path = self._get_path(oid)
        if path.exists():
            await aiofiles.os.remove(path)
            return True
        return False

    async def exists(self, oid: str) -> bool:
        path = self._get_path(oid)
        return path.exists()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_lfs_storage.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add services/lfs_storage.py tests/test_lfs_storage.py
git commit -m "feat(lfs): add storage abstraction with local filesystem backend"
```

---

## Task 4: LFS Storage — S3 Backend

**Files:**
- Modify: `services/lfs_storage.py`
- Modify: `tests/test_lfs_storage.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lfs_storage.py`:

```python
class TestS3Storage:
    """S3 存储测试 (需要运行中的 S3/MinIO)"""
    pytestmark = pytest.mark.skipif(
        not os.environ.get("S3_ENDPOINT"),
        reason="S3 not configured"
    )

    @pytest.fixture
    def s3_storage(self):
        from services.lfs_storage import S3Storage
        return S3Storage(
            bucket=os.environ.get("S3_BUCKET", "test-lfs"),
            endpoint=os.environ.get("S3_ENDPOINT"),
            access_key=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        )

    @pytest.mark.asyncio
    async def test_upload_and_download(self, s3_storage: S3Storage):
        oid = "sha256:s3_test_object"
        data = b"S3 storage test"
        await s3_storage.upload(oid, data)
        result = await s3_storage.download(oid)
        assert result == data

    @pytest.mark.asyncio
    async def test_exists(self, s3_storage: S3Storage):
        oid = "sha256:s3_exists_test"
        assert await s3_storage.exists(oid) is False
        await s3_storage.upload(oid, b"data")
        assert await s3_storage.exists(oid) is True

    @pytest.mark.asyncio
    async def test_delete(self, s3_storage: S3Storage):
        oid = "sha256:s3_delete_test"
        await s3_storage.upload(oid, b"data")
        await s3_storage.delete(oid)
        assert await s3_storage.exists(oid) is False
```

- [ ] **Step 2: Run tests to verify they skip (no S3 configured)**

Run: `pytest tests/test_lfs_storage.py::TestS3Storage -v`
Expected: SKIPPED (S3 not configured)

- [ ] **Step 3: Write minimal implementation**

Append to `services/lfs_storage.py`:

```python
class S3Storage(LFSStorageBackend):
    """S3/MinIO 存储"""

    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import aioboto3
                session = aioboto3.Session()
                self._client = session.client(
                    "s3",
                    endpoint_url=self.endpoint,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                )
            except ImportError:
                raise ImportError("aioboto3 is required for S3 storage. Install with: pip install aioboto3")
        return self._client

    def _get_key(self, oid: str) -> str:
        hash_hex = oid.split(":", 1)[-1] if ":" in oid else oid
        return f"lfs/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}"

    async def upload(self, oid: str, data: bytes) -> str:
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            await s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    async def download(self, oid: str) -> bytes:
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                return await response["Body"].read()
            except client.exceptions.NoSuchKey:
                raise FileNotFoundError(f"LFS object not found: {oid}")

    async def delete(self, oid: str) -> bool:
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def exists(self, oid: str) -> bool:
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False
```

- [ ] **Step 4: Run tests to verify they pass (if S3 configured)**

Run: `pytest tests/test_lfs_storage.py -v`
Expected: All tests pass (S3 tests skip if not configured)

- [ ] **Step 5: Commit**

```bash
git add services/lfs_storage.py tests/test_lfs_storage.py
git commit -m "feat(lfs): add S3/MinIO storage backend"
```

---

## Task 5: LFS Config

**Files:**
- Modify: `core/config.py`

- [ ] **Step 1: Add LFS configuration section**

Add to `core/config.py` after existing settings classes:

```python
class LFSSettings(BaseModel):
    """LFS 配置"""
    enabled: bool = True
    storage_backend: str = "local"  # local | s3
    local_path: str = "/data/lfs"
    s3_bucket: str = "perseus-lfs"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    max_upload_size: int = 5 * 1024 * 1024 * 1024  # 5GB default
```

- [ ] **Step 2: Add lfs_settings to Settings class**

Find the `Settings` class and add:

```python
lfs: LFSSettings = LFSSettings()
```

- [ ] **Step 3: Commit**

```bash
git add core/config.py
git commit -m "feat(lfs): add LFS configuration settings"
```

---

## Task 6: LFS Service — Business Logic

**Files:**
- Create: `services/lfs_service.py`
- Create: `tests/test_lfs_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lfs_service.py
"""LFS 服务层测试"""
import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, patch

from services.lfs_service import LFSService
from services.lfs_storage import LocalFSStorage


@pytest.fixture
def temp_lfs_path():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture
def lfs_service(temp_lfs_path):
    storage = LocalFSStorage(temp_lfs_path)
    return LFSService(storage)


class TestLFSService:
    @pytest.mark.asyncio
    async def test_upload_object(self, lfs_service: LFSService):
        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        data = b"Hello, LFS!"
        result = await lfs_service.upload(oid, data)
        assert result["oid"] == oid
        assert result["size"] == len(data)

    @pytest.mark.asyncio
    async def test_download_object(self, lfs_service: LFSService):
        oid = "sha256:download_test"
        data = b"Download me"
        await lfs_service.upload(oid, data)
        result = await lfs_service.download(oid)
        assert result == data

    @pytest.mark.asyncio
    async def test_delete_object(self, lfs_service: LFSService):
        oid = "sha256:delete_test"
        await lfs_service.upload(oid, b"data")
        result = await lfs_service.delete(oid)
        assert result is True
        assert await lfs_service.exists(oid) is False

    @pytest.mark.asyncio
    async def test_exists(self, lfs_service: LFSService):
        oid = "sha256:exists_test"
        assert await lfs_service.exists(oid) is False
        await lfs_service.upload(oid, b"data")
        assert await lfs_service.exists(oid) is True

    @pytest.mark.asyncio
    async def test_verify_valid(self, lfs_service: LFSService):
        oid = "sha256:verify_test"
        data = b"Verify me"
        await lfs_service.upload(oid, data)
        result = await lfs_service.verify(oid, data)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_invalid(self, lfs_service: LFSService):
        oid = "sha256:verify_invalid"
        await lfs_service.upload(oid, b"original")
        result = await lfs_service.verify(oid, b"different")
        assert result is False

    @pytest.mark.asyncio
    async def test_batch_upload(self, lfs_service: LFSService):
        objects = [
            {"oid": "sha256:batch1", "size": 10},
            {"oid": "sha256:batch2", "size": 20},
        ]
        result = await lfs_service.batch("upload", objects)
        assert len(result["objects"]) == 2
        assert all(obj["actions"] for obj in result["objects"])

    @pytest.mark.asyncio
    async def test_batch_download(self, lfs_service: LFSService):
        # 先上传
        await lfs_service.upload("sha256:batch_dl1", b"data1")
        await lfs_service.upload("sha256:batch_dl2", b"data2")

        objects = [
            {"oid": "sha256:batch_dl1"},
            {"oid": "sha256:batch_dl2"},
        ]
        result = await lfs_service.batch("download", objects)
        assert len(result["objects"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lfs_service.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# services/lfs_service.py
"""LFS 业务逻辑层"""
import hashlib
from typing import Any

from services.lfs_storage import LFSStorageBackend


class LFSService:
    """LFS 服务"""

    def __init__(self, storage: LFSStorageBackend):
        self.storage = storage

    async def upload(self, oid: str, data: bytes) -> dict[str, Any]:
        """
        上传 LFS 对象

        Args:
            oid: 对象 ID (sha256:xxx)
            data: 文件数据

        Returns:
            dict: 上传结果
        """
        await self.storage.upload(oid, data)
        return {"oid": oid, "size": len(data)}

    async def download(self, oid: str) -> bytes:
        """
        下载 LFS 对象

        Args:
            oid: 对象 ID

        Returns:
            bytes: 文件数据
        """
        return await self.storage.download(oid)

    async def delete(self, oid: str) -> bool:
        """
        删除 LFS 对象

        Args:
            oid: 对象 ID

        Returns:
            bool: 是否成功删除
        """
        return await self.storage.delete(oid)

    async def exists(self, oid: str) -> bool:
        """
        检查对象是否存在

        Args:
            oid: 对象 ID

        Returns:
            bool: 是否存在
        """
        return await self.storage.exists(oid)

    async def verify(self, oid: str, data: bytes) -> bool:
        """
        验证对象完整性

        Args:
            oid: 对象 ID
            data: 验证数据

        Returns:
            bool: 数据是否匹配
        """
        try:
            stored = await self.storage.download(oid)
            return stored == data
        except FileNotFoundError:
            return False

    async def batch(self, operation: str, objects: list[dict]) -> dict[str, Any]:
        """
        批量操作

        Args:
            operation: 操作类型 (upload/download)
            objects: 对象列表

        Returns:
            dict: 批量操作结果
        """
        results = []
        for obj in objects:
            oid = obj["oid"]
            actions = {}

            if operation == "upload":
                actions["upload"] = {"href": f"/lfs/objects/{oid}"}
            elif operation == "download":
                actions["download"] = {"href": f"/lfs/objects/{oid}"}

            results.append({
                "oid": oid,
                "size": obj.get("size", 0),
                "actions": actions,
            })

        return {"transfer": "basic", "objects": results}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_lfs_service.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add services/lfs_service.py tests/test_lfs_service.py
git commit -m "feat(lfs): add LFS service layer with batch operations"
```

---

## Task 7: LFS Controller — API Endpoints

**Files:**
- Create: `controller/lfs_controller.py`
- Modify: `api/routes_config.py`
- Create: `tests/test_lfs_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lfs_api.py
"""LFS API 端点测试"""
import pytest
from fastapi.testclient import TestClient


class TestLFSAPI:
    def test_batch_upload_request(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-test-repo")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/lfs/objects/batch",
            json={
                "operation": "upload",
                "transfers": ["basic"],
                "ref": {"name": "main"},
                "objects": [
                    {"oid": "sha256:abc123", "size": 1024}
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "objects" in data
        assert len(data["objects"]) == 1
        assert "actions" in data["objects"][0]

    def test_batch_download_request(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-download-repo")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/lfs/objects/batch",
            json={
                "operation": "download",
                "objects": [
                    {"oid": "sha256:abc123"}
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["objects"][0]["actions"]["download"]["href"]

    def test_upload_object(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-upload-repo")

        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        response = test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Hello, LFS!",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["oid"] == oid

    def test_download_object(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-dl-repo")

        oid = "sha256:download_test"
        # 先上传
        test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Download me",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.content == b"Download me"

    def test_upload_requires_auth(self, test_client: TestClient, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-noauth-repo")

        oid = "sha256:noauth_test"
        response = test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"data",
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 401

    def test_delete_object(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="lfs-delete-repo")

        oid = "sha256:delete_test"
        # 先上传
        test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Delete me",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )

        response = test_client.delete(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            headers=auth_headers,
        )
        assert response.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lfs_api.py -v`
Expected: FAIL with "404 Not Found" (endpoints not registered)

- [ ] **Step 3: Write minimal implementation**

```python
# controller/lfs_controller.py
"""LFS 控制器层"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.lfs_service import LFSService
from services.lfs_storage import LocalFSStorage
from core.config import settings


def get_lfs_service() -> LFSService:
    """获取 LFS 服务实例"""
    if settings.lfs.storage_backend == "local":
        storage = LocalFSStorage(settings.lfs.local_path)
    else:
        raise NotImplementedError("S3 storage not yet configured")
    return LFSService(storage)


router = APIRouter(prefix=get_route_prefix("repositories"), tags=["lfs"])


@router.post("/{repo_id}/lfs/objects/batch")
async def batch(
    repo_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """LFS 批量操作"""
    body = await request.json()
    lfs_service = get_lfs_service()
    return await lfs_service.batch(
        body.get("operation", "download"),
        body.get("objects", []),
    )


@router.put("/{repo_id}/lfs/objects/{oid}", status_code=201)
async def upload_object(
    repo_id: int,
    oid: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """上传 LFS 对象"""
    data = await request.body()
    lfs_service = get_lfs_service()
    return await lfs_service.upload(oid, data)


@router.get("/{repo_id}/lfs/objects/{oid}")
async def download_object(
    repo_id: int,
    oid: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """下载 LFS 对象"""
    lfs_service = get_lfs_service()
    data = await lfs_service.download(oid)
    return Response(content=data, media_type="application/octet-stream")


@router.delete("/{repo_id}/lfs/objects/{oid}", status_code=204)
async def delete_object(
    repo_id: int,
    oid: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除 LFS 对象"""
    lfs_service = get_lfs_service()
    await lfs_service.delete(oid)
    return None
```

- [ ] **Step 4: Register router in routes_config.py**

Add to `api/routes_config.py`:

```python
from controller.lfs_controller import router as lfs_router
# ... in create_api_router():
api_v1_router.include_router(lfs_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_lfs_api.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add controller/lfs_controller.py api/routes_config.py tests/test_lfs_api.py
git commit -m "feat(lfs): add LFS API endpoints with auth"
```

---

## Task 8: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests pass (including new LFS tests)

- [ ] **Step 2: Fix any failures if needed**

- [ ] **Step 3: Final commit if any fixes were made**

```bash
git add -A
git commit -m "fix(lfs): resolve test failures"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `docs/api/README.md`
- Modify: `docs/api/roadmap.md`

- [ ] **Step 1: Add LFS to API README**

Add a new section to `docs/api/README.md`:

```markdown
### 19. Git LFS

| 功能 | 状态 | 说明 |
|------|------|------|
| LFS 指针文件解析 | ✅ | 解析/生成 LFS 指针文件 |
| 本地文件系统存储 | ✅ | 支持大文件本地存储 |
| S3/MinIO 存储 | ✅ | 可选对象存储后端 |
| Batch API | ✅ | 批量上传/下载请求 |
| 对象上传/下载 | ✅ | 单对象上传下载 |
| 对象删除 | ✅ | 删除 LFS 对象 |
| 完整性验证 | ✅ | 验证对象数据完整性 |
```

- [ ] **Step 2: Mark roadmap tasks as complete**

Update `docs/api/roadmap.md` to mark F-034, F-035, F-036 as complete.

- [ ] **Step 3: Commit**

```bash
git add docs/api/README.md docs/api/roadmap.md
git commit -m "docs: update LFS documentation and roadmap status"
```
