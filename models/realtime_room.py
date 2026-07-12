from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel


class RealtimeRoom(BaseModel):
    __tablename__ = "realtime_rooms"

    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    topic = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    repository = relationship("Repository", backref="realtime_room")

    def __repr__(self):
        return f"<RealtimeRoom(id={self.id}, repo_id={self.repository_id}, name='{self.name}')>"


class RoomMember(BaseModel):
    __tablename__ = "room_members"

    room_id = Column(Integer, ForeignKey("realtime_rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime(timezone=True), nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    is_muted = Column(Boolean, default=False, nullable=False)

    room = relationship("RealtimeRoom", backref="members")
    user = relationship("User", backref="room_memberships")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_member"),
    )

    def __repr__(self):
        return f"<RoomMember(room_id={self.room_id}, user_id={self.user_id}, role='{self.role}')>"
