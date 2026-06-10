"""
调试控制器

提供调试/开发用的管理接口：
- debug/initdb: 重置数据库（删除并重新创建所有表）
- debug/initconf: 重置配置文件（删除并重新生成默认配置）

安全要求：
- 仅在调试模式下可用（app.debug=true）
- 需要本地认证（Local Auth）或管理员用户认证
- 这些接口具有破坏性，谨慎使用
"""
import os
import shutil
import gc
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from core.config import get_config, ConfigManager, reset_module_config_manager
from api.dependencies import security
from models.user import User
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from utils.init_database import DatabaseInitializer
from utils.logging import get_named_logger

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])
logger = get_named_logger("debug")


# ============== Pydantic 模型 ==============


class InitDbResponse(BaseModel):
    """初始化数据库响应模型"""
    success: bool
    message: str
    details: dict = Field(default_factory=dict)


class InitConfResponse(BaseModel):
    """初始化配置文件响应模型"""
    success: bool
    message: str
    config_path: str
    backup_path: Optional[str] = None


class RateLimitInfo(BaseModel):
    """限流配置信息"""
    default_limits: list = Field(default_factory=list, description="默认限流规则")
    strict: list = Field(default_factory=list, description="严格限流规则")
    standard: list = Field(default_factory=list, description="标准限流规则")
    generous: list = Field(default_factory=list, description="宽松限流规则")
    git_operations: list = Field(default_factory=list, description="Git操作限流规则")
    download: list = Field(default_factory=list, description="下载限流规则")


class DebugStatusResponse(BaseModel):
    """调试状态响应模型"""
    debug_mode: bool
    config_path: str
    config_exists: bool
    database_url: str
    database_type: str
    environment: dict = Field(default_factory=dict, description="环境变量信息")
    stress_test_mode: bool = Field(default=False, description="是否处于压力测试模式")
    rate_limit: RateLimitInfo = Field(default_factory=RateLimitInfo, description="限流配置信息")


# ============== 依赖函数 ==============


async def require_debug_mode():
    """
    检查是否处于调试模式
    
    Raises:
        HTTPException: 非调试模式下抛出 403 错误
    """
    config = get_config()
    if not config.app.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in debug mode"
        )


async def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    要求 JWT 管理员权限

    Args:
        request: FastAPI 请求对象
        credentials: HTTP 认证凭证

    Returns:
        User: 认证通过的管理员用户

    Raises:
        HTTPException: 权限不足时抛出 401/403 错误
    """
    from services.token_service import verify_token
    from models.async_db import get_async_db
    from sqlalchemy import select

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_data = verify_token(token, token_type="access")

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async for db in get_async_db():
        try:
            result = await db.execute(select(User).filter(User.id == token_data.user_id))
            user = result.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin permission required",
                )

            return user
        finally:
            await db.close()


# ============== 数据库操作辅助函数 ==============

def _get_sync_engine_with_url(url: str):
    """
    根据数据库 URL 创建同步引擎
    
    Args:
        url: 数据库连接 URL
        
    Returns:
        Engine: SQLAlchemy 同步引擎
    """
    from sqlalchemy import create_engine
    
    # 转换 URL 为带驱动的格式
    url_lower = url.lower()
    if url_lower.startswith("postgresql://") and not url_lower.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    return create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)


def _drop_all_tables_postgresql(engine):
    """删除 PostgreSQL 数据库中的所有表"""
    with engine.connect() as conn:
        # 获取所有表
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]
        
        # 删除每个表
        for table in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        
        conn.commit()
        logger.info(f"已删除 PostgreSQL 数据库中的 {len(tables)} 个表")


# ============== API 端点 ==============


@router.get("/status", response_model=DebugStatusResponse)
async def debug_status(
    _: User = Depends(require_admin),
    __: None = Depends(require_debug_mode)
):
    """
    获取调试状态信息

    显示当前调试模式状态、配置文件状态、环境变量等信息

    Returns:
        DebugStatusResponse: 调试状态信息
    """
    config = get_config()
    config_path = "config.toml"

    # 收集环境变量信息（排除敏感信息）
    env_info = {}
    sensitive_keys = {'password', 'secret', 'token', 'key', 'jwt', 'auth'}

    for key, value in os.environ.items():
        # 只包含 PERSEUS_ 开头的环境变量
        if key.startswith('PERSEUS_'):
            # 检查是否是敏感信息
            key_lower = key.lower()
            is_sensitive = any(s in key_lower for s in sensitive_keys)

            if is_sensitive:
                env_info[key] = "***masked***"
            else:
                env_info[key] = value

    # 检查是否处于压力测试模式
    stress_test_mode = os.environ.get('PERSEUS_STRESS_TEST', 'false').lower() == 'true'

    # 获取限流配置
    rate_limit_config = getattr(config, 'rate_limit', None)
    rate_limit_info = RateLimitInfo(
        default_limits=getattr(rate_limit_config, 'default_limits', ["200 per minute", "1000 per hour"]) if rate_limit_config else ["200 per minute", "1000 per hour"],
        strict=getattr(rate_limit_config, 'strict', ["5 per minute", "20 per hour"]) if rate_limit_config else ["5 per minute", "20 per hour"],
        standard=getattr(rate_limit_config, 'standard', ["30 per minute", "500 per hour"]) if rate_limit_config else ["30 per minute", "500 per hour"],
        generous=getattr(rate_limit_config, 'generous', ["100 per minute", "2000 per hour"]) if rate_limit_config else ["100 per minute", "2000 per hour"],
        git_operations=getattr(rate_limit_config, 'git_operations', ["10 per minute", "100 per hour"]) if rate_limit_config else ["10 per minute", "100 per hour"],
        download=getattr(rate_limit_config, 'download', ["20 per minute", "200 per hour"]) if rate_limit_config else ["20 per minute", "200 per hour"]
    )

    return DebugStatusResponse(
        debug_mode=config.app.debug,
        config_path=config_path,
        config_exists=os.path.exists(config_path),
        database_url=config.database._mask_url(config.database.url),
        database_type=config.database.db_type,
        environment=env_info,
        stress_test_mode=stress_test_mode,
        rate_limit=rate_limit_info
    )


@router.post("/initdb", response_model=InitDbResponse)
async def init_database(
    force: bool = False,
    create_test_data: bool = True,
    _: None = Depends(require_debug_mode),
    current_user: User = Depends(require_admin)
):
    """
    重置数据库

    删除所有表并重新创建，可选创建测试数据

    Args:
        force: 是否强制重置（跳过确认提示，始终为 true）
        create_test_data: 是否创建测试数据

    Returns:
        InitDbResponse: 操作结果

    Raises:
        HTTPException: 非调试模式或权限不足时
    """
    config = get_config()
    start_time = datetime.now()
    
    try:
        # 获取数据库类型和 URL
        db_type = config.database.db_type
        db_url = config.database.url
        
        # 关闭现有的异步引擎（如果存在）
        try:
            from models.async_db import close_async_engine
            await close_async_engine()
        except Exception as e:
            logger.warning(f"关闭异步引擎时出错: {e}")
        
        # 关闭现有的同步引擎（如果存在）
        try:
            from models import engine as sync_engine
            if sync_engine:
                sync_engine.dispose()
        except Exception as e:
            logger.warning(f"关闭同步引擎时出错: {e}")
        
        # 强制垃圾回收
        gc.collect()
        
        # 对于 SQLite，删除数据库文件
        if db_type == "sqlite":
            db_path = db_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"已删除 SQLite 数据库文件: {db_path}")
        
        # 对于 PostgreSQL，删除所有表
        else:
            # 创建临时引擎用于删除表
            temp_engine = _get_sync_engine_with_url(db_url)
            try:
                if db_type == "postgresql":
                    _drop_all_tables_postgresql(temp_engine)
            finally:
                temp_engine.dispose()
        
        # 重新创建表
        initializer = DatabaseInitializer()
        success = initializer.create_tables()
        
        if not success:
            raise Exception("创建表失败")
        
        # 创建测试数据
        test_data_info = {}
        if create_test_data:
            initializer.create_test_data()
            test_data_info["test_data_created"] = True
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"数据库重置完成，耗时 {elapsed:.2f} 秒")
        
        return InitDbResponse(
            success=True,
            message=f"数据库重置成功 ({db_type})",
            details={
                "database_type": db_type,
                "elapsed_seconds": round(elapsed, 2),
                "test_data_created": create_test_data,
                **test_data_info
            }
        )
        
    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database reset failed: {str(e)}"
        )


@router.post("/initconf", response_model=InitConfResponse)
async def init_config(
    force: bool = False,
    backup: bool = True,
    _: None = Depends(require_debug_mode),
    current_user: User = Depends(require_admin)
):
    """
    重置配置文件

    删除当前配置文件并从 config.example.toml 恢复

    Args:
        force: 是否强制重置（跳过确认提示，始终为 true）
        backup: 是否备份原配置文件
        
    Returns:
        InitConfResponse: 操作结果
        
    Raises:
        HTTPException: 非调试模式或权限不足时
    """
    config_path = "config.toml"
    backup_path = None
    
    try:
        # 如果配置文件存在，进行备份
        if os.path.exists(config_path) and backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"config.toml.backup.{timestamp}"
            shutil.copy2(config_path, backup_path)
            logger.info(f"配置文件已备份到: {backup_path}")
        
        # 删除原配置文件
        if os.path.exists(config_path):
            os.remove(config_path)
            logger.info(f"已删除原配置文件: {config_path}")
        
        # 重置配置管理器单例
        reset_module_config_manager()
        
        # 重新初始化配置管理器（会自动生成默认配置）
        config_manager = ConfigManager(config_path)
        
        logger.info("配置文件已重置为默认值")
        
        return InitConfResponse(
            success=True,
            message="配置文件重置成功",
            config_path=config_path,
            backup_path=backup_path
        )
        
    except Exception as e:
        logger.error(f"配置文件重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config reset failed: {str(e)}"
        )
