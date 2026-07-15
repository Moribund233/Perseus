"""
Bug 回归测试

验证已知 bug 的存在，修复后确保不回归。
"""
import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Bug #1: 路由冲突 — GET /{repo_id}/commits 被 repository_browser_controller 遮盖
#         修复：移除 commit_controller 中的重复路由
# =============================================================================

def test_commits_endpoint_no_auth_returns_non_401(test_client: TestClient, db):
    """
    Bug #1 回归测试

    修复前：
    - commit_controller 和 browser_controller 都注册了 GET /{repo_id}/commits
    - browser 版本先注册（无认证），导致 commit 版本成为死代码
    - 同时 browser 版本缺失 await，返回 500

    修复后：
    - 已移除 commit_controller 的重复路由
    - browser 版本已添加 await
    - 无认证调用应返回有效的非 401 响应
    """
    from tests.test_helpers import create_test_repo
    from utils.git_utils import init_bare_repo, get_repository_storage_path

    repo = create_test_repo(db, name="bug-test-repo", path="testuser/bug-test-repo")
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)

    response = test_client.get(f"/api/v1/repositories/{repo.id}/commits")

    assert response.status_code != 401, "无认证不应返回 401（browser 版本无需认证）"
    assert response.status_code != 500, f"不应因 await 缺失而崩溃，实际：{response.text}"
    # 空仓库返回 200 的预期结果
    assert response.status_code == 200, f"预期 200，实际 {response.status_code}：{response.text}"


# =============================================================================
# Bug #2: current_user.get("id") 类型错误 — api/error.py:187
#         修复：User 对象用 .id 而非 .get("id")
# =============================================================================

def test_report_error_with_auth_returns_200(test_client: TestClient, auth_headers: dict):
    """
    Bug #2 回归测试

    修复前：
    - current_user: Optional[dict] = Depends(get_current_user)
    - get_current_user() 返回 User 对象，不是 dict
    - User 对象没有 .get() 方法 -> AttributeError -> 500

    修复后：
    - 类型注解改为 Optional[User]
    - current_user.get("id") 改为 current_user.id
    - 带合法 JWT 调用应返回 200
    """
    response = test_client.post(
        "/api/v1/errors/report",
        json={"message": "test error", "stack": "test stack"},
        headers=auth_headers
    )

    assert response.status_code == 200, (
        f"预期 200，实际返回 {response.status_code}。"
        f"响应内容：{response.text}"
    )
    data = response.json()
    assert data["status"] == "received"
