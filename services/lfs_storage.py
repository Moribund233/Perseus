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

    def __init__(self, base_path: str, repo_id: int):
        self.base_path = Path(base_path) / str(repo_id)

    def _get_path(self, oid: str) -> Path:
        """根据 OID 生成存储路径: base/{repo_id}/ab/cd/abcdef..."""
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
        self._session = None

    async def _get_client(self):
        if self._session is None:
            try:
                import aioboto3
                self._session = aioboto3.Session()
            except ImportError:
                raise ImportError("aioboto3 is required for S3 storage. Install with: pip install aioboto3")
        return self._session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

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
        from botocore.exceptions import ClientError
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return False
                raise

    async def exists(self, oid: str) -> bool:
        from botocore.exceptions import ClientError
        client = await self._get_client()
        key = self._get_key(oid)
        async with client as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise