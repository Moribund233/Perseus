"""
Issue 控制器层

处理 Issue 相关的 HTTP 请求
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models.db import get_db
from models.user import User
from api.dependencies import get_current_user
from services.issue_service import (
    list_issues as service_list_issues,
    get_issue as service_get_issue,
    create_issue as service_create_issue,
    update_issue as service_update_issue,
    close_issue as service_close_issue,
    reopen_issue as service_reopen_issue,
    create_issue_comment as service_create_issue_comment,
    list_issue_comments as service_list_issue_comments,
    list_labels as service_list_labels,
    create_label as service_create_label,
    update_label as service_update_label,
    delete_label as service_delete_label,
)

# 创建路由实例
router = APIRouter(tags=["issues"])


class IssueCreateRequest(BaseModel):
    """创建 Issue 请求体"""
    title: str = Field(..., min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="描述")
    priority: str = Field(default="medium", description="优先级：low/medium/high/critical")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    label_ids: Optional[List[int]] = Field(None, description="标签ID列表")


class IssueUpdateRequest(BaseModel):
    """更新 Issue 请求体"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="描述")
    priority: Optional[str] = Field(None, description="优先级：low/medium/high/critical")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    label_ids: Optional[List[int]] = Field(None, description="标签ID列表")


class IssueCommentCreateRequest(BaseModel):
    """创建 Issue 评论请求体"""
    content: str = Field(..., min_length=1, description="评论内容")


class LabelCreateRequest(BaseModel):
    """创建标签请求体"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="标签颜色（十六进制）")
    description: Optional[str] = Field(None, max_length=255, description="标签描述")


class LabelUpdateRequest(BaseModel):
    """更新标签请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="标签名称")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="标签颜色（十六进制）")
    description: Optional[str] = Field(None, max_length=255, description="标签描述")


@router.get("/api/repositories/{repo_id}/issues")
async def list_issues(
    repo_id: int,
    status: Optional[str] = Query(None, description="状态筛选：open/closed"),
    label: Optional[str] = Query(None, description="标签名称筛选"),
    assignee: Optional[int] = Query(None, description="指派人ID筛选"),
    author: Optional[int] = Query(None, description="作者ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取 Issue 列表
    
    Args:
        repo_id: 仓库ID
        status: 状态筛选
        label: 标签名称筛选
        assignee: 指派人ID筛选
        author: 作者ID筛选
        page: 页码
        limit: 每页数量
        db: 数据库会话
    
    Returns:
        dict: Issue 列表和分页信息
    """
    return await service_list_issues(
        db=db,
        repository_id=repo_id,
        status=status,
        label=label,
        assignee_id=assignee,
        author_id=author,
        page=page,
        limit=limit
    )


@router.post("/api/repositories/{repo_id}/issues")
async def create_issue(
    repo_id: int,
    data: IssueCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 Issue

    Args:
        repo_id: 仓库ID
        data: Issue 创建数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的 Issue 数据
    """
    return await service_create_issue(
        db=db,
        repository_id=repo_id,
        author_id=current_user.id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assignee_id=data.assignee_id,
        label_ids=data.label_ids
    )


@router.get("/api/repositories/{repo_id}/issues/{issue_number}")
async def get_issue(
    repo_id: int,
    issue_number: int,
    db: Session = Depends(get_db)
):
    """
    获取 Issue 详情
    
    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        db: 数据库会话
    
    Returns:
        dict: Issue 详情（包含评论）
    """
    return await service_get_issue(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number,
        include_details=True
    )


@router.patch("/api/repositories/{repo_id}/issues/{issue_number}")
async def update_issue(
    repo_id: int,
    issue_number: int,
    data: IssueUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新 Issue

    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        data: 更新数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 Issue 数据
    """
    return await service_update_issue(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assignee_id=data.assignee_id,
        label_ids=data.label_ids
    )


@router.post("/api/repositories/{repo_id}/issues/{issue_number}/close")
async def close_issue(
    repo_id: int,
    issue_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    关闭 Issue

    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 Issue 数据
    """
    return await service_close_issue(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number,
        user_id=current_user.id
    )


@router.post("/api/repositories/{repo_id}/issues/{issue_number}/reopen")
async def reopen_issue(
    repo_id: int,
    issue_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重新打开 Issue

    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 Issue 数据
    """
    return await service_reopen_issue(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number,
        user_id=current_user.id
    )


# ==================== Issue 评论 ====================

@router.get("/api/repositories/{repo_id}/issues/{issue_number}/comments")
async def list_issue_comments(
    repo_id: int,
    issue_number: int,
    db: Session = Depends(get_db)
):
    """
    获取 Issue 评论列表
    
    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        db: 数据库会话
    
    Returns:
        list: 评论列表
    """
    return await service_list_issue_comments(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number
    )


@router.post("/api/repositories/{repo_id}/issues/{issue_number}/comments")
async def create_issue_comment(
    repo_id: int,
    issue_number: int,
    data: IssueCommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 Issue 评论

    Args:
        repo_id: 仓库ID
        issue_number: Issue 编号
        data: 评论数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的评论数据
    """
    return await service_create_issue_comment(
        db=db,
        repository_id=repo_id,
        issue_number=issue_number,
        author_id=current_user.id,
        content=data.content
    )


# ==================== Label 管理 ====================

@router.get("/api/repositories/{repo_id}/labels")
async def list_labels(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    获取仓库标签列表
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        list: 标签列表
    """
    return await service_list_labels(
        db=db,
        repository_id=repo_id
    )


@router.post("/api/repositories/{repo_id}/labels")
async def create_label(
    repo_id: int,
    data: LabelCreateRequest,
    db: Session = Depends(get_db)
):
    """
    创建标签
    
    Args:
        repo_id: 仓库ID
        data: 标签数据
        db: 数据库会话
    
    Returns:
        dict: 创建的标签数据
    """
    return await service_create_label(
        db=db,
        repository_id=repo_id,
        name=data.name,
        color=data.color,
        description=data.description
    )


@router.patch("/api/repositories/{repo_id}/labels/{label_id}")
async def update_label(
    repo_id: int,
    label_id: int,
    data: LabelUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    更新标签
    
    Args:
        repo_id: 仓库ID
        label_id: 标签ID
        data: 更新数据
        db: 数据库会话
    
    Returns:
        dict: 更新后的标签数据
    """
    return await service_update_label(
        db=db,
        repository_id=repo_id,
        label_id=label_id,
        name=data.name,
        color=data.color,
        description=data.description
    )


@router.delete("/api/repositories/{repo_id}/labels/{label_id}")
async def delete_label(
    repo_id: int,
    label_id: int,
    db: Session = Depends(get_db)
):
    """
    删除标签
    
    Args:
        repo_id: 仓库ID
        label_id: 标签ID
        db: 数据库会话
    
    Returns:
        dict: 操作结果
    """
    await service_delete_label(
        db=db,
        repository_id=repo_id,
        label_id=label_id
    )
    return {"message": "Label deleted successfully"}
