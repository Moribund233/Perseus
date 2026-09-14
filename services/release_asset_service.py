"""
Release 附件二进制存储服务

处理 Release 附件文件的上传存储与下载定位：
- 文件保存到本地 uploads 目录（与聊天附件同一存储模式）
- 文件名消毒 + 随机 token 前缀，防止路径穿越与猜测
- 元数据（name/file_path/file_size/content_type）仍由 release_service 注册
"""
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from core.exception import ValidationException

RELEASE_ASSET_UPLOAD_DIR = Path("./data/uploads/release-assets").resolve()
RELEASE_ASSET_MAX_SIZE = 50 * 1024 * 1024  # 50MB（构建产物场景）

# 允许的文件名字符（其余替换为下划线）
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
# 下载/删除时校验存储名格式，防止路径穿越
_STORED_NAME_RE = re.compile(r"^[A-Za-z0-9]{12}_[A-Za-z0-9._-]{1,120}$")


def _sanitize_filename(filename: str) -> str:
    """消毒原始文件名，仅保留安全字符"""
    name = Path(filename or "file").name
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._")
    return name[:120] or "file"


async def read_upload(file: UploadFile) -> tuple[bytes, str, str]:
    """
    读取并校验上传的附件文件

    Returns:
        tuple: (文件字节, 消毒后文件名, MIME 类型)

    Raises:
        ValidationException: 文件为空或超过大小限制
    """
    file_data = await file.read()
    if not file_data:
        raise ValidationException(detail="附件内容为空", error_code="attachment_content_empty")
    if len(file_data) > RELEASE_ASSET_MAX_SIZE:
        raise ValidationException(detail="附件大小不能超过 50MB", error_code="asset_too_large")
    return file_data, _sanitize_filename(file.filename or "file"), file.content_type or "application/octet-stream"


def save_asset_file(release_id: uuid.UUID, stored_name: str, file_data: bytes) -> str:
    """
    写入附件字节并返回相对存储路径（写入 Release.file_path 字段）

    相对路径基于应用工作目录，与 delete_release_asset 的 os.remove 兼容。
    """
    asset_dir = RELEASE_ASSET_UPLOAD_DIR / str(release_id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    disk_path = asset_dir / stored_name
    disk_path.write_bytes(file_data)
    return str(disk_path.relative_to(Path.cwd())) if disk_path.is_relative_to(Path.cwd()) else str(disk_path)


def resolve_asset_path(release_id: uuid.UUID, file_path: str) -> Path:
    """
    定位附件磁盘文件（校验存储名格式 + 目录归属，防路径穿越）

    Raises:
        NotFoundException: 路径非法或文件不存在
    """
    from core.exception import NotFoundException

    stored_name = Path(file_path or "").name
    if not _STORED_NAME_RE.match(stored_name):
        raise NotFoundException(detail="Asset not found", error_code="asset_not_found")
    expected_dir = (RELEASE_ASSET_UPLOAD_DIR / str(release_id)).resolve()
    disk_path = (expected_dir / stored_name).resolve()
    if not str(disk_path).startswith(str(expected_dir)):
        raise NotFoundException(detail="Asset not found", error_code="asset_not_found")
    if not disk_path.is_file():
        raise NotFoundException(detail="Asset not found", error_code="asset_not_found")
    return disk_path


def guess_content_type(stored_name: str) -> str:
    """根据扩展名推断 content_type（回退 octet-stream）"""
    import mimetypes

    content_type, _ = mimetypes.guess_type(stored_name)
    return content_type or "application/octet-stream"
