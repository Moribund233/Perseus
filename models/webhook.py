"""
WebHook 数据模型

存储和管理仓库的 WebHook 配置
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Uuid as SAUuid
from sqlalchemy.orm import relationship

from models.base import BaseModel


# 支持的 WebHook 事件类型
WEBHOOK_EVENTS = [
    # 代码推送事件
    "push",                    # 代码推送
    "tag_push",                # 标签推送
    
    # Pull Request 事件
    "pull_request.opened",     # PR 创建
    "pull_request.updated",    # PR 更新
    "pull_request.merged",     # PR 合并
    "pull_request.closed",     # PR 关闭
    "pull_request.reopened",   # PR 重新打开
    
    # Release 事件
    "release.created",         # Release 创建
    "release.published",       # Release 发布
    "release.updated",         # Release 更新
    "release.deleted",         # Release 删除
    
    # Issue 事件
    "issue.opened",            # Issue 创建
    "issue.closed",            # Issue 关闭
    "issue.reopened",          # Issue 重新打开
    "issue.updated",           # Issue 更新
    
    # 仓库事件
    "repository.created",      # 仓库创建
    "repository.deleted",      # 仓库删除
    "repository.forked",       # 仓库被 Fork
]


class WebHook(BaseModel):
    """
    WebHook 数据模型
    
    存储仓库的 WebHook 配置信息
    """
    __tablename__ = "webhooks"
    
    repository_id = Column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    """所属仓库ID"""
    
    url = Column(String(500), nullable=False)
    """回调 URL"""
    
    events = Column(Text, nullable=False, default="push")
    """订阅的事件列表，JSON 格式存储，如 ["push", "pull_request.opened"]"""
    
    secret = Column(String(255), nullable=True)
    """签名密钥，用于验证请求来源"""
    
    is_active = Column(Boolean, default=True)
    """是否激活"""
    
    content_type = Column(String(50), default="application/json")
    """Content-Type，支持 application/json 或 application/x-www-form-urlencoded"""
    
    last_triggered_at = Column(DateTime, nullable=True)
    """最后触发时间"""
    
    last_response_status = Column(Integer, nullable=True)
    """最后响应状态码"""
    
    last_response_body = Column(Text, nullable=True)
    """最后响应内容"""
    
    # 关联关系
    repository = relationship("Repository", backref="webhooks")
    
    def __repr__(self) -> str:
        return f"<WebHook(id={self.id}, url='{self.url}', active={self.is_active})>"
    
    def get_events_list(self) -> List[str]:
        """
        获取事件列表
        
        Returns:
            List[str]: 订阅的事件列表
        """
        import json
        try:
            return json.loads(self.events) if self.events else []
        except json.JSONDecodeError:
            return []
    
    def set_events_list(self, events: List[str]) -> None:
        """
        设置事件列表
        
        Args:
            events: 事件列表
        """
        import json
        self.events = json.dumps(events)
    
    def is_subscribed_to(self, event: str) -> bool:
        """
        检查是否订阅了指定事件
        
        Args:
            event: 事件名称
            
        Returns:
            bool: 是否订阅
        """
        events = self.get_events_list()
        
        # 支持通配符匹配，如 "pull_request.*" 匹配所有 PR 事件
        for subscribed_event in events:
            if subscribed_event == event:
                return True
            if subscribed_event.endswith(".*"):
                prefix = subscribed_event[:-2]
                if event.startswith(prefix + "."):
                    return True
        
        return False


class WebHookDelivery(BaseModel):
    """
    WebHook 投递记录
    
    记录每次 WebHook 调用的详细信息，用于调试和审计
    """
    __tablename__ = "webhook_deliveries"
    
    webhook_id = Column(SAUuid(as_uuid=True), ForeignKey("webhooks.id"), nullable=False)
    """WebHook ID"""
    
    event = Column(String(100), nullable=False)
    """触发的事件类型"""
    
    payload = Column(Text, nullable=False)
    """发送的 payload 内容（JSON 格式）"""
    
    request_headers = Column(Text, nullable=True)
    """请求头信息（JSON 格式）"""
    
    response_status = Column(Integer, nullable=True)
    """响应状态码"""
    
    response_body = Column(Text, nullable=True)
    """响应内容"""
    
    response_headers = Column(Text, nullable=True)
    """响应头信息（JSON 格式）"""
    
    duration_ms = Column(Integer, nullable=True)
    """请求耗时（毫秒）"""
    
    is_success = Column(Boolean, default=False)
    """是否成功"""
    
    error_message = Column(Text, nullable=True)
    """错误信息"""
    
    # 关联关系
    webhook = relationship("WebHook", backref="deliveries")
    
    def __repr__(self) -> str:
        return f"<WebHookDelivery(id={self.id}, event='{self.event}', success={self.is_success})>"
