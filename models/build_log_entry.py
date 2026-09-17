"""
构建日志流式条目模型（6.2 P2 绿灯）

为构建日志引入"分步 + 时间戳 + 增量拉取"：

- 每一行日志是 build_log_entries 表内一行，seq 在该 build 内从 1 递增；
- stream 分流（stdout/stderr），logged_at 记录该行写入时刻（timestamptz）；
- external CI runner 通过签名回调 `log_entries` 追加写入，不再整串覆盖。

兼容性：BuildStatus.logs 仍保留为拼好的整串快照（旧 GET /builds/{id}/logs
不回退），本表为增量拉取的权威来源。
"""
from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    CheckConstraint,
    ForeignKey,
    Index,
    Uuid as SAUuid,
)
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.sql import func

from models.base import BaseModel


class BuildLogEntry(BaseModel):
    """Build 内按 seq 递增的单条日志行。"""

    __tablename__ = "build_log_entries"

    build_id = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("build_status.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    """所属构建（build_status 表，与 BuildStatus 模型一致）"""

    seq = mapped_column(Integer, nullable=False, default=1)
    """该 build 内自增序号，从 1 开始"""

    stream = mapped_column(String(20), nullable=False, default="stdout")
    """日志流：stdout / stderr"""

    line = mapped_column(Text, nullable=False)
    """单行日志内容"""

    logged_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    """该行写入时刻（时区感知 timestamptz）"""

    build = relationship("BuildStatus", backref="log_entries")

    __table_args__ = (
        CheckConstraint("seq >= 1", name="ck_build_log_entries_seq_positive"),
        CheckConstraint(
            "stream IN ('stdout', 'stderr')", name="ck_build_log_entries_stream_valid"
        ),
        # 每 build 内 seq 唯一：增量拉取 after_seq 的边界
        Index("uq_build_log_entries_build_seq", "build_id", "seq", unique=True),
    )

    def __repr__(self) -> str:
        return f"<BuildLogEntry(build_id={self.build_id}, seq={self.seq}, stream={self.stream})>"
