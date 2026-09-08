from sqlalchemy import DateTime
from sqlalchemy.orm import mapped_column
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.sql import func
from models import Base
from models.uuid7 import generate_uuid7


class TimestampMixin(Base):
    __abstract__ = True

    id = mapped_column(
        SAUuid(as_uuid=True),
        primary_key=True,
        index=True,
        default=generate_uuid7,
    )

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# 保留别名以保持向后兼容（如果其他模块使用了 BaseModel）
BaseModel = TimestampMixin
