"""
行内评论锚定 — Service 层异步测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.repository import Repository
from services.file_comment_service import (
    create_file_comment,
    list_file_comments,
    set_file_comment_resolved,
    delete_file_comment,
)
from tests.test_helpers import async_create_test_repo
from core.exception import ValidationException, NotFoundException, AuthorizationException


@pytest.mark.asyncio
async def test_inline_comment_on_file(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    comment = await create_file_comment(
        async_db,
        repository_id=async_test_repo.id,
        author_id=async_test_user.id,
        content="请检查这段逻辑",
        file_path="src/app.py",
        line_number=42,
        branch="main",
    )
    assert comment["repository_id"] == async_test_repo.id
    assert comment["file_path"] == "src/app.py"
    assert comment["line_number"] == 42
    assert comment["branch"] == "main"
    assert comment["author_id"] == async_test_user.id
    assert comment["author_username"] == "async_testuser"
    assert comment["resolved"] is False
    assert comment["parent_id"] is None


@pytest.mark.asyncio
async def test_inline_comment_empty_content_rejected(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    with pytest.raises(ValidationException):
        await create_file_comment(
            async_db,
            repository_id=async_test_repo.id,
            author_id=async_test_user.id,
            content="   ",
            file_path="src/app.py",
        )


@pytest.mark.asyncio
async def test_inline_comment_empty_file_path_rejected(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    with pytest.raises(ValidationException):
        await create_file_comment(
            async_db,
            repository_id=async_test_repo.id,
            author_id=async_test_user.id,
            content="有内容",
            file_path="",
        )


@pytest.mark.asyncio
async def test_inline_comment_reply(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User
):
    parent = await create_file_comment(
        async_db,
        repository_id=async_test_repo.id,
        author_id=async_test_user.id,
        content="顶层评论",
        file_path="src/app.py",
        line_number=42,
    )
    reply = await create_file_comment(
        async_db,
        repository_id=async_test_repo.id,
        author_id=async_test_user2.id,
        content="已修复",
        file_path="src/app.py",
        parent_id=parent["id"],
    )
    assert reply["parent_id"] == parent["id"]

    comments = await list_file_comments(async_db, async_test_repo.id, async_test_user.id, file_path="src/app.py")
    assert len(comments) == 2


@pytest.mark.asyncio
async def test_inline_comment_reply_invalid_parent(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User
):
    import uuid
    with pytest.raises(ValidationException):
        await create_file_comment(
            async_db,
            repository_id=async_test_repo.id,
            author_id=async_test_user.id,
            content="回复",
            file_path="src/app.py",
            parent_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_list_inline_comments_filter_by_line(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "在 10 行", "src/app.py", line_number=10,
    )
    await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "在 20 行", "src/app.py", line_number=20,
    )

    comments = await list_file_comments(
        async_db, async_test_repo.id, async_test_user.id, file_path="src/app.py", line_number=10,
    )
    assert len(comments) == 1
    assert comments[0]["content"] == "在 10 行"


@pytest.mark.asyncio
async def test_resolve_comment_by_author(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    comment = await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "解决我", "src/app.ts",
    )
    resolved = await set_file_comment_resolved(
        async_db, async_test_repo.id, comment["id"], async_test_user.id, True,
    )
    assert resolved["resolved"] is True

    unresolved = await set_file_comment_resolved(
        async_db, async_test_repo.id, comment["id"], async_test_user.id, False,
    )
    assert unresolved["resolved"] is False


@pytest.mark.asyncio
async def test_resolve_comment_denied_for_outsider(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User
):
    comment = await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "仅作者可解决", "src/app.ts",
    )
    with pytest.raises(AuthorizationException):
        await set_file_comment_resolved(
            async_db, async_test_repo.id, comment["id"], async_another_user.id, True,
        )


@pytest.mark.asyncio
async def test_delete_comment_by_author(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    comment = await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "删除我", "src/app.ts",
    )
    ok = await delete_file_comment(async_db, async_test_repo.id, comment["id"], async_test_user.id)
    assert ok is True
    comments = await list_file_comments(async_db, async_test_repo.id, async_test_user.id)
    assert comments == []


@pytest.mark.asyncio
async def test_delete_comment_denied_for_outsider(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User
):
    comment = await create_file_comment(
        async_db, async_test_repo.id, async_test_user.id, "别删", "src/app.ts",
    )
    with pytest.raises(AuthorizationException):
        await delete_file_comment(async_db, async_test_repo.id, comment["id"], async_another_user.id)


@pytest.mark.asyncio
async def test_empty_list_returns_empty(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    comments = await list_file_comments(
        async_db, async_test_repo.id, async_test_user.id, file_path="missing.py",
    )
    assert comments == []


@pytest.mark.asyncio
async def test_private_repo_access_denied(
    async_db: AsyncSession, async_test_user: User, async_another_user: User
):
    private_repo = await async_create_test_repo(
        async_db, name="private-repo", owner_id=async_test_user.id, is_public=False,
    )
    with pytest.raises(ValidationException):
        await create_file_comment(
            async_db, private_repo.id, async_another_user.id, "闯入", "src/app.py",
        )
    with pytest.raises(ValidationException):
        await list_file_comments(async_db, private_repo.id, async_another_user.id)
    # 仓库负责人可正常评论
    comment = await create_file_comment(
        async_db, private_repo.id, async_test_user.id, "私有仓库评论", "src/app.py",
    )
    assert comment["repository_id"] == private_repo.id


@pytest.mark.asyncio
async def test_comment_on_missing_repo(
    async_db: AsyncSession, async_test_user: User
):
    import uuid
    with pytest.raises(NotFoundException):
        await create_file_comment(
            async_db, uuid.uuid4(), async_test_user.id, "仓库不存在", "src/app.py",
        )