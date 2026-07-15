import uuid
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

    def test_verify_token_returns_oauth_provider(self):
        from services.token_service import create_token_pair, verify_token
        from models.user import User

        user_id = uuid.uuid4()
        user = User(
            id=user_id, username="oauth_user2",
            email="oauth2@test.com", password="x",
            is_active=True, is_admin=False,
        )

        tokens = create_token_pair(user, extra_claims={"oauth_provider": "gitlab"})
        token_data = verify_token(tokens["access_token"])

        assert token_data is not None
        assert token_data.oauth_provider == "gitlab"
        assert token_data.user_id == user_id
        assert token_data.username == "oauth_user2"

    def test_verify_token_returns_none_for_non_oauth_token(self):
        from services.token_service import create_token_pair, verify_token
        from models.user import User

        user_id = uuid.uuid4()
        user = User(
            id=user_id, username="normal_user",
            email="normal@test.com", password="x",
            is_active=True, is_admin=False,
        )

        tokens = create_token_pair(user)
        token_data = verify_token(tokens["access_token"])

        assert token_data is not None
        assert token_data.oauth_provider is None
