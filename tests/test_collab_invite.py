"""协作邀请链接测试 (collab_invite_controller + collab_internal_controller 邀请分支)"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from controller.collab_internal_controller import (
    INTERNAL_SECRET_ENV,
    INTERNAL_SECRET_HEADER,
    make_doc_key,
)
from models.repository_member import RepositoryMember
from services.collab_invite_service import create_invite_token, verify_invite_token
from services.token_service import create_access_token
from tests.test_helpers import create_test_repo

SECRET = "test-internal-secret"


def _internal_headers(secret=SECRET):
    return {INTERNAL_SECRET_HEADER: secret}


def _token_for(user):
    return create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
    })


def _auth_headers(user):
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _add_member(db, repo, user, role):
    db.add(RepositoryMember(
        repository_id=repo.id, user_id=user.id, role=role, is_active=True
    ))
    db.commit()


def _other_user(db):
    """独立的仓库 owner (避免 test_user 因 owner 身份恒有权限)"""
    from models.user import User

    user = User(
        username="invite_repoowner",
        email="invite_owner@example.com",
        password="hashed",
        full_name="Invite Repo Owner",
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _expired_invite_token(doc_key: str) -> str:
    from core.config import get_config

    security = get_config().security
    now = datetime.now(timezone.utc)
    payload = {
        "type": "collab_invite",
        "sub": str(uuid.uuid4()),
        "username": "issuer",
        "doc_key": doc_key,
        "scope": "read",
        "jti": uuid.uuid4().hex,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    return jwt.encode(payload, security.secret_key, algorithm=security.algorithm)


@pytest.fixture
def internal_env(monkeypatch):
    monkeypatch.setenv(INTERNAL_SECRET_ENV, SECRET)


# ==================== 签发 (仅成员) ====================


class TestIssueInviteToken:

    def test_issue_invite_token(self, test_client, db, test_user):
        repo = create_test_repo(db, name="invite-issue", owner_id=_other_user(db).id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")

        resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites",
            json={"doc_key": doc_key, "scope": "read"},
            headers=_auth_headers(test_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["token"]
        assert data["scope"] == "read"
        assert data["url"] == f"/collab/{data['token']}"

        verified = verify_invite_token(data["token"], doc_key=doc_key)
        assert verified is not None
        assert verified["doc_key"] == doc_key
        assert verified["scope"] == "read"
        assert verified["issued_by"] == str(test_user.id)

    def test_invite_token_rejected_for_non_member(self, test_client, db, test_user):
        repo = create_test_repo(db, name="invite-nonmember", owner_id=_other_user(db).id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")

        resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites",
            json={"doc_key": doc_key, "scope": "read"},
            headers=_auth_headers(test_user),
        )
        assert resp.status_code == 403

    def test_issue_invite_dockey_mismatch(self, test_client, db, test_user):
        repo = create_test_repo(db, name="invite-mismatch", owner_id=_other_user(db).id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        other_doc = make_doc_key(str(uuid.uuid4()), "main", "x.py")

        resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites",
            json={"doc_key": other_doc, "scope": "read"},
            headers=_auth_headers(test_user),
        )
        assert resp.status_code == 400

    def test_issue_invite_requires_auth(self, test_client, db):
        repo = create_test_repo(db, name="invite-noauth")
        resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites",
            json={"doc_key": make_doc_key(str(repo.id), "main", "a.py"), "scope": "read"},
        )
        assert resp.status_code == 401


# ==================== 校验 ====================


class TestInviteTokenVerification:

    def test_invite_token_expired(self):
        doc_key = make_doc_key(str(uuid.uuid4()), "main", "a.py")
        assert verify_invite_token(_expired_invite_token(doc_key), doc_key=doc_key) is None

    def test_invite_token_wrong_type_rejected(self):
        from services.token_service import create_access_token

        access = create_access_token({"sub": str(uuid.uuid4()), "username": "x"})
        assert verify_invite_token(access) is None

    def test_invite_token_wrong_doc_rejected(self):
        doc_key = make_doc_key(str(uuid.uuid4()), "main", "a.py")
        issued = create_invite_token(doc_key, "read", uuid.uuid4(), "issuer")
        assert verify_invite_token(issued["token"], doc_key="other:main:b.py") is None


# ==================== /collab/auth 邀请分支 ====================


class TestCollabAuthInvite:

    def _auth(self, client, user, repo, invite_token=None, branch="main", path="src/app.py"):
        body = {"token": _token_for(user), "docKey": make_doc_key(str(repo.id), branch, path)}
        if invite_token is not None:
            body["invite_token"] = invite_token
        return client.post("/api/v1/collab/auth", json=body, headers=_internal_headers())

    def test_invite_token_grants_read_only(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-invite-read", owner_id=_other_user(db).id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = create_invite_token(doc_key, "read", uuid.uuid4(), "issuer")["token"]

        resp = self._auth(test_client, test_user, repo, invite_token=invite)
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_write"] is False
        assert data["via_invite"] is True

    def test_invite_write_token_grants_write(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-invite-write", owner_id=_other_user(db).id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = create_invite_token(doc_key, "write", uuid.uuid4(), "issuer")["token"]

        resp = self._auth(test_client, test_user, repo, invite_token=invite)
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_write"] is True
        assert data["via_invite"] is True

    def test_invite_token_wrong_doc_denied(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-invite-wrongdoc", owner_id=_other_user(db).id, is_public=False)
        other_doc = make_doc_key(str(repo.id), "main", "other.py")
        invite = create_invite_token(other_doc, "write", uuid.uuid4(), "issuer")["token"]

        resp = self._auth(test_client, test_user, repo, invite_token=invite, path="src/app.py")
        assert resp.status_code == 403

    def test_non_member_without_invite_denied(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-invite-none", owner_id=_other_user(db).id, is_public=False)
        resp = self._auth(test_client, test_user, repo)
        assert resp.status_code == 403
