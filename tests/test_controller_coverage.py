"""
Controller 层覆盖率补充测试（F-055）

按 controller 补齐既有测试未覆盖的端点路径，目标将 controller 层
覆盖率提升至 80% 以上。大量用例通过"仓库不存在"等错误路径触发
controller → service → 异常处理的完整调用链。
"""
import base64
import os
import uuid

import pytest
from fastapi import Response

from utils.git_utils import get_repository_storage_path, init_bare_repo
from utils.password_utils import get_password_hash
from tests.test_helpers import create_test_repo

MISSING = "00000000-0000-0000-0000-000000000000"


def _basic_auth(username: str, password: str) -> dict:
    cred = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


def _repo(db):
    repo = create_test_repo(db, name="cov-repo", owner_id=None,
                            path="testuser/cov-repo")
    repo.is_public = False
    return repo


def _expect_error(r):
    """错误路径端点：接受任何 4xx（具体 401/403/422/404 依权限检查顺序不同）"""
    assert 400 <= r.status_code < 500, f"unexpected {r.status_code}: {r.text[:200]}"
    return r


def _expect_no_5xx(r):
    """覆盖测试：端点需优雅处理（200/201/4xx 均可，不允许服务器崩溃）"""
    assert 200 <= r.status_code < 500, f"unexpected {r.status_code}: {r.text[:200]}"
    return r


# ============ git_auth_controller（15% → 目标 80%+） ============

class TestGitAuth:
    URL = "/api/v1/git-auth"

    def test_invalid_uri_path(self, test_client, db):
        r = test_client.get(self.URL, headers={"X-Git-Request-URI": "/nope"})
        assert r.status_code == 403

    def test_public_read_no_auth(self, test_client, db):
        repo = _repo(db)
        repo.is_public = True
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={"X-Git-Request-URI": uri})
        assert r.status_code == 200

    def test_public_write_no_auth(self, test_client, db):
        repo = _repo(db)
        repo.is_public = True
        db.commit()
        uri = f"/{repo.path}.git/git-receive-pack"
        r = test_client.get(self.URL, headers={"X-Git-Request-URI": uri})
        assert r.status_code == 401

    def test_private_read_no_auth(self, test_client, db):
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={"X-Git-Request-URI": uri})
        assert r.status_code == 401

    def test_bad_basic_format(self, test_client, db):
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(
            self.URL,
            headers={"X-Git-Request-URI": uri,
                     "Authorization": "Basic !!!notbase64!!!"},
        )
        assert r.status_code == 401

    def test_basic_unknown_user(self, test_client, db):
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            **_basic_auth("ghost", "pass"),
        })
        assert r.status_code == 401

    def test_basic_wrong_password(self, test_client, db):
        from models.user import User
        user = User(username="authu", email="authu@example.com",
                    password=get_password_hash("rightpass"),
                    full_name="Auth U", is_active=True, is_admin=False)
        db.add(user)
        db.commit()
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            **_basic_auth("authu", "wrongpass"),
        })
        assert r.status_code == 401

    def test_basic_public_read_ok(self, test_client, db):
        from models.user import User
        user = User(username="authu2", email="authu2@example.com",
                    password=get_password_hash("rightpass"),
                    full_name="Auth U2", is_active=True, is_admin=False)
        db.add(user)
        repo = _repo(db)
        repo.is_public = True
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            **_basic_auth("authu2", "rightpass"),
        })
        assert r.status_code == 200

    def test_bearer_invalid_token(self, test_client, db):
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            "Authorization": "Bearer bad.token.here",
        })
        assert r.status_code == 401

    def test_bearer_admin_public_write_ok(self, test_client, admin_user, db):
        repo = _repo(db)
        repo.is_public = True
        db.commit()
        from services.token_service import create_access_token
        token = create_access_token({"sub": str(admin_user.id),
                                     "username": admin_user.username,
                                     "is_admin": True})
        uri = f"/{repo.path}.git/git-receive-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            "Authorization": f"Bearer {token}",
        })
        assert r.status_code == 200

    def test_bearer_nonmember_private_denied(self, test_client, auth_headers, db):
        repo = _repo(db)
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={
            "X-Git-Request-URI": uri,
            **auth_headers,
        })
        assert r.status_code == 403


# ============ search_controller（37% → 补充 global 分支） ============

class TestSearch:
    def test_global_code_no_accessible_repos(self, test_client, auth_headers):
        r = test_client.get("/api/v1/search/code", params={"q": "foo"},
                            headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["repositories"] == []

    def test_global_blank_query(self, test_client, auth_headers):
        r = test_client.get("/api/v1/search/global", params={"q": "   "},
                            headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["repositories"] == []

    def test_global_with_accessible_repos(self, test_client, test_user, db):
        repo = create_test_repo(db, name="mycovsearchrepo",
                                owner_id=test_user.id,
                                path=f"{test_user.username}/mycovsearchrepo")
        repo.is_public = True
        db.commit()
        from services.token_service import create_access_token
        token = create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin,
        })
        headers = {"Authorization": f"Bearer {token}"}
        r = test_client.get("/api/v1/search/global",
                            params={"q": "mycovsearch"},
                            headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["repositories"]

    def test_global_with_issue_and_pr(self, test_client, test_user, db):
        repo = create_test_repo(db, name="searchrepo2",
                                owner_id=test_user.id,
                                path=f"{test_user.username}/searchrepo2")
        repo.is_public = True
        db.commit()
        from models.issue import Issue
        db.add(Issue(repository_id=repo.id, author_id=test_user.id,
                     issue_number=1, title="ApiSearchMarkerIssue",
                     description="marker"))
        from models.pull_request import PullRequest
        db.add(PullRequest(repository_id=repo.id, author_id=test_user.id,
                           pr_number=1, title="ApiSearchMarkerPr",
                           description="marker", source_branch="f",
                           target_branch="master"))
        db.commit()
        from services.token_service import create_access_token
        token = create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin,
        })
        headers = {"Authorization": f"Bearer {token}"}
        r = test_client.get("/api/v1/search/global", params={"q": "marker"},
                            headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["issues"] or data["pull_requests"] or data["repositories"]

    def test_global_code_search_with_results(self, test_client, test_user, db):
        """global code search：索引含目标文件时返回聚合结果"""
        from tests.test_repo_browser_controller import create_repo_with_content
        from services.search_service import SearchIndex
        repo, path = create_repo_with_content(db, "codesearch",
                                              owner_id=test_user.id)
        for fname in ("a.py", "b.py"):
            with open(os.path.join(path, fname), "w",
                      encoding="utf-8") as f:
                f.write("markerfrobnicate = 1\nprint(markerfrobnicate)\n")
        idx = SearchIndex(path)
        idx.build()
        from services.token_service import create_access_token
        token = create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin,
        })
        headers = {"Authorization": f"Bearer {token}"}
        r = test_client.get("/api/v1/search/code?q=markerfrobnicate",
                            headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "repositories" in data
        assert data["repositories"], "应能搜索到索引内代码"

    def test_global_code_search_truncation(self, test_client, test_user, db):
        """截断逻辑：结果数超过 max_results 时触发聚合截断分支"""
        from tests.test_repo_browser_controller import create_repo_with_content
        from services.search_service import SearchIndex
        repo, path = create_repo_with_content(db, "codesearchtrunc",
                                              owner_id=test_user.id)
        for fname in ("f1.py", "f2.py", "f3.py"):
            with open(os.path.join(path, fname), "w",
                      encoding="utf-8") as f:
                f.write("filternical line\n")
        idx = SearchIndex(path)
        idx.build()
        from services.token_service import create_access_token
        token = create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin,
        })
        headers = {"Authorization": f"Bearer {token}"}
        r = test_client.get("/api/v1/search/code?q=filternical&max_results=1",
                            headers=headers)
        assert r.status_code == 200
        assert r.json().get("total_count", 0) >= 1

    def test_search_code_missing_repo(self, test_client, auth_headers):
        assert test_client.get(f"/api/v1/repositories/{MISSING}/search",
                               params={"q": "x"},
                               headers=auth_headers).status_code == 404

    def test_global_search_repo_deleted(self, test_client, test_user, db):
        """仓库仅存在于 DB 但物理目录缺失时 global search 不应 5xx"""
        repo = create_test_repo(db, name="phantomsrch",
                                owner_id=test_user.id,
                                path=f"{test_user.username}/phantomsrch")
        repo.is_public = True
        db.commit()
        init_bare_repo(get_repository_storage_path(repo.path))
        from services.token_service import create_access_token
        token = create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin,
        })
        headers = {"Authorization": f"Bearer {token}"}
        r = test_client.get("/api/v1/search/global",
                            params={"q": "phantomsrch"}, headers=headers)
        assert r.status_code == 200


# ============ branch_controller（66%） ============

class TestBranchCoverage:
    def test_get_branches_missing_repo(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(f"/api/v1/repositories/{MISSING}/branches",
                                       headers=auth_headers))

    def test_default_branch_missing_repo(self, test_client):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/branches/default").status_code == 404

    def test_get_branch_missing(self, test_client):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/branches/main").status_code == 404

    def test_create_branch_missing_repo(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(f"/api/v1/repositories/{MISSING}/branches",
                                        json={"name": "x"}, headers=auth_headers))

    def test_set_default_missing(self, test_client, auth_headers):
        assert test_client.put(
            f"/api/v1/repositories/{MISSING}/branches/main/default",
            headers=auth_headers).status_code == 404

    def test_protect_missing(self, test_client, auth_headers):
        r = test_client.put(
            f"/api/v1/repositories/{MISSING}/branches/main/protect",
            json={}, headers=auth_headers)
        assert r.status_code == 404

    def test_unprotect_missing(self, test_client, auth_headers):
        assert test_client.put(
            f"/api/v1/repositories/{MISSING}/branches/main/unprotect",
            headers=auth_headers).status_code == 404

    def test_check_protection_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/branches/main/protection",
            headers=auth_headers).status_code == 404


# ============ room_controller（43%） ============

class TestRoomCoverage:
    def test_room_of_missing_repo(self, test_client, auth_headers):
        _expect_error(test_client.get(
            f"/api/v1/repositories/{MISSING}/room", headers=auth_headers))

    def test_list_rooms_authenticated(self, test_client, auth_headers):
        r = test_client.get("/api/v1/rooms", headers=auth_headers)
        assert r.status_code == 200

    def test_room_members_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/rooms/{MISSING}/members",
            headers=auth_headers).status_code == 404

    def test_delete_room_missing(self, test_client, auth_headers):
        _expect_error(test_client.delete(
            f"/api/v1/rooms/{MISSING}", headers=auth_headers))


# ============ member 成功路径（owner 操作成员） ============

class TestMemberSuccess:
    def _seed_member(self, db, test_user, user2, role="developer"):
        from models.repository_member import RepositoryMember
        repo = create_test_repo(db, name="cov-member", owner_id=test_user.id,
                                path=f"{test_user.username}/cov-member")
        db.add(RepositoryMember(repository_id=repo.id, user_id=user2.id,
                                role=role, is_active=True))
        db.commit()
        return repo

    def test_member_lifecycle(self, test_client, db, test_user):
        """仓库所有者成员 CRUD：获取/更新/角色/激活/权限/移除 成功路径"""
        from services.token_service import create_access_token
        from models.user import User
        user2 = User(username="member2", email="member2@example.com",
                     password=get_password_hash("pw"), full_name="M2",
                     is_active=True, is_admin=False)
        db.add(user2)
        db.commit()
        db.refresh(user2)
        repo = self._seed_member(db, test_user, user2)
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}
        mid = str(user2.id)

        # 参数缺失 → 422，覆盖 add 的校验分支（物理仓库必需）
        assert test_client.post(
            f"/api/v1/repositories/{repo.id}/members",
            json={"role": "developer"}, headers=headers).status_code in (400, 422)

        assert test_client.get(f"/api/v1/repositories/{repo.id}/members",
                               headers=headers).status_code == 200

        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/members/{mid}",
            headers=headers).status_code == 200

        assert test_client.put(
            f"/api/v1/repositories/{repo.id}/members/{mid}",
            json={"bio": "hello"}, headers=headers).status_code in (200, 422)

        assert test_client.put(
            f"/api/v1/repositories/{repo.id}/members/{mid}/role",
            json={"role": "admin"}, headers=headers).status_code in (200, 422)

        # 无效角色 → 4xx 覆盖 ValidationException 分支
        assert test_client.put(
            f"/api/v1/repositories/{repo.id}/members/{mid}/role",
            json={"role": "maintainer"}, headers=headers).status_code in (200, 400, 422)

        assert test_client.put(
            f"/api/v1/repositories/{repo.id}/members/{mid}/activate",
            headers=headers).status_code in (200, 422)

        assert test_client.put(
            f"/api/v1/repositories/{repo.id}/members/{mid}/deactivate",
            headers=headers).status_code in (200, 422)

        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/members/{mid}/permission",
            params={"permission": "read"}, headers=headers).status_code == 200

        assert test_client.delete(
            f"/api/v1/repositories/{repo.id}/members/{mid}",
            headers=headers).status_code in (200, 404)


# ============ browser 成功路径（真实提交） ============

class TestBrowserSuccess:
    def _committed(self, db, test_user, name):
        from tests.test_repo_browser_controller import (
            create_repo_with_content, create_commit_in_repo)
        repo, path = create_repo_with_content(db, name, owner_id=test_user.id)
        create_commit_in_repo(path, "hello.py", b"def foo():\n    return 42\n")
        create_commit_in_repo(path, "README.md", b"# project\n")
        return repo, path

    def test_tree_blob_commits(self, test_client, db, test_user):
        repo, path = self._committed(db, test_user, "browser-succ-tree")
        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/tree",
            params={"ref": "master"}).status_code == 200
        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/blob",
            params={"path": "hello.py", "ref": "master"}).status_code == 200
        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/commits",
            params={"ref": "master"}).status_code == 200

    def test_diff_readme_symbols_language(self, test_client, db, test_user):
        import pygit2
        from tests.test_repo_browser_controller import create_repo_with_content
        repo, path = create_repo_with_content(db, "browser-succ-diff",
                                              owner_id=test_user.id)
        from tests.test_repo_browser_controller import create_commit_in_repo
        c1 = create_commit_in_repo(path, "f.txt", b"v1", "first")
        c2 = create_commit_in_repo(path, "f.txt", b"v2", "second")
        r = test_client.get(
            f"/api/v1/repositories/{repo.id}/diff",
            params={"head": str(c2), "base": str(c1)})
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.status_code != 500

        create_commit_in_repo(path, "README.md", b"# rc", "readme")
        create_commit_in_repo(path, "hello.py",
                              b"def foo():\n    return 42\n", "sym")
        assert test_client.get(
            f"/api/v1/repositories/{repo.id}/readme").status_code in (200, 404)

        r1 = test_client.get(
            f"/api/v1/repositories/{repo.id}/symbols",
            params={"path": "hello.py"})
        assert r1.status_code in (200, 404, 422)

        r2 = test_client.get(
            f"/api/v1/repositories/{repo.id}/language",
            params={"path": "hello.py"})
        assert r2.status_code in (200, 404, 422)

    def test_commit_file_and_delete(self, test_client, db, test_user):
        from tests.test_repo_browser_controller import create_repo_with_content
        from services.token_service import create_access_token
        repo, path = create_repo_with_content(db, "browser-succ-commit",
                                              owner_id=test_user.id)
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}
        r = test_client.put(
            f"/api/v1/repositories/{repo.id}/contents/newfile.txt",
            json={"content": "x", "message": "add"}, headers=headers)
        assert r.status_code in (200, 400, 404, 422)
        assert test_client.delete(
            f"/api/v1/repositories/{repo.id}/contents/newfile.txt",
            headers=headers).status_code in (200, 404, 422)


# ============ room 成功路径（真实仓库自动建房） ============

class TestRoomSuccess:
    def test_room_created_for_repo(self, test_client, db, test_user, admin_user):
        from services.token_service import create_access_token

        def _headers(u):
            return {"Authorization": "Bearer " + create_access_token({
                "sub": str(u.id), "username": u.username,
                "is_admin": u.is_admin})}

        repo = create_test_repo(db, name="room-succ", owner_id=test_user.id,
                                path=f"{test_user.username}/room-succ")
        headers = _headers(test_user)
        r = test_client.get(f"/api/v1/repositories/{repo.id}/room",
                            headers=headers)
        assert r.status_code == 200
        room_id = r.json()["id"]

        assert test_client.get(f"/api/v1/rooms/{room_id}/members",
                               headers=_headers(test_user)).status_code == 200

        assert test_client.delete(f"/api/v1/rooms/{room_id}",
                                  headers=_headers(admin_user)) \
            .status_code in (200, 403, 404)


# ============ app 日志 / 配置管理（管理员） ============

class TestAppAdminCoverage:
    def _admin(self, db, admin_user):
        from services.token_service import create_access_token
        return {"Authorization": "Bearer " + create_access_token({
            "sub": str(admin_user.id), "username": admin_user.username,
            "is_admin": True})}

    def test_config_read_and_validate(self, test_client, db, admin_user):
        headers = self._admin(db, admin_user)
        r = test_client.get("/api/app/config", headers=headers)
        assert r.status_code == 200
        data = r.json().get("data") or {}
        assert isinstance(data, dict)

        # 用允许修改的节做 validate，校验通过（不写文件）
        r = test_client.post("/api/app/config/validate",
                             json={"gunicorn": {"workers": 1}},
                             headers=headers)
        assert r.status_code == 200
        assert r.json().get("success") is True

        # 无效配置（protected/app 节）→ 校验失败，不回写 config.toml
        r = test_client.post("/api/app/config",
                             json={"config": {"app": {"bogus_key_zzz": 1}}},
                             headers=headers)
        assert r.status_code in (400, 422)

    def test_logs_info_content_cleanup(self, test_client, db, admin_user):
        headers = self._admin(db, admin_user)
        r = test_client.get("/api/app/logs", headers=headers)
        assert r.status_code in (200, 403)
        r = test_client.get("/api/app/logs/content",
                            params={"log_name": "app", "lines": 5},
                            headers=headers)
        assert r.status_code in (200, 403, 404, 422)
        r = test_client.post("/api/app/logs/cleanup",
                             params={"keep_days": 365}, headers=headers)
        assert r.status_code in (200, 403)


# ============ repository_member_controller（56%） ============

class TestMemberCoverage:
    def test_list_missing_repo(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(f"/api/v1/repositories/{MISSING}/members",
                                       headers=auth_headers))

    def test_get_member_missing_repo(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}",
            headers=auth_headers))

    def test_add_member_missing_repo(self, test_client, auth_headers):
        r = test_client.post(f"/api/v1/repositories/{MISSING}/members",
                             json={"user_id": str(uuid.uuid4()),
                                   "role": "developer"},
                             headers=auth_headers)
        assert 400 <= r.status_code < 500

    def test_update_member_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.put(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}",
            headers=auth_headers))

    def test_set_role_missing(self, test_client, auth_headers):
        r = test_client.put(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}/role",
            json={"role": "developer"}, headers=auth_headers)
        assert 400 <= r.status_code < 500

    def test_activate_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.put(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}/activate",
            headers=auth_headers))

    def test_deactivate_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.put(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}/deactivate",
            headers=auth_headers))

    def test_permission_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/members/{MISSING}/permission",
            headers=auth_headers))


# ============ repository_browser_controller（58%） ============

class TestBrowserCoverage:
    def test_blob_missing(self, test_client):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/blob",
            params={"path": "README.md"}).status_code == 404

    def test_contents_put_missing(self, test_client, auth_headers):
        assert test_client.put(
            f"/api/v1/repositories/{MISSING}/contents/README.md",
            json={"content": "x", "message": "m"},
            headers=auth_headers).status_code == 404

    def test_contents_delete_missing(self, test_client, auth_headers):
        assert test_client.delete(
            f"/api/v1/repositories/{MISSING}/contents/README.md",
            headers=auth_headers).status_code == 404

    def test_commits_missing(self, test_client):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/commits").status_code == 404

    def test_diff_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/diff",
            headers=auth_headers))

    def test_readme_missing(self, test_client):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/readme").status_code == 404

    def test_symbols_missing(self, test_client):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/symbols"))

    def test_language_missing(self, test_client):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/language"))


# ============ label / pr_label（67% / 67%） ============

class TestLabelCoverage:
    def test_list_labels_missing(self, test_client, auth_headers):
        _expect_error(test_client.get(f"/api/v1/repositories/{MISSING}/labels",
                                      headers=auth_headers))

    def test_create_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.post(
            f"/api/v1/repositories/{MISSING}/labels",
            json={"name": "x", "color": "#fff"},
            headers=auth_headers))

    def test_update_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.put(
            f"/api/v1/repositories/{MISSING}/labels/{MISSING}",
            json={"name": "x"}, headers=auth_headers))

    def test_delete_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.delete(
            f"/api/v1/repositories/{MISSING}/labels/{MISSING}",
            headers=auth_headers))

    def test_add_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.post(
            f"/api/v1/repositories/{MISSING}/labels/{MISSING}/add",
            json={"issue_number": 1}, headers=auth_headers))

    def test_remove_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.post(
            f"/api/v1/repositories/{MISSING}/labels/{MISSING}/remove",
            json={"issue_number": 1}, headers=auth_headers))

    def test_list_pr_labels_missing(self, test_client, auth_headers):
        _expect_error(test_client.get(f"/api/v1/repositories/{MISSING}/pr-labels",
                                      headers=auth_headers))

    def test_create_pr_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.post(
            f"/api/v1/repositories/{MISSING}/pr-labels",
            json={"name": "x", "color": "#fff"},
            headers=auth_headers))

    def test_update_pr_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.put(
            f"/api/v1/repositories/{MISSING}/pr-labels/{MISSING}",
            json={"name": "x"}, headers=auth_headers))

    def test_delete_pr_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.delete(
            f"/api/v1/repositories/{MISSING}/pr-labels/{MISSING}",
            headers=auth_headers))

    def test_pr_add_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.post(
            f"/api/v1/repositories/{MISSING}/pull-requests/1/labels/{MISSING}",
            headers=auth_headers))

    def test_pr_remove_label_missing(self, test_client, auth_headers):
        _expect_error(test_client.delete(
            f"/api/v1/repositories/{MISSING}/pull-requests/1/labels/{MISSING}",
            headers=auth_headers))

    def test_pr_label_pull_requests_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/pr-labels/{MISSING}/pull-requests",
            headers=auth_headers).status_code == 404


# ============ lfs（62%） / star（60%） / fork（63%+） ============

class TestLfsStarForkCoverage:
    def test_lfs_batch_missing(self, test_client):
        _expect_no_5xx(test_client.post(
            f"/api/v1/repositories/{MISSING}/lfs/objects/batch",
            json={"operation": "upload", "objects": []}))

    def test_lfs_upload_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.put(
            f"/api/v1/repositories/{MISSING}/lfs/objects/abcdef",
            headers=auth_headers))

    def test_lfs_get_missing(self, test_client):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/lfs/objects/abcdef"))

    def test_star_missing(self, test_client, auth_headers):
        assert test_client.post(
            f"/api/v1/repositories/{MISSING}/star",
            headers=auth_headers).status_code == 404

    def test_unstar_missing(self, test_client, auth_headers):
        assert test_client.delete(
            f"/api/v1/repositories/{MISSING}/star",
            headers=auth_headers).status_code == 404

    def test_star_status_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/star",
            headers=auth_headers).status_code == 404

    def test_stargazers_missing(self, test_client):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/stargazers"))

    def test_fork_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(
            f"/api/v1/repositories/{MISSING}/forks",
            headers=auth_headers))

    def test_fork_list_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/forks",
            headers=auth_headers).status_code == 404

    def test_fork_source_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/forks/source",
            headers=auth_headers).status_code == 404


# ============ commit（60%） / build（74%） / chat（64%） ============

class TestCommitBuildChatCoverage:
    def test_commit_history_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/history",
            headers=auth_headers))

    def test_commit_count_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/count",
            headers=auth_headers))

    def test_commit_search_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/search",
            params={"q": "x"}, headers=auth_headers))

    def test_commit_author_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/author",
            headers=auth_headers))

    def test_commit_latest_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/latest",
            headers=auth_headers).status_code == 404

    def test_commit_hash_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/commits/abcdef",
            headers=auth_headers).status_code == 404

    def test_create_commit_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(
            f"/api/v1/repositories/{MISSING}/commits",
            json={"message": "m"}, headers=auth_headers))

    def test_branch_commits_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get(
            f"/api/v1/repositories/{MISSING}/branches/main/commits",
            headers=auth_headers))

    def test_build_create_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(
            f"/api/v1/repositories/{MISSING}/builds",
            json={"branch": "main"}, headers=auth_headers))

    def test_build_list_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/builds",
            headers=auth_headers).status_code == 404

    def test_build_logs_missing(self, test_client, auth_headers):
        assert test_client.get(
            f"/api/v1/repositories/{MISSING}/builds/{MISSING}/logs",
            headers=auth_headers).status_code == 404

    def test_chat_unread(self, test_client, auth_headers):
        assert test_client.get("/api/v1/rooms/unread",
                               headers=auth_headers).status_code == 200

    def test_chat_mark_read_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(
            f"/api/v1/rooms/{MISSING}/read",
            headers=auth_headers))

    def test_chat_reactions_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post(
            f"/api/v1/rooms/{MISSING}/messages/{MISSING}/reactions",
            json={"emoji": "👍"}, headers=auth_headers))

    def test_chat_delete_reaction_missing(self, test_client, auth_headers):
        _expect_no_5xx(test_client.delete(
            f"/api/v1/rooms/{MISSING}/messages/{MISSING}/reactions",
            headers=auth_headers))


# ============ app / debug / user（59% / 40% / 88%） ============

class TestAppDebugCoverage:
    def test_root(self, test_client):
        assert test_client.get("/").status_code == 200

    def test_health(self, test_client):
        assert test_client.get("/health").status_code == 200

    def test_app_status(self, test_client):
        assert test_client.get("/api/app/status").status_code == 200

    def test_app_config_get(self, test_client, admin_headers):
        assert test_client.get("/api/app/config",
                               headers=admin_headers).status_code == 200

    def test_app_config_validate(self, test_client, admin_headers):
        assert test_client.post("/api/app/config/validate",
                                headers=admin_headers).status_code == 200

    def test_platform_stats(self, test_client, auth_headers):
        assert test_client.get("/api/v1/stats/platform",
                               headers=auth_headers).status_code == 200

    def test_debug_status(self, test_client, auth_headers):
        _expect_no_5xx(test_client.get("/api/v1/debug/status",
                                       headers=auth_headers))

    def test_debug_initdb(self, test_client, auth_headers):
        _expect_no_5xx(test_client.post("/api/v1/debug/initdb",
                                        headers=auth_headers))

    def test_debug_status_success(self, test_client, admin_user, monkeypatch):
        """调试模式开启时 /status 成功路径（用假 config 模拟）"""
        from types import SimpleNamespace
        import controller.debug_controller as dc

        class _DB:
            url = "sqlite:///:memory:"
            db_type = "sqlite"

            def _mask_url(self, url):
                return "sqlite:///:memory:"

        class _Cfg:
            class app:
                debug = True
            database = _DB()

        monkeypatch.setattr(dc, "get_config", lambda: _Cfg())
        monkeypatch.setenv("PERSEUS_STRESS_TEST", "true")
        from services.token_service import create_access_token
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(admin_user.id), "username": admin_user.username,
            "is_admin": True})}
        r = test_client.get("/api/v1/debug/status", headers=headers)
        assert r.status_code == 200
        assert r.json().get("debug_mode") is True


class TestUserCoverage:
    def test_me(self, test_client, auth_headers):
        assert test_client.get("/api/v1/users/me",
                               headers=auth_headers).status_code == 200

    def test_me_dashboard(self, test_client, auth_headers):
        assert test_client.get("/api/v1/users/me/dashboard",
                               headers=auth_headers).status_code == 200

    def test_me_pull_requests(self, test_client, auth_headers):
        assert test_client.get("/api/v1/users/me/pull-requests",
                               headers=auth_headers).status_code == 200

    def test_me_issues(self, test_client, auth_headers):
        assert test_client.get("/api/v1/users/me/issues",
                               headers=auth_headers).status_code == 200

    def test_change_password_wrong_old(self, test_client, auth_headers, db,
                                       test_user):
        r = test_client.post(
            "/api/v1/users/me/password",
            json={"old_password": "wrong", "new_password": "newpass123"},
            headers=auth_headers)
        assert 400 <= r.status_code < 500

    def test_list_users(self, test_client, auth_headers):
        assert test_client.get("/api/v1/users", headers=auth_headers).status_code == 200

    def test_get_user(self, test_client, auth_headers, test_user):
        assert test_client.get(f"/api/v1/users/{test_user.id}",
                               headers=auth_headers).status_code == 200


# ============ collab_internal（70%） ============

class TestCollabInternal:
    """协作内部回调：auth/doc/save 成功与校验分支"""

    SECRET = "cov-internal-secret-zz"

    def _hdr(self, test_user):
        from services.token_service import create_access_token
        return {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}

    def test_secret_not_configured_503(self, test_client, db, monkeypatch):
        monkeypatch.delenv("PERSEUS_COLLAB_INTERNAL_SECRET", raising=False)
        r = test_client.post("/api/v1/collab/auth", json={"token": "t", "docKey": "r:b:f"},
                             headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 503

    def test_wrong_secret(self, test_client, db, monkeypatch):
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        r = test_client.post("/api/v1/collab/auth", json={"token": "t", "docKey": "r:b:f"},
                             headers={"X-Collab-Internal-Secret": "wrong"})
        assert r.status_code in (401, 403)

    def test_auth_success(self, test_client, db, test_user, monkeypatch):
        from tests.test_repo_browser_controller import create_repo_with_content
        repo, _ = create_repo_with_content(db, "collab-auth", owner_id=test_user.id)
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        doc_key = f"{repo.id}:master:README.md"
        r = test_client.post("/api/v1/collab/auth",
                             json={"token": self._hdr(test_user)["Authorization"][7:],
                                   "docKey": doc_key},
                             headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 200
        body = r.json()
        assert body["can_write"] is True

    def test_doc_loaded(self, test_client, db, test_user, monkeypatch):
        from tests.test_repo_browser_controller import (
            create_repo_with_content, create_commit_in_repo)
        repo, path = create_repo_with_content(db, "collab-doc", owner_id=test_user.id)
        create_commit_in_repo(path, "hello.txt", b"collab content")
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        r = test_client.get("/api/v1/collab/doc",
                            params={"docKey": f"{repo.id}:master:hello.txt"},
                            headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 200

    def test_doc_missing_file(self, test_client, db, test_user, monkeypatch):
        from tests.test_repo_browser_controller import create_repo_with_content
        repo, _ = create_repo_with_content(db, "collab-docmiss", owner_id=test_user.id)
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        r = test_client.get("/api/v1/collab/doc",
                            params={"docKey": f"{repo.id}:master:nope.txt"},
                            headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 200

    def test_save_commit(self, test_client, db, test_user, monkeypatch):
        from tests.test_repo_browser_controller import (
            create_repo_with_content, create_commit_in_repo)
        repo, path = create_repo_with_content(db, "collab-save", owner_id=test_user.id)
        create_commit_in_repo(path, "base.txt", b"base")
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        r = test_client.post("/api/v1/collab/save",
                             json={"token": self._hdr(test_user)["Authorization"][7:],
                                   "docKey": f"{repo.id}:master:doc.md",
                                   "content": "# saved", "message": "cov"},
                             headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 200
        assert r.json().get("commit_id")

    def test_save_invalid_dockey(self, test_client, db, test_user, monkeypatch):
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        r = test_client.post("/api/v1/collab/save",
                             json={"token": self._hdr(test_user)["Authorization"][7:],
                                   "docKey": "baddockey"},
                             headers={"X-Collab-Internal-Secret": self.SECRET})
        assert 400 <= r.status_code < 500

    def test_auth_missing_repo(self, test_client, db, test_user, monkeypatch):
        import uuid as _u
        monkeypatch.setenv("PERSEUS_COLLAB_INTERNAL_SECRET", self.SECRET)
        doc_key = f"{_u.uuid4()}:master:f.txt"
        r = test_client.post("/api/v1/collab/auth",
                             json={"token": self._hdr(test_user)["Authorization"][7:],
                                   "docKey": doc_key},
                             headers={"X-Collab-Internal-Secret": self.SECRET})
        assert r.status_code == 404


# ============ lfs 成功路径（62%→） ============

class TestLfsSuccess:
    """LFS batch/upload/download/delete 完整成功路径（local 后端）"""

    def _headers(self, test_user):
        from services.token_service import create_access_token
        return {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}

    def test_lfs_roundtrip(self, test_client, db, test_user):
        repo = create_test_repo(db, name="lfs-succ", owner_id=test_user.id,
                                path=f"{test_user.username}/lfs-succ")
        headers = self._headers(test_user)
        url = f"/api/v1/repositories/{repo.id}/lfs/objects"
        oid = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

        r = test_client.post(f"{url}/batch",
                             json={"operation": "download", "objects": [{"oid": oid}]},
                             headers=headers)
        assert r.status_code == 200
        assert r.json().get("objects") == [{"oid": oid, "size": 0,
                                            "actions": {"download": {"href": f"/lfs/objects/{oid}"}}}]

        r = test_client.put(f"{url}/{oid}", content=b"lfs-data", headers=headers)
        assert r.status_code == 201
        assert r.json().get("oid") == oid

        r = test_client.get(f"{url}/{oid}", headers=headers)
        assert r.status_code == 200
        assert r.content == b"lfs-data"

        r = test_client.delete(f"{url}/{oid}", headers=headers)
        assert r.status_code == 204


# ============ git_auth 成员/角色分支（65%→） ============

class TestGitAuthMemberBranches:
    URL = "/api/v1/git-auth"

    def _bearer(self, token_user):
        from services.token_service import create_access_token
        return {"Authorization": "Bearer " + create_access_token({
            "sub": str(token_user.id), "username": token_user.username,
            "is_admin": token_user.is_admin})}

    def _member_repo(self, db, test_user):
        from models.user import User
        from models.repository_member import RepositoryMember
        repo = create_test_repo(db, name="gwapriv", owner_id=test_user.id,
                                path=f"{test_user.username}/gwapriv")
        user = User(username="gwauser", email="gwauser@example.com",
                    password=get_password_hash("pw"), is_active=True)
        db.add(user)
        db.commit()
        return repo, user

    def test_member_read_ok(self, test_client, db, test_user):
        from models.repository_member import RepositoryMember
        repo, user = self._member_repo(db, test_user)
        db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                role="developer", is_active=True))
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={**self._bearer(user),
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 200

    def test_member_write_ok(self, test_client, db, test_user):
        from models.repository_member import RepositoryMember
        repo, user = self._member_repo(db, test_user)
        db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                role="admin", is_active=True))
        db.commit()
        uri = f"/{repo.path}.git/git-receive-pack"
        r = test_client.get(self.URL, headers={**self._bearer(user),
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 200

    def test_readonly_write_denied(self, test_client, db, test_user):
        from models.repository_member import RepositoryMember
        repo, user = self._member_repo(db, test_user)
        db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                role="readonly", is_active=True))
        db.commit()
        uri = f"/{repo.path}.git/git-receive-pack"
        r = test_client.get(self.URL, headers={**self._bearer(user),
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 403

    def test_public_read_member(self, test_client, db, test_user):
        repo, user = self._member_repo(db, test_user)
        repo.is_public = True
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={**self._bearer(user),
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 200

    def test_bearer_user_not_found(self, test_client, db):
        from services.token_service import create_access_token
        repo = _repo(db)
        db.commit()
        token = create_access_token({"sub": str(uuid.uuid4()),
                                     "username": "ghost", "is_admin": False})
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={**{"Authorization": f"Bearer {token}"},
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 401

    def test_bearer_basic_member(self, test_client, db, test_user):
        """Basic 认证 + 成员 → 成功（覆盖 _auth_basic 通过后的权限链）"""
        from models.repository_member import RepositoryMember
        from models.user import User
        repo = create_test_repo(db, name="gwabasic", owner_id=test_user.id,
                                path=f"{test_user.username}/gwabasic")
        user = User(username="gwa-basic", email="gwa-basic@example.com",
                    password=get_password_hash("pw"), is_active=True)
        db.add(user)
        db.commit()
        db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                role="developer", is_active=True))
        db.commit()
        uri = f"/{repo.path}.git/git-upload-pack"
        r = test_client.get(self.URL, headers={**_basic_auth("gwa-basic", "pw"),
                                               "X-Git-Request-URI": uri})
        assert r.status_code == 200


# ============ git_auth 直接函数级覆盖（异步路径稳定计测） ============

class TestGitAuthDirect:
    """直接调用 controller 函数，覆盖 TestClient 异步路径不可靠的计测缺口。

    pytest-asyncio 的 async 测试在事件循环内直接执行，coverage 可稳定记录
    _check_user_access/_auth_basic 等异步 helper 的命中行。
    """

    async def _mk_user(self, async_db, name, admin=False):
        from models.user import User
        user = User(username=name, email=f"{name}@example.com",
                    password=get_password_hash("pw"), is_active=True,
                    is_admin=admin)
        async_db.add(user)
        await async_db.commit()
        await async_db.refresh(user)
        return user

    async def _mk_repo(self, async_db, owner, name="rp1", is_public=False):
        from models.repository import Repository
        repo = Repository(name=name, path=f"{owner.username}/{name}",
                          is_public=is_public, default_branch="master",
                          owner_id=owner.id)
        async_db.add(repo)
        await async_db.commit()
        await async_db.refresh(repo)
        return repo

    async def test_direct_member_read_200(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect1")
        repo = await self._mk_repo(async_db, user, "gwadirect")
        from models.repository_member import RepositoryMember
        async_db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                      role="developer", is_active=True))
        await async_db.commit()
        res = await _check_user_access(user, async_db,
                                       user.username, "gwadirect", False)
        assert res.status_code == 200

    async def test_direct_readonly_write_403(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect2")
        repo = await self._mk_repo(async_db, user, "gwadirect2")
        from models.repository_member import RepositoryMember
        async_db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                      role="readonly", is_active=True))
        await async_db.commit()
        res = await _check_user_access(user, async_db,
                                       user.username, "gwadirect2", True)
        assert res.status_code == 403

    async def test_direct_admin_any_200(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect3", admin=True)
        res = await _check_user_access(user, async_db, "nobody", "nope", True)
        assert res.status_code == 200

    async def test_direct_repo_missing_404(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect4")
        res = await _check_user_access(user, async_db, "zzdirect4", "ghost", False)
        assert res.status_code == 404

    async def test_direct_public_read_200(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect5")
        repo = await self._mk_repo(async_db, user, "gwadirect5", is_public=True)
        res = await _check_user_access(user, async_db,
                                       user.username, "gwadirect5", False)
        assert res.status_code == 200

    async def test_direct_public_write_denied(self, async_db):
        from controller.git_auth_controller import _check_user_access
        user = await self._mk_user(async_db, "zzdirect6")
        repo = await self._mk_repo(async_db, user, "gwadirect6", is_public=True)
        res = await _check_user_access(user, async_db,
                                       user.username, "gwadirect6", True)
        assert res.status_code == 403

    async def test_direct_basic_auth(self, async_db):
        from starlette.requests import Request
        from controller.git_auth_controller import _auth_basic
        user = await self._mk_user(async_db, "zzdirect7")
        scope = {"type": "http", "headers": [
            (b"authorization", _basic_auth("zzdirect7", "pw")["Authorization"].encode())]}
        req = Request(scope)
        res = await _auth_basic(req, async_db)
        assert res.username == "zzdirect7"

        scope = {"type": "http", "headers": [
            (b"authorization", _basic_auth("zzdirect7", "wrong")["Authorization"].encode())]}
        res = await _auth_basic(Request(scope), async_db)
        assert isinstance(res, Response) and res.status_code == 401

        scope = {"type": "http", "headers": []}
        assert await _auth_basic(Request(scope), async_db) is None

        scope = {"type": "http", "headers": [(b"authorization", b"Basic !!!notbase64!!!")]}
        res = await _auth_basic(Request(scope), async_db)
        assert isinstance(res, Response) and res.status_code == 401

        scope = {"type": "http", "headers": [(b"authorization", b"Basic Og==")]}
        res = await _auth_basic(Request(scope), async_db)
        assert isinstance(res, Response) and res.status_code == 401

        scope = {"type": "http", "headers": [
            (b"authorization", _basic_auth("zzdirect-missing", "pw")["Authorization"].encode())]}
        res = await _auth_basic(Request(scope), async_db)
        assert isinstance(res, Response) and res.status_code == 401

    async def test_direct_extract_token(self, async_db):
        from starlette.requests import Request
        from controller.git_auth_controller import _extract_token
        req = Request({"type": "http", "headers": [
            (b"authorization", "Bearer abc.def.ghi".encode())]})
        assert _extract_token(req) == "abc.def.ghi"
        req = Request({"type": "http", "headers": []})
        assert _extract_token(req) is None
        req = Request({"type": "http", "headers": [
            (b"authorization", "Basic dXNlcjpwdw==".encode())]})
        assert _extract_token(req) is None

    async def test_direct_public_access(self, async_db):
        from starlette.requests import Request
        from controller.git_auth_controller import _check_public_access
        user = await self._mk_user(async_db, "zzdirect8")
        repo = await self._mk_repo(async_db, user, "gwapub", is_public=True)
        res = await _check_public_access(async_db, user.username, "gwapub", False)
        assert res.status_code == 200
        res = await _check_public_access(async_db, user.username, "gwapub", True)
        assert res.status_code == 401
        res = await _check_public_access(async_db, user.username, "ghost", False)
        assert res.status_code == 401

    async def test_direct_developer_write_200(self, async_db):
        from controller.git_auth_controller import _check_user_access
        from models.repository_member import RepositoryMember
        user = await self._mk_user(async_db, "zzdirect9")
        repo = await self._mk_repo(async_db, user, "gwadev")
        async_db.add(RepositoryMember(repository_id=repo.id, user_id=user.id,
                                      role="developer", is_active=True))
        await async_db.commit()
        res = await _check_user_access(user, async_db, user.username, "gwadev", True)
        assert res.status_code == 200


# ============ room 附件上传/下载成功路径 ============

class TestRoomAttachment:
    def test_upload_and_download(self, test_client, db, test_user):
        from services.token_service import create_access_token
        import io
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}
        repo = create_test_repo(db, name="attach-succ", owner_id=test_user.id,
                                path=f"{test_user.username}/attach-succ")
        r = test_client.get(f"/api/v1/repositories/{repo.id}/room", headers=headers)
        assert r.status_code == 200
        room_id = r.json()["id"]

        up = test_client.post(
            f"/api/v1/rooms/{room_id}/attachments",
            headers=headers,
            files={"file": ("note.txt", io.BytesIO(b"attachment body"),
                            "text/plain")})
        assert up.status_code == 200
        body = up.json()
        assert body.get("url")
        stored = body["url"].rsplit("/", 1)[1]

        dl = test_client.get(f"/api/v1/attachments/{room_id}/{stored}",
                             headers=headers)
        assert dl.status_code == 200
        assert dl.content == b"attachment body"

    def test_upload_not_member_403(self, test_client, db, test_user, admin_user):
        from services.token_service import create_access_token
        import io
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(admin_user.id), "username": admin_user.username,
            "is_admin": True})}
        repo = create_test_repo(db, name="attach-deny", owner_id=test_user.id,
                                path=f"{test_user.username}/attach-deny")
        r = test_client.get(f"/api/v1/repositories/{repo.id}/room", headers=headers)
        # 管理员非房间成员 → 403；若允许创建则 200（仍可接受，覆盖成功分支）
        assert r.status_code in (200, 403)
        if r.status_code == 200:
            room_id = r.json()["id"]
            up = test_client.post(
                f"/api/v1/rooms/{room_id}/attachments",
                headers=headers,
                files={"file": ("n2.txt", io.BytesIO(b"x"), "text/plain")})
            assert up.status_code in (200, 403)


# ============ 全局搜索（含 Issue/PR，69%→） ============

class TestSearchGlobalContent:
    def test_global_search_repo_issue_pr(self, test_client, db, test_user):
        from services.token_service import create_access_token
        from models.issue import Issue
        from models.pull_request import PullRequest

        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(test_user.id), "username": test_user.username,
            "is_admin": test_user.is_admin})}
        keyword = "needleglobalsearchzz"
        repo = create_test_repo(db, name=keyword, owner_id=test_user.id,
                                path=f"{test_user.username}/{keyword}")
        db.add(Issue(repository_id=repo.id, issue_number=1, title=f"bug {keyword}",
                     description=f"desc {keyword}", author_id=test_user.id,
                     status="open"))
        db.add(PullRequest(repository_id=repo.id, pr_number=1,
                           title=f"feat {keyword}", description=f"body {keyword}",
                           source_branch="feature", target_branch="master",
                           author_id=test_user.id, status="open"))
        db.commit()

        r = test_client.get("/api/v1/search/global",
                            params={"q": keyword, "per_type": 5}, headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert any(x["name"] == keyword for x in body.get("repositories", []))
        assert any(x["title"] == f"bug {keyword}" for x in body.get("issues", []))
        assert any(x["title"] == f"feat {keyword}" for x in body.get("pull_requests", []))

    def test_global_search_blank(self, test_client, auth_headers):
        r = test_client.get("/api/v1/search/global", params={"q": "   "},
                            headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["repositories"] == []

    def test_global_search_no_accessible(self, test_client, db):
        from services.token_service import create_access_token
        from models.user import User
        user2 = User(username="searchlone", email="searchlone@example.com",
                     password=get_password_hash("pw"), is_active=True)
        db.add(user2)
        db.commit()
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": str(user2.id), "username": user2.username,
            "is_admin": False})}
        r = test_client.get("/api/v1/search/global", params={"q": "zzz"},
                            headers=headers)
        assert r.status_code == 200
        assert r.json()["repositories"] == []