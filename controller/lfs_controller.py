"""LFS 控制器层"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.lfs_service import LFSService
from services.lfs_storage import LocalFSStorage
from core.config import get_config


def get_lfs_service(repo_id: int) -> LFSService:
    """获取 LFS 服务实例（按 repo_id 隔离）"""
    config = get_config()
    if config.lfs.storage_backend == "local":
        storage = LocalFSStorage(config.lfs.local_path, repo_id)
    else:
        raise HTTPException(status_code=501, detail="S3 storage not yet configured")
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
    try:
        body = await request.json()
        lfs_service = get_lfs_service(repo_id)
        return await lfs_service.batch(
            body.get("operation", "download"),
            body.get("objects", []),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{repo_id}/lfs/objects/{oid}", status_code=201)
async def upload_object(
    repo_id: int,
    oid: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """上传 LFS 对象"""
    try:
        data = await request.body()
        lfs_service = get_lfs_service(repo_id)
        return await lfs_service.upload(oid, data)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/lfs/objects/{oid}")
async def download_object(
    repo_id: int,
    oid: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """下载 LFS 对象"""
    try:
        lfs_service = get_lfs_service(repo_id)
        data = await lfs_service.download(oid)
        return Response(content=data, media_type="application/octet-stream")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{repo_id}/lfs/objects/{oid}", status_code=204)
async def delete_object(
    repo_id: int,
    oid: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除 LFS 对象"""
    try:
        lfs_service = get_lfs_service(repo_id)
        await lfs_service.delete(oid)
        return None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
