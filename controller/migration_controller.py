"""
数据库迁移控制器

提供迁移预检查和执行的API接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from models.user import User
from api.dependencies import get_current_user, get_current_admin_user
from utils.migration_precheck import run_precheck_from_env, PrecheckReport
from services.migration_service import run_migration_from_env, MigrationResult

router = APIRouter(prefix="/api/v1/migration", tags=["migration"])

security = HTTPBearer(auto_error=False)


class PrecheckRequest(BaseModel):
    """预检查请求"""
    target_url: str = Field(..., description="目标数据库连接URL")


class MigrationRequest(BaseModel):
    """迁移请求"""
    target_url: str = Field(..., description="目标数据库连接URL")
    batch_size: int = Field(default=1000, ge=100, le=10000, description="批量大小")
    tables: Optional[List[str]] = Field(default=None, description="要迁移的表名列表，None表示迁移所有表")


class PrecheckResponse(BaseModel):
    """预检查响应"""
    source_db_type: str
    target_db_type: str
    passed: bool
    is_synced: bool = Field(default=False, description="数据库是否已同步")
    sync_details: Optional[Dict[str, Any]] = Field(default=None, description="同步详情")
    summary: Dict[str, int]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    infos: List[Dict[str, Any]]


class MigrationResponse(BaseModel):
    """迁移响应"""
    success: bool
    tables_migrated: int
    tables_failed: int
    total_rows_migrated: int
    total_rows_failed: int
    duration_seconds: float
    table_progress: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    skipped: bool = Field(default=False, description="是否被跳过")
    skip_reason: Optional[str] = Field(default=None, description="跳过原因")


@router.post(
    "/precheck",
    summary="执行迁移预检查",
    response_model=PrecheckResponse,
    status_code=status.HTTP_200_OK
)
async def precheck(
    request: PrecheckRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    执行数据库迁移预检查
    
    检查源数据库和目标数据库之间的兼容性，包括：
    - 连接测试
    - 驱动检查
    - 表结构兼容性
    - 数据类型兼容性
    
    **需要管理员权限**
    
    Args:
        request: 预检查请求，包含目标数据库URL
        current_user: 当前管理员用户
    
    Returns:
        PrecheckResponse: 预检查结果
    
    Raises:
        HTTPException: 预检查失败时抛出
    """
    try:
        report = run_precheck_from_env(request.target_url)
        
        return PrecheckResponse(
            source_db_type=report.source_db_type,
            target_db_type=report.target_db_type,
            passed=report.passed,
            is_synced=report.is_synced,
            sync_details=report.sync_details,
            summary=report.to_dict()["summary"],
            errors=[r.__dict__ for r in report.errors],
            warnings=[r.__dict__ for r in report.warnings],
            infos=[r.__dict__ for r in report.infos]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预检查执行失败: {str(e)}"
        )


@router.post(
    "/execute",
    summary="执行数据库迁移",
    response_model=MigrationResponse,
    status_code=status.HTTP_200_OK
)
async def execute_migration(
    request: MigrationRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    执行数据库迁移
    
    将源数据库的数据迁移到目标数据库，包括：
    - 自动创建表结构
    - 批量迁移数据
    - ON CONFLICT DO NOTHING 处理冲突
    
    **注意：迁移过程不会阻塞服务正常运行**
    
    **需要管理员权限**
    
    Args:
        request: 迁移请求
        current_user: 当前管理员用户
    
    Returns:
        MigrationResponse: 迁移结果
    
    Raises:
        HTTPException: 迁移失败时抛出
    """
    try:
        result = run_migration_from_env(
            target_url=request.target_url,
            batch_size=request.batch_size,
            tables=request.tables
        )
        
        return MigrationResponse(
            success=result.success,
            tables_migrated=result.tables_migrated,
            tables_failed=result.tables_failed,
            total_rows_migrated=result.total_rows_migrated,
            total_rows_failed=result.total_rows_failed,
            duration_seconds=result.duration_seconds,
            table_progress=[
                {
                    "table_name": p.table_name,
                    "total_rows": p.total_rows,
                    "migrated_rows": p.migrated_rows,
                    "status": p.status,
                    "started_at": p.started_at.isoformat() if p.started_at else None,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                    "error_message": p.error_message
                }
                for p in result.table_progress
            ],
            errors=result.errors,
            skipped=getattr(result, 'skipped', False),
            skip_reason=getattr(result, 'skip_reason', None)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"迁移执行失败: {str(e)}"
        )


@router.get(
    "/status",
    summary="获取迁移状态",
    status_code=status.HTTP_200_OK
)
async def get_migration_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取迁移服务状态
    
    **需要管理员权限**
    """
    from core.config import get_config
    config = get_config()
    
    return {
        "source_db_type": config.database.db_type,
        "source_url": "使用环境变量 DATABASE_URL",
        "migration_available": True
    }
