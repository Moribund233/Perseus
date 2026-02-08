"""
Pull Request API 测试

测试范围:
1. PR 列表 API - GET /api/repositories/{repo_id}/pull-requests
2. PR 创建 API - POST /api/repositories/{repo_id}/pull-requests
3. PR 详情 API - GET /api/repositories/{repo_id}/pull-requests/{pr_number}
4. PR 更新 API - PATCH /api/repositories/{repo_id}/pull-requests/{pr_number}
5. PR 关闭 API - POST /api/repositories/{repo_id}/pull-requests/{pr_number}/close
6. PR 合并 API - POST /api/repositories/{repo_id}/pull-requests/{pr_number}/merge
7. PR 评论 API - GET/POST /api/repositories/{repo_id}/pull-requests/{pr_number}/comments
8. PR 审查 API - POST /api/repositories/{repo_id}/pull-requests/{pr_number}/reviews
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
from models import Repository, User, PullRequest, PRComment, PRReview
from app import create_app
from client.utils.git_utils import init_bare_repo
from services.token_service import create_token_pair


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_pr_api.db"

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

@pytest.fixture(autouse=True)
def clean_database():
    """每个测试前清理数据库"""
    db = TestingSessionLocal()
    # 清理所有相关表
    db.query(PRReview).delete()
    db.query(PRComment).delete()
    db.query(PullRequest).delete()
    db.query(Repository).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    yield


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
def auth_headers(test_user):
    """创建认证请求头"""
    tokens = create_token_pair(test_user)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def test_repository(test_user):
    """创建测试仓库"""
    db = TestingSessionLocal()
    
    repo_root = "./repositories"
    os.makedirs(repo_root, exist_ok=True)
    
    repo_path = f"testuser/test-repo-pr"
    physical_path = os.path.join(repo_root, repo_path)
    
    # 清理已存在的仓库
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path, ignore_errors=True)
    
    init_bare_repo(physical_path)
    
    repo = Repository(
        name="test-repo-pr",
        path=repo_path,
        description="Test repository for PR API",
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
def test_pull_request(test_repository, test_user):
    """创建测试 PR"""
    db = TestingSessionLocal()
    
    pr = PullRequest(
        repository_id=test_repository.id,
        pr_number=1,
        title="Test PR",
        description="This is a test PR",
        source_branch="feature-branch",
        target_branch="master",
        author_id=test_user.id,
        status="open"
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    
    yield pr
    
    # 清理
    db.query(PullRequest).filter(PullRequest.id == pr.id).delete()
    db.commit()
    db.close()


# ==================== PR 列表测试 ====================

def test_list_pull_requests_empty(client, test_repository):
    """测试获取空 PR 列表"""
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_pull_requests_with_data(client, test_pull_request, test_repository):
    """测试获取 PR 列表（有数据）"""
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test PR"


def test_list_pull_requests_with_status_filter(client, test_pull_request, test_repository):
    """测试按状态筛选 PR"""
    # 筛选 open 状态
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests?status=open")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    
    # 筛选 closed 状态（应该为空）
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests?status=closed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0


def test_list_pull_requests_pagination(client, test_repository, test_user):
    """测试 PR 列表分页"""
    db = TestingSessionLocal()
    
    # 创建多个 PR
    for i in range(5):
        pr = PullRequest(
            repository_id=test_repository.id,
            pr_number=i + 1,
            title=f"Test PR {i + 1}",
            description=f"Description {i + 1}",
            source_branch=f"feature-{i + 1}",
            target_branch="master",
            author_id=test_user.id,
            status="open"
        )
        db.add(pr)
    db.commit()
    
    # 测试分页
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests?page=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    
    # 清理
    db.query(PullRequest).filter(PullRequest.repository_id == test_repository.id).delete()
    db.commit()
    db.close()


# ==================== PR 创建测试 ====================

def test_create_pull_request_success(client, test_repository, auth_headers):
    """测试成功创建 PR"""
    payload = {
        "title": "New Feature",
        "description": "Add new feature",
        "source_branch": "feature/new-feature",
        "target_branch": "master"
    }

    response = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Feature"
    assert data["description"] == "Add new feature"
    assert data["source_branch"] == "feature/new-feature"
    assert data["target_branch"] == "master"
    assert data["status"] == "open"
    assert data["pr_number"] == 1


def test_create_pull_request_unauthorized(client, test_repository):
    """测试未认证创建 PR"""
    payload = {
        "title": "New Feature",
        "source_branch": "feature/new-feature",
        "target_branch": "master"
    }

    response = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload)

    assert response.status_code == 403  # 未认证应该返回 403


def test_create_pull_request_validation_error(client, test_repository, auth_headers):
    """测试创建 PR 参数验证失败"""
    # 缺少标题
    payload = {
        "description": "Add new feature",
        "source_branch": "feature/new-feature",
        "target_branch": "master"
    }

    response = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload, headers=auth_headers)
    assert response.status_code == 422

    # 源分支和目标分支相同
    payload = {
        "title": "Test",
        "source_branch": "master",
        "target_branch": "master"
    }

    response = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_create_pull_request_auto_numbering(client, test_repository, auth_headers):
    """测试 PR 编号自动递增"""
    # 获取当前 PR 数量
    list_response = client.get(f"/api/repositories/{test_repository.id}/pull-requests")
    initial_count = list_response.json()["total"]

    # 创建第一个 PR
    payload1 = {
        "title": "First PR",
        "source_branch": "feature-1",
        "target_branch": "master"
    }
    response1 = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload1, headers=auth_headers)
    assert response1.status_code == 200
    pr_number1 = response1.json()["pr_number"]

    # 创建第二个 PR
    payload2 = {
        "title": "Second PR",
        "source_branch": "feature-2",
        "target_branch": "master"
    }
    response2 = client.post(f"/api/repositories/{test_repository.id}/pull-requests", json=payload2, headers=auth_headers)
    assert response2.status_code == 200
    pr_number2 = response2.json()["pr_number"]

    # 验证编号递增
    assert pr_number2 == pr_number1 + 1


# ==================== PR 详情测试 ====================

def test_get_pull_request_success(client, test_pull_request, test_repository):
    """测试获取 PR 详情"""
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}")
    
    assert response.status_code == 200
    data = response.json()
    # 验证返回的数据结构正确
    assert "id" in data
    assert "title" in data
    assert "pr_number" in data
    assert data["pr_number"] == test_pull_request.pr_number
    assert "comments" in data
    assert "reviews" in data


def test_get_pull_request_not_found(client, test_repository):
    """测试获取不存在的 PR"""
    response = client.get(f"/api/repositories/{test_repository.id}/pull-requests/999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ==================== PR 更新测试 ====================

def test_update_pull_request_success(client, test_pull_request, test_repository, auth_headers):
    """测试成功更新 PR"""
    payload = {
        "title": "Updated Title",
        "description": "Updated description"
    }

    response = client.patch(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"


def test_update_pull_request_not_found(client, test_repository, auth_headers):
    """测试更新不存在的 PR"""
    payload = {"title": "Updated"}

    response = client.patch(f"/api/repositories/{test_repository.id}/pull-requests/999", json=payload, headers=auth_headers)

    assert response.status_code == 404


# ==================== PR 关闭测试 ====================

def test_close_pull_request_success(client, test_pull_request, test_repository, auth_headers):
    """测试成功关闭 PR"""
    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/close",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"


def test_close_pull_request_already_closed(client, test_pull_request, test_repository, auth_headers):
    """测试关闭已关闭的 PR"""
    # 先关闭 PR
    client.post(f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/close", headers=auth_headers)

    # 再次关闭
    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/close",
        headers=auth_headers
    )

    assert response.status_code == 400


# ==================== PR 合并测试 ====================

def test_merge_pull_request_not_found(client, test_repository, auth_headers):
    """测试合并不存在的 PR"""
    payload = {"merge_method": "merge"}

    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/999/merge",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 404


def test_merge_pull_request_already_merged(client, test_pull_request, test_repository, auth_headers):
    """测试合并已关闭的 PR"""
    # 先关闭 PR
    client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/close",
        headers=auth_headers
    )

    # 尝试合并已关闭的 PR
    payload = {"merge_method": "merge"}
    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/merge",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 400


# ==================== PR 评论测试 ====================

def test_create_pr_comment_success(client, test_pull_request, test_repository, auth_headers):
    """测试成功创建 PR 评论"""
    payload = {
        "content": "This is a great PR!"
    }

    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/comments",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "This is a great PR!"


def test_create_pr_comment_line_level(client, test_pull_request, test_repository, auth_headers):
    """测试创建行级评论"""
    payload = {
        "content": "This line needs improvement",
        "file_path": "src/main.py",
        "line_number": 10,
        "commit_hash": "abc123"
    }

    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/comments",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["file_path"] == "src/main.py"
    assert data["line_number"] == 10


def test_list_pr_comments(client, test_pull_request, test_repository, auth_headers):
    """测试获取 PR 评论列表"""
    # 先通过 API 创建评论
    payload = {"content": "Test comment for list"}
    client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/comments",
        json=payload,
        headers=auth_headers
    )

    response = client.get(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/comments"
    )

    assert response.status_code == 200
    data = response.json()
    # 检查是否包含我们创建的评论
    contents = [c["content"] for c in data]
    assert "Test comment for list" in contents


# ==================== PR 审查测试 ====================

def test_create_pr_review_approved(client, test_pull_request, test_repository, auth_headers):
    """测试创建批准审查"""
    payload = {
        "status": "approved",
        "comment": "LGTM!"
    }

    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/reviews",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["comment"] == "LGTM!"


def test_create_pr_review_changes_requested(client, test_pull_request, test_repository, auth_headers):
    """测试创建请求修改审查"""
    payload = {
        "status": "changes_requested",
        "comment": "Please fix the issues"
    }

    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/reviews",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "changes_requested"


def test_update_existing_pr_review(client, test_pull_request, test_repository, auth_headers):
    """测试更新已存在的审查"""
    # 先创建审查
    payload = {"status": "approved"}
    client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/reviews",
        json=payload,
        headers=auth_headers
    )

    # 更新审查
    payload = {"status": "changes_requested", "comment": "Found some issues"}
    response = client.post(
        f"/api/repositories/{test_repository.id}/pull-requests/{test_pull_request.pr_number}/reviews",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "changes_requested"
