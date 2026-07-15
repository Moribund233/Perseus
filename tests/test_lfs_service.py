"""LFS 服务层测试"""
import pytest
import uuid
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
    storage = LocalFSStorage(temp_lfs_path, repo_id=uuid.uuid4())
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
