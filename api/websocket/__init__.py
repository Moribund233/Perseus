"""
WebSocket API模块

提供WebSocket实时通信功能，包括：
- 实时通知推送
- 协作状态同步
- 操作进度反馈
"""
from api.websocket.router import router

__all__ = ["router"]
