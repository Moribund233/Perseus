"""
WebSocket路由模块

定义WebSocket端点和连接处理逻辑
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging

from api.websocket.manager import manager, Connection
from api.websocket.auth import authenticate_websocket, authenticate_websocket_optional, WebSocketAuthError
from api.websocket.handlers import register_all_handlers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# 注册所有消息处理器
register_all_handlers()


@router.websocket("/logs")
async def logs_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="认证token（可选）")
):
    """
    实时日志 WebSocket 端点

    用于接收实时日志推送，替代传统的 HTTP 轮询日志接口

    连接URL格式:
    - ws://host:port/ws/logs?token=your_jwt_token

    消息协议:
    客户端 -> 服务端:
    {
        "type": "subscribe_logs",
        "filters": {
            "levels": ["INFO", "WARNING", "ERROR"],
            "loggers": ["app", "git"],
            "keywords": ["error"]
        },
        "history_count": 50
    }

    服务端 -> 客户端:
    {
        "type": "log",
        "timestamp": "2026-02-18 10:30:45",
        "level": "ERROR",
        "logger": "app.git",
        "message": "Git operation failed"
    }
    """
    connection: Optional[Connection] = None

    try:
        # 接受连接
        connection = await manager.connect(websocket)

        # 尝试认证（可选）
        try:
            user_info = await authenticate_websocket_optional(websocket)
            if user_info:
                manager.bind_user(
                    connection,
                    user_id=user_info["user_id"],
                    username=user_info["username"]
                )

                await connection.send({
                    "type": "connected",
                    "connection_id": connection.connection_id,
                    "authenticated": True,
                    "channel": "logs",
                    "message": "日志通道已连接"
                })
            else:
                await connection.send({
                    "type": "connected",
                    "connection_id": connection.connection_id,
                    "authenticated": False,
                    "channel": "logs",
                    "message": "日志通道已连接（匿名模式）"
                })
        except WebSocketAuthError as e:
            await websocket.close(code=e.code, reason=e.message)
            if connection:
                manager.disconnect(connection)
            return

        # 主消息循环
        while connection.is_alive:
            try:
                data = await websocket.receive_json()
                # 更新心跳时间，保持连接活跃
                connection.update_ping()
                await manager.handle_message(connection, data)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"日志WebSocket异常: {e}")
                try:
                    await connection.send({
                        "type": "error",
                        "error": f"消息处理失败: {str(e)}"
                    })
                except:
                    break

    finally:
        if connection:
            # 取消日志订阅
            from api.websocket.handlers.log_handler import get_websocket_log_handler
            handler = get_websocket_log_handler()
            await handler.subscription_manager.unsubscribe(connection)
            manager.disconnect(connection)


@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="认证token（可选，如果不提供则尝试从query参数获取）")
):
    """
    WebSocket主端点
    
    连接URL格式:
    - ws://host:port/ws/?token=your_jwt_token
    
    认证:
    - 通过URL query参数传递token
    - 如果不提供token，连接将被接受但处于匿名状态
    - 某些功能可能需要认证后才能使用
    
    消息协议:
    客户端 -> 服务端:
    {
        "type": "ping|subscribe|unsubscribe|sync_request|...",
        ...
    }
    
    服务端 -> 客户端:
    {
        "type": "pong|notification|sync_status|progress|error|...",
        ...
    }
    """
    connection: Optional[Connection] = None
    
    try:
        # 接受WebSocket连接
        connection = await manager.connect(websocket)
        logger.info(f"WebSocket连接已建立: {connection.connection_id}")
        
        # 尝试认证（可选）
        try:
            user_info = await authenticate_websocket_optional(websocket)
            if user_info:
                # 绑定用户到连接
                manager.bind_user(
                    connection,
                    user_id=user_info["user_id"],
                    username=user_info["username"]
                )
                # 存储用户权限信息
                connection.metadata["is_admin"] = user_info.get("is_admin", False)
                
                # 发送认证成功消息
                await connection.send({
                    "type": "connected",
                    "connection_id": connection.connection_id,
                    "authenticated": True,
                    "user": {
                        "id": user_info["user_id"],
                        "username": user_info["username"],
                        "is_admin": user_info.get("is_admin", False)
                    },
                    "message": "连接成功，已认证"
                })
            else:
                # 匿名连接
                await connection.send({
                    "type": "connected",
                    "connection_id": connection.connection_id,
                    "authenticated": False,
                    "message": "连接成功，匿名模式（部分功能受限）"
                })
        except WebSocketAuthError as e:
            # 认证失败，发送错误后关闭连接
            logger.warning(f"WebSocket认证失败: {e.message}")
            await websocket.close(code=e.code, reason=e.message)
            if connection:
                manager.disconnect(connection)
            return
        
        # 主消息循环
        while connection.is_alive:
            try:
                # 接收消息
                data = await websocket.receive_json()
                logger.debug(f"收到消息 connection_id={connection.connection_id}: {data}")

                # 更新心跳时间，保持连接活跃
                connection.update_ping()

                # 处理消息
                await manager.handle_message(connection, data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket连接断开: {connection.connection_id}")
                break
            except Exception as e:
                logger.error(f"处理消息时出错 connection_id={connection.connection_id}: {e}")
                try:
                    await connection.send({
                        "type": "error",
                        "error": f"消息处理失败: {str(e)}"
                    })
                except:
                    break
    
    except Exception as e:
        logger.error(f"WebSocket连接处理异常: {e}")
    
    finally:
        # 清理连接
        if connection:
            manager.disconnect(connection)
            logger.info(f"WebSocket连接已清理: {connection.connection_id}")


@router.websocket("/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="认证token（必需）")
):
    """
    通知专用WebSocket端点（需要认证）
    
    此端点仅用于接收通知，自动订阅用户通知频道
    """
    connection: Optional[Connection] = None
    
    try:
        # 必须先认证
        try:
            user_info = await authenticate_websocket(websocket)
        except WebSocketAuthError as e:
            await websocket.close(code=e.code, reason=e.message)
            return
        
        # 接受连接
        connection = await manager.connect(websocket)
        
        # 绑定用户
        manager.bind_user(
            connection,
            user_id=user_info["user_id"],
            username=user_info["username"]
        )
        
        # 自动订阅用户通知
        await connection.send({
            "type": "connected",
            "connection_id": connection.connection_id,
            "channel": "user_notifications",
            "message": "通知通道已连接"
        })
        
        # 保持连接，处理心跳
        while connection.is_alive:
            try:
                data = await websocket.receive_json()
                
                # 只处理ping消息
                if data.get("type") == "ping":
                    connection.update_ping()
                    await connection.send({
                        "type": "pong",
                        "timestamp": data.get("timestamp"),
                        "server_time": __import__('datetime').datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"通知WebSocket异常: {e}")
                break
    
    finally:
        if connection:
            manager.disconnect(connection)


@router.websocket("/repository/{repository_id}")
async def repository_websocket(
    websocket: WebSocket,
    repository_id: int,
    token: Optional[str] = Query(None, description="认证token（可选）")
):
    """
    仓库专用WebSocket端点
    
    连接后自动订阅指定仓库的消息
    """
    connection: Optional[Connection] = None
    
    try:
        # 接受连接
        connection = await manager.connect(websocket)
        
        # 尝试认证
        try:
            user_info = await authenticate_websocket_optional(websocket)
            if user_info:
                manager.bind_user(
                    connection,
                    user_id=user_info["user_id"],
                    username=user_info["username"]
                )
        except WebSocketAuthError:
            pass  # 允许匿名连接
        
        # 自动订阅仓库
        manager.subscribe_repository(connection, repository_id)
        
        await connection.send({
            "type": "connected",
            "connection_id": connection.connection_id,
            "repository_id": repository_id,
            "authenticated": connection.user_id is not None,
            "message": f"已连接到仓库 {repository_id}"
        })
        
        # 主消息循环
        while connection.is_alive:
            try:
                data = await websocket.receive_json()
                await manager.handle_message(connection, data)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"仓库WebSocket异常: {e}")
                break
    
    finally:
        if connection:
            manager.disconnect(connection)
