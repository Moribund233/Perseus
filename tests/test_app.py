import pytest
from fastapi.testclient import TestClient
from app import create_app, app_singleton
from config import reset_module_config_manager


def test_create_app():
    """
    测试创建FastAPI应用
    """
    # 创建应用
    app = create_app()
    
    # 验证应用
    assert app is not None
    assert app.title == "LanGit API"
    assert app.description == "A Git-based collaborative development tool API"
    assert app.version == "0.1.0"


def test_app_singleton():
    """
    测试应用单例模式
    """
    # 重置应用单例和配置管理器
    app_singleton.reset()
    reset_module_config_manager()
    
    # 获取第一个实例
    app1 = app_singleton.get_app()
    
    # 获取第二个实例
    app2 = app_singleton.get_app()
    
    # 验证是同一个实例
    assert app1 is app2
    
    # 重置单例
    app_singleton.reset()
    
    # 获取新实例
    app3 = app_singleton.get_app()
    
    # 验证是新实例
    assert app1 is not app3


def test_root_route():
    """
    测试根路由
    """
    # 创建应用和测试客户端
    app = create_app()
    client = TestClient(app)
    
    # 发送请求
    response = client.get("/")
    
    # 验证响应
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to LanGit API"
    assert "title" in response.json()
    assert "version" in response.json()
    assert "status" in response.json()


def test_health_check():
    """
    测试健康检查路由
    """
    # 创建应用和测试客户端
    app = create_app()
    client = TestClient(app)
    
    # 发送请求
    response = client.get("/health")
    
    # 验证响应
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()
    assert "service" in response.json()


def test_cors_headers():
    """
    测试CORS头
    
    注意：如果配置中启用了Nginx代理，FastAPI的CORS中间件会被禁用，
    此时CORS头由Nginx处理，测试会跳过CORS验证
    """
    from config import get_config
    
    # 获取配置
    config = get_config()
    
    # 创建应用和测试客户端
    app = create_app()
    client = TestClient(app)
    
    # 发送带有Origin头的请求
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    
    # 验证响应状态
    assert response.status_code == 200
    
    # 如果Nginx代理未启用，验证FastAPI的CORS头
    if not config.nginx.proxy:
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        
        # 发送带有不允许的Origin头的请求
        response = client.get("/", headers={"Origin": "http://example.com"})
        
        # 验证没有CORS头
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
    else:
        # Nginx代理模式下，CORS由Nginx处理，FastAPI不添加CORS头
        # 这种情况下只验证响应成功即可
        pass
