"""LFS 存储后端测试"""
import os
import uuid
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
    return LocalFSStorage(temp_lfs_path, repo_id=uuid.uuid4())


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
    async def test_storage_path_structure(self, local_storage: LocalFSStorage):
        oid = "sha256:abcdef1234567890"
        await local_storage.upload(oid, b"data")
        # 验证路径结构: base/repo_id/前2位/2-4位/完整oid
        expected_path = local_storage.base_path / "ab" / "cd" / "abcdef1234567890"
        assert os.path.exists(expected_path)


class TestStorageInterface:
    def test_implements_interface(self, local_storage: LocalFSStorage):
        assert isinstance(local_storage, LFSStorageBackend)


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
    async def test_upload_and_download(self, s3_storage):
        oid = "sha256:s3_test_object"
        data = b"S3 storage test"
        await s3_storage.upload(oid, data)
        result = await s3_storage.download(oid)
        assert result == data

    @pytest.mark.asyncio
    async def test_exists(self, s3_storage):
        oid = "sha256:s3_exists_test"
        assert await s3_storage.exists(oid) is False
        await s3_storage.upload(oid, b"data")
        assert await s3_storage.exists(oid) is True

    @pytest.mark.asyncio
    async def test_delete(self, s3_storage):
        oid = "sha256:s3_delete_test"
        await s3_storage.upload(oid, b"data")
        await s3_storage.delete(oid)
        assert await s3_storage.exists(oid) is False