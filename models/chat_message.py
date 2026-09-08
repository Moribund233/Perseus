from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Index, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy import JSON

from models.base import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    room_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("realtime_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message_type = mapped_column(String(20), default="text", nullable=False)
    content = mapped_column(Text, nullable=False)
    reply_to_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True)
    edited_at = mapped_column(DateTime, nullable=True)
    metadata_ = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_chat_messages_room_created", "room_id", "created_at"),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, room_id={self.room_id}, sender_id={self.sender_id}, type={self.message_type})>"

    room = relationship("RealtimeRoom", backref="messages")
    sender = relationship("User", backref="chat_messages")
    reply_to = relationship("ChatMessage", remote_side="ChatMessage.id", backref="replies")
