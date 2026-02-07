"""
测试用户API端点

验证用户API端点使用自定义异常，并且这些异常能够被全局异常处理器正确捕获和处理
"""
import pytest
from fastapi.testclient import TestClient
from app import get_app

# 创建测试客户端
app = get_app()
client = TestClient(app)


def test_get_users():
    """
    测试获取所有用户
    """
    response = client.get("/api/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_non_existent_user():
    """
    测试获取不存在的用户，应该返回404 Not Found
    """
    response = client.get("/api/users/999")
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == 404
    assert response.json()["error"]["type"] == "NotFoundException"


def test_create_user():
    """
    测试创建新用户
    """
    # 先创建一个测试用户
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword"
    }
    
    # 发送创建用户请求
    response = client.post("/api/users/", json=user_data)
    
    # 检查响应
    if response.status_code == 200:
        # 用户创建成功
        assert "id" in response.json()
        assert response.json()["username"] == user_data["username"]
        assert response.json()["email"] == user_data["email"]
    elif response.status_code == 409:
        # 用户已存在，这也是一个可以接受的结果
        assert "error" in response.json()
        assert response.json()["error"]["type"] == "ConflictException"
    else:
        # 其他状态码，测试失败
        assert False, f"Unexpected status code: {response.status_code}"


def test_create_duplicate_user():
    """
    测试创建重复用户，应该返回409 Conflict
    """
    # 先创建一个测试用户
    user_data = {
        "username": "duplicateuser",
        "email": "duplicate@example.com",
        "password": "testpassword"
    }
    
    # 第一次创建用户
    client.post("/api/users/", json=user_data)
    
    # 第二次创建相同的用户，应该返回冲突
    response = client.post("/api/users/", json=user_data)
    assert response.status_code == 409
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "ConflictException"


def test_update_user():
    """
    测试更新用户信息
    """
    # 先创建一个测试用户
    user_data = {
        "username": "updateuser",
        "email": "update@example.com",
        "password": "testpassword"
    }
    create_response = client.post("/api/users/", json=user_data)
    
    if create_response.status_code == 200:
        user_id = create_response.json()["id"]
        
        # 更新用户信息
        update_data = {
            "full_name": "Updated User Name",
            "is_active": True
        }
        
        response = client.put(f"/api/users/{user_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["full_name"] == update_data["full_name"]
        assert response.json()["is_active"] == update_data["is_active"]
    elif create_response.status_code == 409:
        # 用户已存在，跳过更新测试
        pass


def test_delete_user():
    """
    测试删除用户
    """
    # 先创建一个测试用户
    user_data = {
        "username": "deleteuser",
        "email": "delete@example.com",
        "password": "testpassword"
    }
    create_response = client.post("/api/users/", json=user_data)
    
    if create_response.status_code == 200:
        user_id = create_response.json()["id"]
        
        # 删除用户
        response = client.delete(f"/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "User deleted successfully"
        
        # 验证用户已被删除
        get_response = client.get(f"/api/users/{user_id}")
        assert get_response.status_code == 404
    elif create_response.status_code == 409:
        # 用户已存在，跳过删除测试
        pass


if __name__ == "__main__":
    # 运行所有测试
    test_get_users()
    test_get_non_existent_user()
    test_create_user()
    test_create_duplicate_user()
    test_update_user()
    test_delete_user()
    
    print("All tests passed!")
