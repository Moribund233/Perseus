from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship
from models.base import BaseModel


class UserOAuthAccount(BaseModel):
    """OAuth 账号绑定模型 - 存储用户关联的第三方 OAuth 账号"""

    __tablename__ = "user_oauth_accounts"

    user_id = Column(SAUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    """关联的用户 ID"""

    provider = Column(String(50), nullable=False)
    """OAuth provider 名称: github, gitlab"""

    provider_user_id = Column(String(255), nullable=False)
    """第三方平台的用户 ID"""

    provider_username = Column(String(255), nullable=True)
    """第三方平台的用户名"""

    access_token = Column(String(512), nullable=True)
    """OAuth 访问令牌"""

    refresh_token = Column(String(256), nullable=True)
    """OAuth 刷新令牌"""

    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    """令牌过期时间"""

    user = relationship("User", backref="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_oauth_provider"),
    )
