"""自动落盘草稿分支 (批次7) — TDD 红灯

todo docs/todos.md:110: 会话空闲 N 分钟自动 collab_save 到 `collab/draft-...`。
当前缺口:
  - `CollabSaveRequest` (collab_internal_controller.py:60-65) 只有 token/docKey/
    content/message/invite_token, 无 "draft" 语义;
  - `/collab/save` (196-247) 直接把内容 commit 到 docKey 原始 branch, 没有草稿分支通道。

绿灯契约 (本测试只断言 API 契约红线):
  - `POST /api/v1/collab/save` 带 `draft: true` 时, 将 docKey 的 branch 替换为
    `collab/draft-{branch}` 写入 (存量 commit_file 分支不存在即创建);
  - 响应返回 draft 分支名 (非触碰用户工作分支)。
"""
from unittest.mock import AsyncMock

import pytest

from controller.collab_internal_controller import (
    INTERNAL_SECRET_ENV,
    INTERNAL_SECRET_HEADER,
    make_doc_key,
)
from services.token_service import create_access_token
from tests.test_helpers import create_test_repo

SECRET = "test-internal-secret"


def _headers(secret=SECRET):
    return {INTERNAL_SECRET_HEADER: secret}


def _token_for(user):
    return create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
        }
    )


@pytest.fixture
def internal_env(monkeypatch):
    monkeypatch.setenv(INTERNAL_SECRET_ENV, SECRET)


class TestCollabAutosaveDraft:
    """自动落盘草稿分支 — 会话空闲自动保存到 collab/draft-*。"""

    def test_autosave_to_draft_branch(
        self, test_client, db, test_user, internal_env, monkeypatch
    ):
        """RED: 现在保存无 draft 通道, 直接落原始 branch。

        绿灯后: draft=True -> branch 变为 collab/draft-{branch}。
        """
        repo = create_test_repo(db, name="draft-repo", owner_id=test_user.id)
        mock = AsyncMock(
            return_value={
                "commit_id": "draft000",
                "branch": "collab/draft-main",
                "path": "src/app.py",
            }
        )
        monkeypatch.setattr("services.repository_browser_service.commit_file", mock)

        resp = test_client.post(
            "/api/v1/collab/save",
            json={
                "token": _token_for(test_user),
                "docKey": make_doc_key(str(repo.id), "main", "src/app.py"),
                "content": "draft content",
                "message": "autosave to draft",
                "draft": True,
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        # RED: 现在无 draft 选项 -> branch 仍是原始 main (无提交创建)
        assert data["commit_id"] == "draft000"
        assert data["branch"].startswith("collab/draft-")
        assert data["branch"] == "collab/draft-main"
        # 工作分支未被触碰: commit_file 收到的 branch 必须重写为草稿分支
        args, _ = mock.call_args
        assert args[1] == "collab/draft-main"