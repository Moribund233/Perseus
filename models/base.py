from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from models import Base


class TimestampMixin(Base):
    """
    时间戳混入类

    提供通用的ID、创建时间和更新时间字段。
    所有数据模型应继承此类以获得标准的时间戳字段。

    Example:
        >>> class User(TimestampMixin):
        ...     __tablename__ = "users"
        ...     username = Column(String, nullable=False)
    """
    __abstract__ = True  # 抽象类，不会创建实际的数据库表

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """主键ID，自增整数"""

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """创建时间，默认值为当前时间"""

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    """更新时间，默认值为当前时间，更新时自动设置为当前时间"""


# 保留别名以保持向后兼容（如果其他模块使用了 BaseModel）
BaseModel = TimestampMixin
