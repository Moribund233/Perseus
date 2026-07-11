from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from models.async_db import get_async_db
from models.user import User
from services import notification_service, notification_preference_service

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


@router.get("/preferences", status_code=status.HTTP_200_OK)
async def get_preferences(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_preference_service.get_or_create(
        db=db, user_id=current_user.id
    )


class UpdatePreferencesRequest(BaseModel):
    email_on_mention: Optional[bool] = None
    email_on_pr_review: Optional[bool] = None
    email_on_issue_comment: Optional[bool] = None
    email_on_pr_merge: Optional[bool] = None
    email_on_release: Optional[bool] = None
    in_app_on_mention: Optional[bool] = None
    in_app_on_pr_review: Optional[bool] = None
    in_app_on_issue_comment: Optional[bool] = None


@router.put("/preferences", status_code=status.HTTP_200_OK)
async def update_preferences(
    data: UpdatePreferencesRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    update_fields = data.model_dump(exclude_none=True)
    return await notification_preference_service.update_preferences(
        db=db, user_id=current_user.id, **update_fields
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await notification_service.delete_notification(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
