"""
用户头像上传 API 测试
"""
import io
import pytest

from services.user_service import AVATAR_UPLOAD_DIR


@pytest.fixture(autouse=True)
def cleanup_avatars():
    """每次测试前清理头像目录"""
    yield
    if AVATAR_UPLOAD_DIR.exists():
        for f in AVATAR_UPLOAD_DIR.iterdir():
            try:
                f.unlink()
            except OSError:
                pass


def test_upload_avatar_success(test_client, auth_headers):
    """成功上传头像"""
    response = test_client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", io.BytesIO(b"fake-image-data"), "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "avatar_url" in data
    assert data["avatar_url"].startswith("/api/v1/users/")
    assert data["avatar_url"].endswith("/avatar")


def test_upload_avatar_invalid_format(test_client, auth_headers):
    """上传非图片文件应该失败"""
    response = test_client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.txt", io.BytesIO(b"not-an-image"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_upload_avatar_requires_auth(test_client):
    """未认证不能上传头像"""
    response = test_client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", io.BytesIO(b"fake-image-data"), "image/png")},
    )
    assert response.status_code == 401


def test_get_avatar_success(test_client, auth_headers):
    """成功获取头像文件"""
    upload_response = test_client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", io.BytesIO(b"fake-image-data"), "image/png")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 200
    user_id = upload_response.json()["id"]

    response = test_client.get(f"/api/v1/users/{user_id}/avatar")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"fake-image-data"


def test_get_avatar_not_found(test_client):
    """获取不存在的头像返回 404"""
    response = test_client.get("/api/v1/users/00000000-0000-0000-0000-000000000000/avatar")
    assert response.status_code == 404
