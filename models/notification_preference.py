from sqlalchemy import Column, Integer, Boolean, ForeignKey, Uuid as SAUuid
from models.base import BaseModel


class NotificationPreference(BaseModel):
    __tablename__ = "notification_preferences"

    user_id = Column(SAUuid(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Email preferences
    email_on_mention = Column(Boolean, default=True, nullable=False)
    email_on_pr_review = Column(Boolean, default=True, nullable=False)
    email_on_issue_comment = Column(Boolean, default=True, nullable=False)
    email_on_pr_merge = Column(Boolean, default=True, nullable=False)
    email_on_release = Column(Boolean, default=True, nullable=False)

    # In-app preferences
    in_app_on_mention = Column(Boolean, default=True, nullable=False)
    in_app_on_pr_review = Column(Boolean, default=True, nullable=False)
    in_app_on_issue_comment = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id})>"
