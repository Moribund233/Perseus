import pytest


class TestUserOAuthAccountModel:
    """UserOAuthAccount 模型应正确映射数据库"""

    def test_model_has_required_fields(self):
        from models.user_oauth import UserOAuthAccount

        assert hasattr(UserOAuthAccount, "user_id")
        assert hasattr(UserOAuthAccount, "provider")
        assert hasattr(UserOAuthAccount, "provider_user_id")
        assert hasattr(UserOAuthAccount, "access_token")

    def test_unique_constraint_on_provider_and_provider_user_id(self):
        from models.user_oauth import UserOAuthAccount

        uk = [c for c in UserOAuthAccount.__table_args__ if hasattr(c, "columns") and hasattr(c, "name")]
        names = {c.name for c in uk}
        assert "uq_user_oauth_provider" in names
