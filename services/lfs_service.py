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
