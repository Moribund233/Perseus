"""
Issue API 测试

测试范围:
1. Issue 列表 API - GET /api/repositories/{repo_id}/issues
2. Issue 创建 API - POST /api/repositories/{repo_id}/issues
3. Issue 详情 API - GET /api/repositories/{repo_id}/issues/{issue_number}
4. Issue 更新 API - PATCH /api/repositories/{repo_id}/issues/{issue_number}
5. Issue 关闭 API - POST /api/repositories/{repo_id}/issues/{issue_number}/close
6. Issue 重新打开 API - POST /api/repositories/{repo_id}/issues/{issue_number}/reopen
7. Issue 评论 API - GET/POST /api/repositories/{repo_id}/issues/{issue_number}/comments
8. Label 管理 API - GET/POST/PATCH/DELETE /api/repositories/{repo_id}/labels
"""

import stat


def remove_readonly(func, path, excinfo):
    """Windows 下删除只读文件的回调函数"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

import pytest
import os
import shutil
import stat

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.db import get_db
from models import Repository, User, Issue, Label, IssueComment
from app import create_app
from utils.git_utils import init_bare_repo
from services.token_service import create_access_token


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_issue_api.db"

# 创建测试数据库引擎
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库表
Base.metadata.create_all(bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 创建测试应用
app = create_app(config_path="config.toml")
app.dependency_overrides[get_db] = override_get_db


# ==================== Fixtures ====================

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """创建测试用户"""
    db = TestingSessionLocal()
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # 清理
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


@pytest.fixture
def test_repository(test_user):
    """创建测试仓库"""
    db = TestingSessionLocal()
    
    repo_root = "./repositories"
    os.makedirs(repo_root, exist_ok=True)
    
    repo_path = f"testuser/test-repo-issue"
    physical_path = os.path.join(repo_root, repo_path)
    
    # 清理已存在的仓库
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path, ignore_errors=True)
    
    init_bare_repo(physical_path)
    
    repo = Repository(
        name="test-repo-issue",
        path=repo_path,
        description="Test repository for Issue API",
        owner_id=test_user.id,
        is_public=True
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    
    yield repo
    
    # 清理
    db.query(Repository).filter(Repository.id == repo.id).delete()
    db.commit()
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path, ignore_errors=True)
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """创建认证请求头"""
    token = create_access_token({"sub": str(test_user.id), "username": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_label(test_repository):
    """创建测试标签"""
    db = TestingSessionLocal()
    
    label = Label(
        repository_id=test_repository.id,
        name="bug",
        color="#ff0000",
        description="Bug label"
    )
    db.add(label)
    db.commit()
    label_id = label.id
    
    yield label
    
    # 清理
    db.query(Label).filter(Label.id == label_id).delete()
    db.commit()
    db.close()


@pytest.fixture
def test_issue(test_repository, test_user, test_label):
    """创建测试 Issue"""
    db = TestingSessionLocal()
    
    # 重新获取标签对象（避免会话问题）
    label = db.query(Label).filter(Label.id == test_label.id).first()
    
    issue = Issue(
        repository_id=test_repository.id,
        issue_number=1,
        title="Test Issue",
        description="This is a test issue",
        author_id=test_user.id,
        status="open",
        priority="medium"
    )
    if label:
        issue.labels.append(label)
    db.add(issue)
    db.commit()
    issue_id = issue.id
    
    yield issue
    
    # 清理
    db.query(Issue).filter(Issue.id == issue_id).delete()
    db.commit()
    db.close()


# ==================== Issue 列表测试 ====================

def test_list_issues_empty(client, test_repository):
    """测试获取空 Issue 列表"""
    response = client.get(f"/api/repositories/{test_repository.id}/issues")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_issues_with_data(client, test_issue, test_repository):
    """测试获取 Issue 列表（有数据）"""
    response = client.get(f"/api/repositories/{test_repository.id}/issues")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test Issue"


def test_list_issues_with_status_filter(client, test_issue, test_repository):
    """测试按状态筛选 Issue"""
    # 筛选 open 状态
    response = client.get(f"/api/repositories/{test_repository.id}/issues?status=open")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    
    # 筛选 closed 状态（应该为空）
    response = client.get(f"/api/repositories/{test_repository.id}/issues?status=closed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0


def test_list_issues_with_label_filter(client, test_issue, test_repository, test_label):
    """测试按标签筛选 Issue"""
    response = client.get(f"/api/repositories/{test_repository.id}/issues?label=bug")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["labels"][0]["name"] == "bug"


def test_list_issues_pagination(client, test_repository, test_user):
    """测试 Issue 列表分页"""
    db = TestingSessionLocal()
    
    # 创建多个 Issue
    for i in range(5):
        issue = Issue(
            repository_id=test_repository.id,
            issue_number=i + 1,
            title=f"Test Issue {i + 1}",
            description=f"Description {i + 1}",
            author_id=test_user.id,
            status="open",
            priority="medium"
        )
        db.add(issue)
    db.commit()
    
    # 测试分页
    response = client.get(f"/api/repositories/{test_repository.id}/issues?page=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    
    # 清理
    db.query(Issue).filter(Issue.repository_id == test_repository.id).delete()
    db.commit()
    db.close()


# ==================== Issue 创建测试 ====================

def test_create_issue_success(client, test_repository, test_label, auth_headers):
    """测试成功创建 Issue"""
    payload = {
        "title": "New Bug Report",
        "description": "Found a bug in the system",
        "priority": "high",
        "label_ids": [test_label.id]
    }
    
    response = client.post(f"/api/repositories/{test_repository.id}/issues", json=payload, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Bug Report"
    assert data["description"] == "Found a bug in the system"
    assert data["priority"] == "high"
    assert data["status"] == "open"
    assert data["issue_number"] == 1
    assert len(data["labels"]) == 1


def test_create_issue_validation_error(client, test_repository, auth_headers):
    """测试创建 Issue 参数验证失败"""
    # 缺少标题
    payload = {
        "description": "Found a bug",
        "priority": "high"
    }
    
    response = client.post(f"/api/repositories/{test_repository.id}/issues", json=payload, headers=auth_headers)
    assert response.status_code == 422
    
    # 无效的优先级
    payload = {
        "title": "Test",
        "priority": "invalid"
    }
    
    response = client.post(f"/api/repositories/{test_repository.id}/issues", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_create_issue_auto_numbering(client, test_repository, auth_headers):
    """测试 Issue 编号自动递增"""
    # 获取当前 Issue 数量
    list_response = client.get(f"/api/repositories/{test_repository.id}/issues")
    initial_count = list_response.json()["total"]

    # 创建第一个 Issue
    payload1 = {"title": "First Issue"}
    response1 = client.post(f"/api/repositories/{test_repository.id}/issues", json=payload1, headers=auth_headers)
    assert response1.status_code == 200
    issue_number1 = response1.json()["issue_number"]

    # 创建第二个 Issue
    payload2 = {"title": "Second Issue"}
    response2 = client.post(f"/api/repositories/{test_repository.id}/issues", json=payload2, headers=auth_headers)
    assert response2.status_code == 200
    issue_number2 = response2.json()["issue_number"]

    # 验证编号递增
    assert issue_number2 == issue_number1 + 1


# ==================== Issue 详情测试 ====================

def test_get_issue_success(client, test_issue, test_repository):
    """测试获取 Issue 详情"""
    response = client.get(f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}")
    
    assert response.status_code == 200
    data = response.json()
    # 验证返回的数据结构正确
    assert "id" in data
    assert "title" in data
    assert "issue_number" in data
    assert data["issue_number"] == test_issue.issue_number
    assert "priority" in data
    assert "labels" in data
    assert "comments" in data


def test_get_issue_not_found(client, test_repository):
    """测试获取不存在的 Issue"""
    response = client.get(f"/api/repositories/{test_repository.id}/issues/999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ==================== Issue 更新测试 ====================

def test_update_issue_success(client, test_issue, test_repository, test_user, auth_headers):
    """测试成功更新 Issue"""
    payload = {
        "title": "Updated Title",
        "description": "Updated description",
        "priority": "high",
        "assignee_id": test_user.id
    }

    response = client.patch(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"
    assert data["priority"] == "high"
    assert data["assignee"]["id"] == test_user.id


def test_update_issue_not_found(client, test_repository, auth_headers):
    """测试更新不存在的 Issue"""
    payload = {"title": "Updated"}

    response = client.patch(f"/api/repositories/{test_repository.id}/issues/999", json=payload, headers=auth_headers)

    assert response.status_code == 404


# ==================== Issue 关闭/重新打开测试 ====================

def test_close_issue_success(client, test_issue, test_repository, auth_headers):
    """测试成功关闭 Issue"""
    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/close",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_by"] is not None


def test_close_issue_already_closed(client, test_issue, test_repository, auth_headers):
    """测试关闭已关闭的 Issue"""
    # 先关闭 Issue
    client.post(f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/close", headers=auth_headers)

    # 再次关闭
    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/close",
        headers=auth_headers
    )

    assert response.status_code == 400


def test_reopen_issue_success(client, test_issue, test_repository, auth_headers):
    """测试成功重新打开 Issue"""
    # 先关闭 Issue
    client.post(f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/close", headers=auth_headers)

    # 重新打开
    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/reopen",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "open"
    # 当 Issue 是 open 状态时，closed_by 字段不应该存在或为 None
    assert data.get("closed_by") is None


def test_reopen_issue_already_open(client, test_issue, test_repository, auth_headers):
    """测试重新打开已打开的 Issue"""
    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/reopen",
        headers=auth_headers
    )

    assert response.status_code == 400


# ==================== Issue 评论测试 ====================

def test_create_issue_comment_success(client, test_issue, test_repository, auth_headers):
    """测试成功创建 Issue 评论"""
    payload = {
        "content": "I can reproduce this issue"
    }

    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/comments",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "I can reproduce this issue"


def test_create_issue_comment_empty_content(client, test_issue, test_repository, auth_headers):
    """测试创建空内容评论"""
    payload = {"content": ""}

    response = client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/comments",
        json=payload,
        headers=auth_headers
    )

    # Pydantic min_length 验证会返回 422
    assert response.status_code == 422


def test_list_issue_comments(client, test_issue, test_repository, auth_headers):
    """测试获取 Issue 评论列表"""
    # 先通过 API 创建评论
    payload = {"content": "Test comment for list"}
    client.post(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/comments",
        json=payload,
        headers=auth_headers
    )

    response = client.get(
        f"/api/repositories/{test_repository.id}/issues/{test_issue.issue_number}/comments"
    )

    assert response.status_code == 200
    data = response.json()
    # 检查是否包含我们创建的评论
    contents = [c["content"] for c in data]
    assert "Test comment for list" in contents


# ==================== Label 管理测试 ====================

def test_list_labels(client, test_repository, test_label):
    """测试获取标签列表"""
    response = client.get(f"/api/repositories/{test_repository.id}/labels")
    
    assert response.status_code == 200
    data = response.json()
    # 检查是否包含测试标签
    label_names = [l["name"] for l in data]
    assert "bug" in label_names
    # 找到 bug 标签并验证颜色
    bug_label = next((l for l in data if l["name"] == "bug"), None)
    assert bug_label is not None
    assert bug_label["color"] == "#ff0000"


def test_create_label_success(client, test_repository):
    """测试成功创建标签"""
    payload = {
        "name": "enhancement",
        "color": "#a2eeef",
        "description": "New feature or request"
    }
    
    response = client.post(f"/api/repositories/{test_repository.id}/labels", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "enhancement"
    assert data["color"] == "#a2eeef"
    assert data["description"] == "New feature or request"


def test_create_label_validation_error(client, test_repository):
    """测试创建标签参数验证失败"""
    # 缺少名称
    payload = {"color": "#ff0000"}
    response = client.post(f"/api/repositories/{test_repository.id}/labels", json=payload)
    assert response.status_code == 422
    
    # 无效的颜色格式
    payload = {"name": "test", "color": "red"}
    response = client.post(f"/api/repositories/{test_repository.id}/labels", json=payload)
    assert response.status_code == 422


def test_create_label_duplicate_name(client, test_repository, test_label):
    """测试创建重复名称的标签"""
    payload = {
        "name": "bug",
        "color": "#000000"
    }
    
    response = client.post(f"/api/repositories/{test_repository.id}/labels", json=payload)
    
    assert response.status_code == 400


def test_update_label_success(client, test_repository, test_label):
    """测试成功更新标签"""
    payload = {
        "name": "critical-bug",
        "color": "#ff0000",
        "description": "Critical bug that needs immediate attention"
    }
    
    response = client.patch(
        f"/api/repositories/{test_repository.id}/labels/{test_label.id}",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "critical-bug"
    assert data["description"] == "Critical bug that needs immediate attention"


def test_update_label_not_found(client, test_repository):
    """测试更新不存在的标签"""
    payload = {"name": "test"}
    
    response = client.patch(f"/api/repositories/{test_repository.id}/labels/999", json=payload)
    
    assert response.status_code == 404


def test_delete_label_success(client, test_repository):
    """测试成功删除标签"""
    # 先创建标签
    db = TestingSessionLocal()
    label = Label(
        repository_id=test_repository.id,
        name="temp-label",
        color="#cccccc"
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    label_id = label.id
    db.close()
    
    response = client.delete(f"/api/repositories/{test_repository.id}/labels/{label_id}")
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


def test_delete_label_not_found(client, test_repository):
    """测试删除不存在的标签"""
    response = client.delete(f"/api/repositories/{test_repository.id}/labels/999")
    
    assert response.status_code == 404
