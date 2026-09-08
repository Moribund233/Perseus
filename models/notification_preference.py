from sqlalchemy import Integer, Boolean, ForeignKey, Uuid as SAUuid
from sqlalchemy.orm import mapped_column
from models.base import BaseModel


class NotificationPreference(BaseModel):
    __tablename__ = "notification_preferences"

    user_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Email preferences
    email_on_mention = mapped_column(Boolean, default=True, nullable=False)
    email_on_pr_review = mapped_column(Boolean, default=True, nullable=False)
    email_on_issue_comment = mapped_column(Boolean, default=True, nullable=False)
    email_on_pr_merge = mapped_column(Boolean, default=True, nullable=False)
    email_on_release = mapped_column(Boolean, default=True, nullable=False)

    # In-app preferences
    in_app_on_mention = mapped_column(Boolean, default=True, nullable=False)
    in_app_on_pr_review = mapped_column(Boolean, default=True, nullable=False)
    in_app_on_issue_comment = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id})>"
