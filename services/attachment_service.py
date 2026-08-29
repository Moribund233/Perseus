"""
聊天附件服务层

处理聊天文件上传与下载：
- 附件保存到本地 uploads 目录（与头像上传同一存储模式）
- 文件名消毒 + 随机 token 前缀，防止路径穿越与猜测
"""
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from core.exception import ValidationException, NotFoundException

ATTACHMENT_UPLOAD_DIR = Path("./data/uploads/attachments").resolve()
ATTACHMENT_MAX_SIZE = 20 * 1024 * 1024  # 20MB

# 允许的文件名字符（其余替换为下划线）
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
# 下载时校验存储名格式，防止路径穿越
_STORED_NAME_RE = re.compile(r"^[A-Za-z0-9]{12}_[A-Za-z0-9._-]{1,120}$")


def _sanitize_filename(filename: str) -> str:
    """消毒原始文件名，仅保留安全字符"""
    name = Path(filename or "file").name
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._")
    return name[:120] or "file"


async def upload_attachment(room_id: uuid.UUID, file: UploadFile) -> dict:
    """
    保存聊天附件并返回可访问的 URL 信息

    Args:
        room_id: 房间 ID（仅用于生成存储子目录隔离）
        file: 上传的文件

    Returns:
        dict: {name, size, content_type, url}

    Raises:
        ValidationException: 文件为空或超过大小限制
    """
    file_data = await file.read()
    if not file_data:
        raise ValidationException(detail="附件内容为空")
    if len(file_data) > ATTACHMENT_MAX_SIZE:
        raise ValidationException(detail="附件大小不能超过 20MB")

    safe_name = _sanitize_filename(file.filename or "file")
    token = uuid.uuid4().hex[:12]
    stored_name = f"{token}_{safe_name}"

    room_dir = ATTACHMENT_UPLOAD_DIR / str(room_id)
    room_dir.mkdir(parents=True, exist_ok=True)
    file_path = room_dir / stored_name
    file_path.write_bytes(file_data)

    return {
        "name": safe_name,
        "size": len(file_data),
        "content_type": file.content_type or "application/octet-stream",
        "url": f"/api/v1/attachments/{room_id}/{stored_name}",
    }


async def get_attachment_file(
    room_id: uuid.UUID, stored_name: str
) -> tuple[Path, str]:
    """
    定位附件文件并返回 (路径, content_type)

    Raises:
        NotFoundException: 文件名非法或文件不存在
    """
    if not _STORED_NAME_RE.match(stored_name or ""):
        raise NotFoundException(detail="Attachment not found")

    file_path = ATTACHMENT_UPLOAD_DIR / str(room_id) / stored_name
    if not file_path.is_file():
        raise NotFoundException(detail="Attachment not found")

    content_type = _guess_content_type(stored_name)
    return file_path, content_type


def _guess_content_type(stored_name: str) -> str:
    """根据扩展名推断 content_type（回退 octet-stream）"""
    import mimetypes

    content_type, _ = mimetypes.guess_type(stored_name)
    return content_type or "application/octet-stream"
