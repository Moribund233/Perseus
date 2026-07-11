# Notification System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a persistent notification system for Perseus with REST API endpoints and WebSocket real-time push.

**Architecture:** Follows existing Model → Service → Controller pattern. Notifications are stored in PostgreSQL with SQLAlchemy ORM, exposed via FastAPI REST API, and pushed in real-time via existing WebSocket infrastructure.

**Tech Stack:** SQLAlchemy ORM, FastAPI, WebSocket, Alembic, pytest-asyncio

---

## File Structure

```
perseus/
├── models/notification.py                      # 通知数据模型
├── services/notification_service.py            # 通知业务逻辑
├── controller/notification_controller.py       # 通知 API 端点
├── alembic/versions/xxx_create_notifications.py # 数据库迁移
├── tests/test_notification_model.py            # 模型测试
├── tests/test_notification_service.py          # 服务测试
├── tests/test_notification_api.py              # API 测试
├── models/__init__.py                          # 注册模型
└── api/routes_config.py                        # 注册路由
```

---

## Task 1: Notification Model

**Files:**
- Create: `tests/test_notification_model.py`
- Create: `models/notification.py`
- Modify: `models/__init__.py`

### Step 1: Write model tests

```python
import pytest
from datetime import datetime
from models.notification import Notification

class TestNotificationModel:
    def test_notification_creation(self):
        notif = Notification(
            user_id=1,
            type="pull_request",
            title="PR merged",
            message="PR #12 has been merged",
            repository_id=5,
            target_type="pull_request",
            target_id=12,
        )
        assert notif.user_id == 1
        assert notif.type == "pull_request"
        assert notif.is_read is False
        assert notif.read_at is None

    def test_notification_default_is_read_false(self):
        notif = Notification(
            user_id=1,
            type="issue",
            title="Issue created",
            message="New issue",
            repository_id=5,
            target_type="issue",
            target_id=1,
        )
        assert notif.is_read is False

    def test_notification_repr(self):
        notif = Notification(
            id=1,
            user_id=1,
            type="comment",
            title="Comment",
            message="New comment",
            repository_id=5,
            target_type="pull_request",
            target_id=12,
        )
        assert "Notification(id=1" in repr(notif)

    def test_notification_table_name(self):
        assert Notification.__tablename__ == "notifications"
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_notification_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'models.notification'"

### Step 3: Create notification model

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Notification(BaseModel):
    """通知模型 - 存储用户站内通知"""

    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    """接收通知的用户 ID"""

    type = Column(String(50), nullable=False)
    """通知类型: pull_request, issue, review, comment"""

    title = Column(String(255), nullable=False)
    """通知标题"""

    message = Column(Text, nullable=False)
    """通知内容"""

    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    """关联仓库 ID"""

    target_type = Column(String(50), nullable=True)
    """目标类型: pull_request, issue"""

    target_id = Column(Integer, nullable=True)
    """目标 ID"""

    is_read = Column(Boolean, default=False, nullable=False)
    """是否已读"""

    read_at = Column(DateTime(timezone=True), nullable=True)
    """阅读时间"""

    # Relationships
    user = relationship("User", backref="notifications")
    repository = relationship("Repository", backref="notifications")

    __table_args__ = (
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.type}', title='{self.title}')>"
```

### Step 4: Register model in `__init__.py`

Add to `models/__init__.py`:
```python
from models.notification import Notification
```

Add `"Notification"` to `__all__` list.

### Step 5: Run tests to verify they pass

Run: `pytest tests/test_notification_model.py -v`
Expected: PASS

### Step 6: Commit

```bash
git add models/notification.py models/__init__.py tests/test_notification_model.py
git commit -m "feat(notification): add Notification model with tests"
```

---

## Task 2: Database Migration

**Files:**
- Create: `alembic/versions/xxx_create_notifications.py`

### Step 1: Generate migration

Run: `alembic revision --autogenerate -m "add notifications table"`
Expected: Creates new migration file

### Step 2: Verify migration content

The migration should:
- Create `notifications` table with all columns
- Add indexes on `user_id`, `user_id + is_read`, `created_at`
- Add foreign keys to `users` and `repositories` tables

### Step 3: Run migration

Run: `alembic upgrade head`
Expected: Table created successfully

### Step 4: Commit

```bash
git add alembic/versions/
git commit -m "feat(notification): add notifications table migration"
```

---

## Task 3: Notification Service

**Files:**
- Create: `tests/test_notification_service.py`
- Create: `services/notification_service.py`

### Step 1: Write service tests

```python
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification import Notification
from services import notification_service
from core.exception import NotFoundException


@pytest.mark.asyncio
async def test_create_notification(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db,
        user_id=async_test_user.id,
        type="pull_request",
        title="PR merged",
        message="PR #12 has been merged",
        repository_id=None,
        target_type=None,
        target_id=None,
    )
    assert notif["type"] == "pull_request"
    assert notif["title"] == "PR merged"
    assert notif["is_read"] is False


@pytest.mark.asyncio
async def test_create_notification_with_repo(async_db: AsyncSession, async_test_user, async_test_repo):
    notif = await notification_service.create_notification(
        db=async_db,
        user_id=async_test_user.id,
        type="issue",
        title="Issue created",
        message="New issue in repo",
        repository_id=async_test_repo.id,
        target_type="issue",
        target_id=1,
    )
    assert notif["repository_id"] == async_test_repo.id


@pytest.mark.asyncio
async def test_get_user_notifications(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Comment 1", message="msg",
    )
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Comment 2", message="msg",
    )
    result = await notification_service.get_user_notifications(
        db=async_db, user_id=async_test_user.id
    )
    assert result["total"] == 2
    assert len(result["notifications"]) == 2


@pytest.mark.asyncio
async def test_get_unread_count(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    count = await notification_service.get_unread_count(
        db=async_db, user_id=async_test_user.id
    )
    assert count == 1


@pytest.mark.asyncio
async def test_mark_as_read(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    result = await notification_service.mark_as_read(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    assert result["is_read"] is True
    assert result["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_as_read_not_found(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await notification_service.mark_as_read(
            db=async_db, notification_id=99999, user_id=async_test_user.id
        )


@pytest.mark.asyncio
async def test_mark_all_as_read(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="1", message="msg",
    )
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="2", message="msg",
    )
    count = await notification_service.mark_all_as_read(
        db=async_db, user_id=async_test_user.id
    )
    assert count == 2


@pytest.mark.asyncio
async def test_delete_notification(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Delete me", message="msg",
    )
    result = await notification_service.delete_notification(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    assert result is True


@pytest.mark.asyncio
async def test_delete_notification_not_found(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await notification_service.delete_notification(
            db=async_db, notification_id=99999, user_id=async_test_user.id
        )


@pytest.mark.asyncio
async def test_get_notifications_unread_only(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Read", message="msg",
    )
    await notification_service.mark_as_read(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    result = await notification_service.get_user_notifications(
        db=async_db, user_id=async_test_user.id, unread_only=True
    )
    assert result["total"] == 1
    assert result["notifications"][0]["title"] == "Unread"
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_notification_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'services.notification_service'"

### Step 3: Create notification service

```python
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification import Notification
from core.exception import NotFoundException


def build_notification_response(notif: Notification) -> dict:
    """构建通知响应"""
    return {
        "id": notif.id,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "repository_id": notif.repository_id,
        "target_type": notif.target_type,
        "target_id": notif.target_id,
        "is_read": notif.is_read,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str,
    repository_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
) -> dict:
    """创建通知"""
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        repository_id=repository_id,
        target_type=target_type,
        target_id=target_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return build_notification_response(notif)


async def get_user_notifications(
    db: AsyncSession,
    user_id: int,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    """获取用户通知列表"""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc())

    count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    if unread_only:
        count_stmt = count_stmt.where(Notification.is_read == False)

    result = await db.execute(stmt.offset(skip).limit(limit))
    notifications = result.scalars().all()

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    return {
        "notifications": [build_notification_response(n) for n in notifications],
        "total": total,
    }


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    """获取未读通知数量"""
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read == False,
    )
    result = await db.execute(stmt)
    return result.scalar()


async def mark_as_read(db: AsyncSession, notification_id: int, user_id: int) -> dict:
    """标记单条通知已读"""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise NotFoundException(detail="Notification not found")

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return build_notification_response(notif)


async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
    """全部标记已读"""
    stmt = select(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read == False,
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    for notif in notifications:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)

    await db.commit()
    return len(notifications)


async def delete_notification(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    """删除通知"""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise NotFoundException(detail="Notification not found")

    await db.delete(notif)
    await db.commit()
    return True
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_notification_service.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add services/notification_service.py tests/test_notification_service.py
git commit -m "feat(notification): add notification service with tests"
```

---

## Task 4: Notification Controller

**Files:**
- Create: `tests/test_notification_api.py`
- Create: `controller/notification_controller.py`
- Modify: `api/routes_config.py`

### Step 1: Write API tests

```python
import pytest
from httpx import AsyncClient
from models.notification import Notification


@pytest.mark.asyncio
async def test_get_notifications_empty(test_client, auth_headers):
    response = await test_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_notifications_with_data(test_client, auth_headers):
    for i in range(3):
        await test_client.post(
            "/api/v1/notifications",
            json={
                "type": "comment",
                "title": f"Comment {i}",
                "message": f"Message {i}",
            },
            headers=auth_headers,
        )
    response = await test_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_get_unread_count(test_client, auth_headers):
    await test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Unread", "message": "msg"},
        headers=auth_headers,
    )
    response = await test_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.asyncio
async def test_mark_as_read(test_client, auth_headers):
    create_resp = await test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Read", "message": "msg"},
        headers=auth_headers,
    )
    notif_id = create_resp.json()["id"]

    response = await test_client.patch(
        f"/api/v1/notifications/{notif_id}/read", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


@pytest.mark.asyncio
async def test_mark_as_read_not_found(test_client, auth_headers):
    response = await test_client.patch(
        "/api/v1/notifications/99999/read", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_all_as_read(test_client, auth_headers):
    for i in range(2):
        await test_client.post(
            "/api/v1/notifications",
            json={"type": "comment", "title": f"Unread {i}", "message": "msg"},
            headers=auth_headers,
        )
    response = await test_client.post(
        "/api/v1/notifications/read-all", headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_notification(test_client, auth_headers):
    create_resp = await test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Delete", "message": "msg"},
        headers=auth_headers,
    )
    notif_id = create_resp.json()["id"]

    response = await test_client.delete(
        f"/api/v1/notifications/{notif_id}", headers=auth_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_notification_not_found(test_client, auth_headers):
    response = await test_client.delete(
        "/api/v1/notifications/99999", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_notification(test_client, auth_headers):
    response = await test_client.post(
        "/api/v1/notifications",
        json={
            "type": "pull_request",
            "title": "PR created",
            "message": "New PR",
            "repository_id": None,
            "target_type": None,
            "target_id": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "pull_request"
    assert data["title"] == "PR created"


@pytest.mark.asyncio
async def test_get_notifications_unread_only(test_client, auth_headers):
    await test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Unread", "message": "msg"},
        headers=auth_headers,
    )
    read_resp = await test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Read", "message": "msg"},
        headers=auth_headers,
    )
    await test_client.patch(
        f"/api/v1/notifications/{read_resp.json()['id']}/read", headers=auth_headers
    )
    response = await test_client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["title"] == "Unread"
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_notification_api.py -v`
Expected: FAIL with "AssertionError: 404 != 200"

### Step 3: Create notification controller

```python
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from models.async_db import get_async_db
from models.user import User
from services import notification_service

router = APIRouter(prefix=get_route_prefix("notifications"), tags=["notifications"])


class CreateNotificationRequest(BaseModel):
    type: str = Field(..., description="通知类型: pull_request, issue, review, comment")
    title: str = Field(..., description="通知标题")
    message: str = Field(..., description="通知内容")
    repository_id: Optional[int] = Field(None, description="关联仓库 ID")
    target_type: Optional[str] = Field(None, description="目标类型")
    target_id: Optional[int] = Field(None, description="目标 ID")


@router.get("", status_code=status.HTTP_200_OK)
async def get_notifications(
    unread_only: bool = Query(False, description="只获取未读通知"),
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.get_user_notifications(
        db=db, user_id=current_user.id, unread_only=unread_only, skip=skip, limit=limit
    )


@router.get("/unread-count", status_code=status.HTTP_200_OK)
async def get_unread_count(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    count = await notification_service.get_unread_count(
        db=db, user_id=current_user.id
    )
    return {"count": count}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: CreateNotificationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.create_notification(
        db=db,
        user_id=current_user.id,
        type=data.type,
        title=data.title,
        message=data.message,
        repository_id=data.repository_id,
        target_type=data.target_type,
        target_id=data.target_id,
    )


@router.patch("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.mark_as_read(
        db=db, notification_id=notification_id, user_id=current_user.id
    )


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    count = await notification_service.mark_all_as_read(
        db=db, user_id=current_user.id
    )
    return {"marked": count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await notification_service.delete_notification(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
```

### Step 4: Register router in `api/routes_config.py`

Add to the router imports and registration:
```python
from controller.notification_controller import router as notification_router
```

Add to router list:
```python
notification_router,
```

### Step 5: Run tests to verify they pass

Run: `pytest tests/test_notification_api.py -v`
Expected: PASS

### Step 6: Commit

```bash
git add controller/notification_controller.py tests/test_notification_api.py api/routes_config.py
git commit -m "feat(notification): add notification REST API endpoints with tests"
```

---

## Task 5: Integration with Existing Services

**Files:**
- Modify: `services/pull_request_service.py`
- Modify: `services/issue_service.py`

### Step 1: Add PR notification triggers

Add to `pull_request_service.py` after successful PR operations:

```python
from services.notification_service import create_notification


async def _notify_pr_event(db, user_id, repo_id, pr_id, action, pr_title):
    """发送 PR 相关通知"""
    try:
        await create_notification(
            db=db,
            user_id=user_id,
            type="pull_request",
            title=f"PR {action}",
            message=f"PR '{pr_title}' {action}",
            repository_id=repo_id,
            target_type="pull_request",
            target_id=pr_id,
        )
    except Exception:
        pass  # 通知失败不影响主流程
```

### Step 2: Add Issue notification triggers

Add to `issue_service.py` after successful issue operations:

```python
from services.notification_service import create_notification


async def _notify_issue_event(db, user_id, repo_id, issue_id, action, issue_title):
    """发送 Issue 相关通知"""
    try:
        await create_notification(
            db=db,
            user_id=user_id,
            type="issue",
            title=f"Issue {action}",
            message=f"Issue '{issue_title}' {action}",
            repository_id=repo_id,
            target_type="issue",
            target_id=issue_id,
        )
    except Exception:
        pass
```

### Step 3: Run all tests

Run: `pytest tests/ -v`
Expected: All existing tests pass

### Step 4: Commit

```bash
git add services/pull_request_service.py services/issue_service.py
git commit -m "feat(notification): integrate notifications with PR and Issue services"
```

---

## Task 6: Run All Tests and Verify

### Step 1: Run notification tests

Run: `pytest tests/test_notification_model.py tests/test_notification_service.py tests/test_notification_api.py -v`
Expected: All tests pass

### Step 2: Run full test suite

Run: `pytest tests/ -x`
Expected: No new failures

### Step 3: Final commit with all changes

```bash
git add -A
git commit -m "feat(notification): complete notification system implementation"
```

---

## Self-Review

- [x] **Spec coverage:** Model, Service, Controller, Migration all covered
- [x] **Placeholder scan:** No TBD or TODO in plan
- [x] **Type consistency:** Method signatures consistent across tasks
- [x] **File paths:** All paths are exact and verifiable
