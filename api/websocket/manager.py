"""
WebSocket连接管理器

管理所有WebSocket连接，提供：
- 连接注册/注销
- 用户绑定和查询
- 分组广播（按仓库、按用户）
- 心跳检测
- 消息发送
"""
import asyncio
import json
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)


class Connection:
    """
    WebSocket连接包装类
    
    封装单个WebSocket连接，维护连接状态和用户绑定信息
    """
    
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id: Optional[int] = None
        self.username: Optional[str] = None
        self.repository_ids: Set[int] = set()  # 用户关注的仓库ID列表
        self.connected_at: datetime = datetime.now()
        self.last_ping: datetime = datetime.now()
        self.is_alive: bool = True
        self.metadata: Dict[str, Any] = {}  # 扩展元数据
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """
        发送消息到客户端
        
        Args:
            message: 消息字典，会被序列化为JSON
            
        Returns:
            bool: 发送成功返回True
        """
        try:
            await self.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败 connection_id={self.connection_id}: {e}")
            self.is_alive = False
            return False
    
    def bind_user(self, user_id: int, username: str) -> None:
        """绑定用户到连接"""
        self.user_id = user_id
        self.username = username
        logger.info(f"用户绑定 connection_id={self.connection_id}, user_id={user_id}, username={username}")
    
    def subscribe_repository(self, repository_id: int) -> None:
        """订阅仓库消息"""
        self.repository_ids.add(repository_id)
        logger.debug(f"订阅仓库 connection_id={self.connection_id}, repository_id={repository_id}")
    
    def unsubscribe_repository(self, repository_id: int) -> None:
        """取消订阅仓库消息"""
        self.repository_ids.discard(repository_id)
        logger.debug(f"取消订阅仓库 connection_id={self.connection_id}, repository_id={repository_id}")
    
    def update_ping(self) -> None:
        """更新心跳时间"""
        self.last_ping = datetime.now()
    
    def is_timeout(self, timeout_seconds: int = 120) -> bool:
        """检查连接是否超时"""
        return (datetime.now() - self.last_ping).seconds > timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "username": self.username,
            "repository_ids": list(self.repository_ids),
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "is_alive": self.is_alive,
        }


class ConnectionManager:
    """
    WebSocket连接管理器（单例模式）
    
    管理所有活跃的WebSocket连接，提供高效的连接查询和消息广播功能
    """
    
    _instance: Optional['ConnectionManager'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ConnectionManager._initialized:
            return
        
        # 连接存储: connection_id -> Connection
        self._connections: Dict[str, Connection] = {}
        
        # 用户索引: user_id -> set of connection_ids
        self._user_index: Dict[int, Set[str]] = {}
        
        # 仓库索引: repository_id -> set of connection_ids
        self._repository_index: Dict[int, Set[str]] = {}
        
        # 连接ID计数器
        self._connection_counter: int = 0
        
        # 消息处理器注册表: message_type -> handler function
        self._message_handlers: Dict[str, Callable] = {}
        
        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running: bool = False
        
        ConnectionManager._initialized = True
    
    def _generate_connection_id(self) -> str:
        """生成唯一的连接ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    async def connect(self, websocket: WebSocket) -> Connection:
        """
        接受新的WebSocket连接
        
        Args:
            websocket: FastAPI WebSocket对象
            
        Returns:
            Connection: 创建的连接对象
        """
        await websocket.accept()
        connection_id = self._generate_connection_id()
        connection = Connection(websocket, connection_id)
        self._connections[connection_id] = connection
        
        logger.debug(f"WebSocket连接: {connection_id}, 当前: {len(self._connections)}")
        
        if not self._running:
            self._start_background_tasks()
        
        return connection
    
    def disconnect(self, connection: Connection) -> None:
        """
        断开WebSocket连接并清理资源
        
        Args:
            connection: 要断开的连接对象
        """
        connection_id = connection.connection_id
        
        # 从用户索引中移除
        if connection.user_id is not None:
            if connection.user_id in self._user_index:
                self._user_index[connection.user_id].discard(connection_id)
                if not self._user_index[connection.user_id]:
                    del self._user_index[connection.user_id]
        
        # 从仓库索引中移除
        for repo_id in connection.repository_ids:
            if repo_id in self._repository_index:
                self._repository_index[repo_id].discard(connection_id)
                if not self._repository_index[repo_id]:
                    del self._repository_index[repo_id]
        
        # 从连接池中移除
        if connection_id in self._connections:
            del self._connections[connection_id]
        
        connection.is_alive = False
        logger.debug(f"WebSocket断开: {connection_id}, 当前: {len(self._connections)}")
    
    def bind_user(self, connection: Connection, user_id: int, username: str) -> None:
        """
        将连接绑定到用户
        
        Args:
            connection: 连接对象
            user_id: 用户ID
            username: 用户名
        """
        # 如果之前绑定过其他用户，先清理
        if connection.user_id is not None and connection.user_id != user_id:
            old_user_id = connection.user_id
            if old_user_id in self._user_index:
                self._user_index[old_user_id].discard(connection.connection_id)
        
        # 绑定新用户
        connection.bind_user(user_id, username)
        
        # 更新用户索引
        if user_id not in self._user_index:
            self._user_index[user_id] = set()
        self._user_index[user_id].add(connection.connection_id)
    
    def subscribe_repository(self, connection: Connection, repository_id: int) -> None:
        """
        订阅仓库消息
        
        Args:
            connection: 连接对象
            repository_id: 仓库ID
        """
        connection.subscribe_repository(repository_id)
        
        # 更新仓库索引
        if repository_id not in self._repository_index:
            self._repository_index[repository_id] = set()
        self._repository_index[repository_id].add(connection.connection_id)
    
    def unsubscribe_repository(self, connection: Connection, repository_id: int) -> None:
        """
        取消订阅仓库消息
        
        Args:
            connection: 连接对象
            repository_id: 仓库ID
        """
        connection.unsubscribe_repository(repository_id)
        
        # 更新仓库索引
        if repository_id in self._repository_index:
            self._repository_index[repository_id].discard(connection.connection_id)
            if not self._repository_index[repository_id]:
                del self._repository_index[repository_id]
    
    # ==================== 消息发送方法 ====================
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        发送消息到指定连接
        
        Args:
            connection_id: 连接ID
            message: 消息字典
            
        Returns:
            bool: 发送成功返回True
        """
        connection = self._connections.get(connection_id)
        if connection and connection.is_alive:
            return await connection.send(message)
        return False
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """
        发送消息给用户的所有连接
        
        Args:
            user_id: 用户ID
            message: 消息字典
            
        Returns:
            int: 成功发送的连接数
        """
        connection_ids = self._user_index.get(user_id, set())
        success_count = 0
        
        for conn_id in list(connection_ids):
            if await self.send_to_connection(conn_id, message):
                success_count += 1
        
        return success_count
    
    async def send_to_repository(self, repository_id: int, message: Dict[str, Any], exclude_user_id: Optional[int] = None) -> int:
        """
        广播消息到仓库的所有订阅者
        
        Args:
            repository_id: 仓库ID
            message: 消息字典
            exclude_user_id: 排除的用户ID（可选，用于不发送给操作者自己）
            
        Returns:
            int: 成功发送的连接数
        """
        connection_ids = self._repository_index.get(repository_id, set())
        success_count = 0
        
        for conn_id in list(connection_ids):
            connection = self._connections.get(conn_id)
            if connection and connection.is_alive:
                # 如果指定了排除用户，跳过该用户的连接
                if exclude_user_id is not None and connection.user_id == exclude_user_id:
                    continue
                if await connection.send(message):
                    success_count += 1
        
        return success_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        广播消息给所有连接
        
        Args:
            message: 消息字典
            
        Returns:
            int: 成功发送的连接数
        """
        success_count = 0
        dead_connections: List[str] = []
        
        for conn_id, connection in list(self._connections.items()):
            if connection.is_alive:
                if await connection.send(message):
                    success_count += 1
                else:
                    dead_connections.append(conn_id)
            else:
                dead_connections.append(conn_id)
        
        # 清理死连接
        for conn_id in dead_connections:
            if conn_id in self._connections:
                self.disconnect(self._connections[conn_id])
        
        return success_count
    
    # ==================== 消息处理器 ====================
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数，接收(connection, message)参数
        """
        self._message_handlers[message_type] = handler
    
    async def handle_message(self, connection: Connection, message: Dict[str, Any]) -> None:
        """
        处理收到的消息
        
        Args:
            connection: 连接对象
            message: 消息字典
        """
        msg_type = message.get("type", "unknown")
        handler = self._message_handlers.get(msg_type)
        
        if handler:
            try:
                await handler(connection, message)
            except Exception as e:
                logger.error(f"消息处理失败 type={msg_type}: {e}")
                await connection.send({
                    "type": "error",
                    "error": f"消息处理失败: {str(e)}",
                    "original_type": msg_type
                })
        else:
            logger.warning(f"未找到消息处理器: {msg_type}")
            await connection.send({
                "type": "error",
                "error": f"未知的消息类型: {msg_type}",
                "supported_types": list(self._message_handlers.keys())
            })
    
    # ==================== 后台任务 ====================
    
    def _start_background_tasks(self) -> None:
        """启动后台任务"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_background_tasks(self) -> None:
        """停止后台任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def heartbeat_checker(self) -> None:
        """
        心跳检测任务
        
        由 lifespan 管理器启动，用于监控连接健康状态
        """
        while self._running:
            try:
                await asyncio.sleep(30)
                await self._cleanup_timeout_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测任务异常: {e}")

    @property
    def active_connections(self) -> Dict[str, 'Connection']:
        """获取所有活跃连接"""
        return self._connections

    @property
    def user_connections(self) -> Dict[int, Set[str]]:
        """获取用户连接索引"""
        return self._user_index
    
    async def _cleanup_loop(self) -> None:
        """清理循环，定期移除超时连接"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_timeout_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务异常: {e}")
    
    async def _cleanup_timeout_connections(self) -> None:
        """清理超时连接"""
        timeout_connections: List[Connection] = []
        
        for connection in self._connections.values():
            if connection.is_timeout():
                timeout_connections.append(connection)
        
        for connection in timeout_connections:
            logger.info(f"清理超时连接 connection_id={connection.connection_id}")
            try:
                await connection.websocket.close(code=1001, reason="Connection timeout")
            except:
                pass
            self.disconnect(connection)
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        return {
            "total_connections": len(self._connections),
            "active_users": len(self._user_index),
            "subscribed_repositories": len(self._repository_index),
            "connections": [conn.to_dict() for conn in self._connections.values()],
        }
    
    def get_user_connections(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户的所有连接信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            List: 连接信息列表
        """
        connection_ids = self._user_index.get(user_id, set())
        return [
            self._connections[conn_id].to_dict()
            for conn_id in connection_ids
            if conn_id in self._connections
        ]


# 全局连接管理器实例
manager = ConnectionManager()
