from datetime import datetime, timezone
from jose import jwt


class TestTokenOAuth:
    """JWT 应携带 oauth_provider 信息"""

    def test_create_token_pair_with_extra_claims(self):
        from services.token_service import create_token_pair
        from models.user import User

        user = User(
            id=999, username="oauth_user",
            email="oauth@test.com", password="x",
            is_active=True, is_admin=False,
        )

        tokens = create_token_pair(user, extra_claims={"oauth_provider": "github"})
        decoded = jwt.decode(
            tokens["access_token"], "", options={"verify_signature": False},
        )

        assert decoded["oauth_provider"] == "github"
        assert decoded["sub"] == "999"
        assert decoded["username"] == "oauth_user"
