import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def _get_or_create_user(db: Session):
    from models.user import User
    user = db.query(User).first()
    if user is None:
        user = User(
            username="autotest_user",
            email="autotest@example.com",
            password="hashed",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def _async_get_or_create_user(db: AsyncSession):
    from models.user import User
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username="async_autotest_user",
            email="async_autotest@example.com",
            password="hashed",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


def create_test_repo(
    db: Session,
    name: str = "test-repo",
    owner_id: Optional[uuid.UUID] = None,
    path: Optional[str] = None,
    is_public: bool = True,
) -> "Repository":
    from models.repository import Repository

    if owner_id is None:
        owner_id = _get_or_create_user(db).id

    if path is None:
        path = name

    repo = Repository(
        name=name,
        path=path,
        owner_id=owner_id,
        is_public=is_public,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


async def async_create_test_repo(
    db: AsyncSession,
    name: str = "async-test-repo",
    owner_id: Optional[uuid.UUID] = None,
    path: Optional[str] = None,
    is_public: bool = True,
) -> "Repository":
    from models.repository import Repository

    if owner_id is None:
        user = await _async_get_or_create_user(db)
        owner_id = user.id

    if path is None:
        path = name

    repo = Repository(
        name=name,
        path=path,
        owner_id=owner_id,
        is_public=is_public,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


def create_test_issue(
    db: Session,
    repo_id: uuid.UUID,
    issue_number: int,
    title: str,
    status: str = "open",
    priority: str = "medium",
    author_id: Optional[uuid.UUID] = None,
    assignee_id: Optional[uuid.UUID] = None,
    labels: Optional[list] = None,
) -> "Issue":
    from models.issue import Issue

    if author_id is None:
        author_id = _get_or_create_user(db).id

    issue = Issue(
        repository_id=repo_id,
        issue_number=issue_number,
        title=title,
        status=status,
        priority=priority,
        author_id=author_id,
        assignee_id=assignee_id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    if labels:
        from models.issue import issue_label_association
        for label in labels:
            db.execute(
                issue_label_association.insert().values(
                    issue_id=issue.id, label_id=label.id
                )
            )
        db.commit()

    return issue


async def async_create_test_issue(
    db: AsyncSession,
    repo_id: uuid.UUID,
    issue_number: int,
    title: str,
    status: str = "open",
    priority: str = "medium",
    author_id: Optional[uuid.UUID] = None,
    assignee_id: Optional[uuid.UUID] = None,
    labels: Optional[list] = None,
) -> "Issue":
    from models.issue import Issue, issue_label_association

    if author_id is None:
        user = await _async_get_or_create_user(db)
        author_id = user.id

    issue = Issue(
        repository_id=repo_id,
        issue_number=issue_number,
        title=title,
        status=status,
        priority=priority,
        author_id=author_id,
        assignee_id=assignee_id,
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    if labels:
        for label in labels:
            await db.execute(
                issue_label_association.insert().values(
                    issue_id=issue.id, label_id=label.id
                )
            )
        await db.commit()

    return issue


def create_test_pr(
    db: Session,
    repo_id: uuid.UUID,
    pr_number: int,
    title: str,
    status: str = "open",
    author_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
) -> "PullRequest":
    from models.pull_request import PullRequest

    if author_id is None:
        author_id = _get_or_create_user(db).id

    pr = PullRequest(
        repository_id=repo_id,
        pr_number=pr_number,
        title=title,
        description=description,
        source_branch="feature/test",
        target_branch="main",
        status=status,
        author_id=author_id,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


async def async_create_test_pr(
    db: AsyncSession,
    repo_id: uuid.UUID,
    pr_number: int,
    title: str,
    status: str = "open",
    author_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
) -> "PullRequest":
    from models.pull_request import PullRequest

    if author_id is None:
        user = await _async_get_or_create_user(db)
        author_id = user.id

    pr = PullRequest(
        repository_id=repo_id,
        pr_number=pr_number,
        title=title,
        description=description,
        source_branch="feature/test",
        target_branch="main",
        status=status,
        author_id=author_id,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)
    return pr


def create_test_label(
    db: Session,
    repo_id: uuid.UUID,
    name: str,
    color: str = "#ff0000",
) -> "Label":
    from models.issue import Label

    label = Label(
        repository_id=repo_id,
        name=name,
        color=color,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


async def async_create_test_label(
    db: AsyncSession,
    repo_id: uuid.UUID,
    name: str,
    color: str = "#ff0000",
) -> "Label":
    from models.issue import Label

    label = Label(
        repository_id=repo_id,
        name=name,
        color=color,
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label
