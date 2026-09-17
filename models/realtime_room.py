from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel


class RealtimeRoom(BaseModel):
    __tablename__ = "realtime_rooms"

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=True, unique=True, index=True)
    name = mapped_column(String(100), nullable=False)
    topic = mapped_column(String(500), nullable=True)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    room_type = mapped_column(String(20), default="repository", nullable=False)

    repository = relationship("Repository", backref="realtime_room")

    def __repr__(self):
        return f"<RealtimeRoom(id={self.id}, repo_id={self.repository_id}, name='{self.name}', type={self.room_type})>"


class RoomMember(BaseModel):
    __tablename__ = "room_members"

    room_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("realtime_rooms.id"), nullable=False, index=True)
    user_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = mapped_column(String(20), nullable=False, default="member")
    joined_at = mapped_column(DateTime(timezone=True), nullable=False)
    last_read_at = mapped_column(DateTime(timezone=True), nullable=True)
    is_muted = mapped_column(Boolean, default=False, nullable=False)

    room = relationship("RealtimeRoom", backref="members")
    user = relationship("User", backref="room_memberships")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_member"),
    )

    def __repr__(self):
        return f"<RoomMember(room_id={self.room_id}, user_id={self.user_id}, role='{self.role}')>"


class DirectMessage(BaseModel):
    """
    私聊会话模型（F-203 DM 私聊）

    一个 DM 会话对应一个 room_type="dm" 的 RealtimeRoom。
    user_a_id / user_b_id 以规范化顺序存储（较小的 UUID 在前），
    保证同一对用户无论由谁发起都命中同一会话。
    """
    __tablename__ = "direct_messages"

    room_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("realtime_rooms.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_a_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user_b_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)

    room = relationship("RealtimeRoom", backref="dm_pair")
    user_a = relationship("User", foreign_keys=[user_a_id], backref="dm_conversations_as_a")
    user_b = relationship("User", foreign_keys=[user_b_id], backref="dm_conversations_as_b")

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_dm_pair"),
    )

    def __repr__(self):
        return f"<DirectMessage(room_id={self.room_id})>"
