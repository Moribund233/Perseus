from sqlalchemy import Column, DateTime
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.sql import func
from models import Base
from models.uuid7 import generate_uuid7


class TimestampMixin(Base):
    __abstract__ = True

    id = Column(
        SAUuid(as_uuid=True),
        primary_key=True,
        index=True,
        default=generate_uuid7,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# 保留别名以保持向后兼容（如果其他模块使用了 BaseModel）
BaseModel = TimestampMixin
