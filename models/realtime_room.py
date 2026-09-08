from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel


class RealtimeRoom(BaseModel):
    __tablename__ = "realtime_rooms"

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False, unique=True, index=True)
    name = mapped_column(String(100), nullable=False)
    topic = mapped_column(String(500), nullable=True)
    is_active = mapped_column(Boolean, default=True, nullable=False)

    repository = relationship("Repository", backref="realtime_room")

    def __repr__(self):
        return f"<RealtimeRoom(id={self.id}, repo_id={self.repository_id}, name='{self.name}')>"


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
