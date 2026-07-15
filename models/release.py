"""
Release 数据模型

存储仓库的版本发布信息
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Uuid as SAUuid
from sqlalchemy.orm import relationship

from models.base import BaseModel


class Release(BaseModel):
    """
    Release 数据模型
    
    存储代码版本发布信息，支持关联 Git 标签和上传附件
    """
    __tablename__ = "releases"
    
    repository_id = Column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    """所属仓库ID"""
    
    release_number = Column(Integer, nullable=False)
    """Release 编号（每个仓库内自增）"""
    
    tag_name = Column(String(100), nullable=False)
    """Git 标签名称"""
    
    name = Column(String(255), nullable=False)
    """Release 标题"""
    
    description = Column(Text, nullable=True)
    """Release 描述（支持 Markdown）"""
    
    author_id = Column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    """创建者ID"""
    
    commit_hash = Column(String(40), nullable=False)
    """关联的提交哈希"""
    
    is_draft = Column(Boolean, default=False)
    """是否为草稿"""
    
    is_prerelease = Column(Boolean, default=False)
    """是否为预发布版本"""
    
    # 关联关系
    repository = relationship("Repository", backref="releases")
    author = relationship("User", backref="created_releases")
    
    def __repr__(self):
        return f"<Release({self.tag_name}: {self.name})>"


class ReleaseAsset(BaseModel):
    """
    Release 附件模型
    
    存储 Release 相关的附件文件（如构建产物）
    """
    __tablename__ = "release_assets"
    
    release_id = Column(SAUuid(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    """所属 Release ID"""
    
    name = Column(String(255), nullable=False)
    """文件名"""
    
    file_path = Column(String(500), nullable=False)
    """文件存储路径"""
    
    file_size = Column(Integer, nullable=False)
    """文件大小（字节）"""
    
    content_type = Column(String(100), nullable=True)
    """文件 MIME 类型"""
    
    download_count = Column(Integer, default=0)
    """下载次数"""
    
    # 关联关系
    release = relationship("Release", backref="assets")
    
    def __repr__(self):
        return f"<ReleaseAsset({self.name})>"
