"""协作邀请 token 撤销测试 (collab_invite_controller revoke + 内部回调强制执行)

补齐邀请 token 生命周期: 除签发/校验外, 支持**撤销**。
- 发起人 (仓库 owner/admin) 可撤销某邀请 token (按 jti 记入黑名单);
- /collab/auth 与 /collab/save 校验撤销状态: 已撤销的邀请即时失效 (403);
- 撤销幂等; 非法/过期 token 撤销返回 400; 跨仓库 doc_key 拒绝。
"""
import uuid
from unittest.mock import AsyncMock

import pytest

from controller.collab_internal_controller import (
    INTERNAL_SECRET_ENV,
    INTERNAL_SECRET_HEADER,
    make_doc_key,
)
from models.repository_member import RepositoryMember
from services.collab_invite_service import create_invite_token
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


def _other_user(db, username="revoke_repoowner", email="revoke_owner@example.com"):
    from models.user import User

    user = User(
        username=username,
        email=email,
        password="hashed",
        full_name="Revoke Repo Owner",
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def internal_env(monkeypatch):
    monkeypatch.setenv(INTERNAL_SECRET_ENV, SECRET)


class TestInviteRevocation:
    def _revoke(self, client, host, repo, token):
        return client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites/revoke",
            json={"token": token},
            headers=_auth_headers(host),
        )

    def _auth(self, client, user, repo, invite_token, branch="main", path="src/app.py"):
        return client.post(
            "/api/v1/collab/auth",
            json={
                "token": _token_for(user),
                "docKey": make_doc_key(str(repo.id), branch, path),
                "invite_token": invite_token,
            },
            headers=_internal_headers(),
        )

    def _save(self, client, user, repo, invite_token, content="new content"):
        return client.post(
            "/api/v1/collab/save",
            json={
                "token": _token_for(user),
                "docKey": make_doc_key(str(repo.id), "main", "src/app.py"),
                "content": content,
                "message": "collab save test",
                "invite_token": invite_token,
            },
            headers=_internal_headers(),
        )

    def _invite(self, doc_key, scope="read", issuer=None):
        issuer = issuer or uuid.uuid4()
        return create_invite_token(doc_key, scope, issuer, "issuer")["token"]

    # ---------- 撤销即时生效 ----------

    def test_revoke_then_auth_denied(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="revoke-auth", owner_id=owner.id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = self._invite(doc_key)

        # test_user 非成员: 仅凭邀请 token 获得会话权限
        assert self._auth(test_client, test_user, repo, invite).status_code == 200
        assert self._revoke(test_client, owner, repo, invite).status_code == 200
        assert self._auth(test_client, test_user, repo, invite).status_code == 403

    def test_revoke_then_save_denied(self, test_client, db, test_user, internal_env, monkeypatch):
        owner = _other_user(db)
        repo = create_test_repo(db, name="revoke-save", owner_id=owner.id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = self._invite(doc_key, scope="write")
        monkeypatch.setattr(
            "services.repository_browser_service.commit_file",
            AsyncMock(return_value={"commit_id": "abc1234"}),
        )

        assert self._save(test_client, test_user, repo, invite).status_code == 200
        assert self._revoke(test_client, owner, repo, invite).status_code == 200
        assert self._save(test_client, test_user, repo, invite).status_code == 403

    def test_revoked_token_does_not_affect_other_invites(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="revoke-isolated", owner_id=owner.id, is_public=False)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite_a = self._invite(doc_key)
        invite_b = self._invite(doc_key)

        assert self._revoke(test_client, owner, repo, invite_a).status_code == 200
        assert self._auth(test_client, test_user, repo, invite_a).status_code == 403
        assert self._auth(test_client, test_user, repo, invite_b).status_code == 200

    # ---------- 端点门禁 / 校验 ----------

    def test_revoke_requires_host_role(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="revoke-forbidden", owner_id=_other_user(db).id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = self._invite(doc_key)

        assert self._revoke(test_client, test_user, repo, invite).status_code == 403

    def test_revoke_requires_auth(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="revoke-noauth", owner_id=test_user.id)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = self._invite(doc_key)

        resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/collab/invites/revoke",
            json={"token": invite},
        )
        assert resp.status_code == 401

    def test_revoke_invalid_token_rejected(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="revoke-invalid", owner_id=test_user.id)
        resp = self._revoke(test_client, test_user, repo, "not-a-valid-invite")
        assert resp.status_code == 400

    def test_revoke_foreign_dockey_rejected(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="revoke-foreign", owner_id=test_user.id)
        foreign = self._invite(make_doc_key(str(uuid.uuid4()), "main", "a.py"))
        resp = self._revoke(test_client, test_user, repo, foreign)
        assert resp.status_code == 400

    def test_revoke_is_idempotent(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="revoke-idempotent", owner_id=test_user.id)
        doc_key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = self._invite(doc_key)

        assert self._revoke(test_client, test_user, repo, invite).status_code == 200
        assert self._revoke(test_client, test_user, repo, invite).status_code == 200
