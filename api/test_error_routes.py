"""
错误处理测试路由

提供用于测试异常处理机制的端点，仅用于开发和测试环境
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_current_user, get_current_admin_user
from exception import (
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    DatabaseException,
)

router = APIRouter(prefix="/api/test/errors", tags=["test-errors"])


class ErrorResponse(BaseModel):
    """错误测试响应"""
    message: str
    error_type: str


@router.get("/validation", response_model=ErrorResponse)
async def trigger_validation_error():
    """
    触发验证异常 (400)

    用于测试 ValidationException 的处理
    """
    raise ValidationException("测试验证错误：参数格式不正确")


@router.get("/authentication", response_model=ErrorResponse)
async def trigger_authentication_error():
    """
    触发认证异常 (401)

    用于测试 AuthenticationException 的处理
    """
    raise AuthenticationException("测试认证错误：Token无效或已过期")


@router.get("/authorization", response_model=ErrorResponse)
async def trigger_authorization_error():
    """
    触发授权异常 (403)

    用于测试 AuthorizationException 的处理
    """
    raise AuthorizationException("测试授权错误：权限不足")


@router.get("/not-found", response_model=ErrorResponse)
async def trigger_not_found_error():
    """
    触发资源不存在异常 (404)

    用于测试 NotFoundException 的处理
    """
    raise NotFoundException("测试资源不存在错误：请求的资源未找到")


@router.get("/conflict", response_model=ErrorResponse)
async def trigger_conflict_error():
    """
    触发资源冲突异常 (409)

    用于测试 ConflictException 的处理
    """
    raise ConflictException("测试资源冲突错误：资源已存在")


@router.get("/database", response_model=ErrorResponse)
async def trigger_database_error():
    """
    触发数据库异常 (500)

    用于测试 DatabaseException 的处理
    """
    raise DatabaseException("测试数据库错误：数据库连接失败")


@router.get("/internal")
async def trigger_internal_error():
    """
    触发内部服务器错误 (500)

    用于测试未捕获的 Python 异常处理
    """
    # 故意触发一个除以零错误
    result = 1 / 0
    return {"message": "这行代码不会执行", "result": result}


@router.get("/key-error")
async def trigger_key_error():
    """
    触发 KeyError 异常 (500)

    用于测试字典键不存在的异常处理
    """
    data = {}
    value = data["不存在的键"]
    return {"message": "这行代码不会执行", "value": value}


@router.get("/type-error")
async def trigger_type_error():
    """
    触发 TypeError 异常 (500)

    用于测试类型错误的异常处理
    """
    result = "字符串" + 123
    return {"message": "这行代码不会执行", "result": result}


@router.get("/value-error")
async def trigger_value_error():
    """
    触发 ValueError 异常 (500)

    用于测试值错误的异常处理
    """
    value = int("不是数字")
    return {"message": "这行代码不会执行", "value": value}


@router.get("/attribute-error")
async def trigger_attribute_error():
    """
    触发 AttributeError 异常 (500)

    用于测试属性不存在的异常处理
    """
    class EmptyClass:
        pass

    obj = EmptyClass()
    value = obj.不存在的属性
    return {"message": "这行代码不会执行", "value": value}


@router.get("/http-exception")
async def trigger_http_exception():
    """
    触发 FastAPI HTTPException (418)

    用于测试 FastAPI 内置 HTTPException 的处理
    """
    raise HTTPException(status_code=418, detail="我是一个茶壶")


@router.get("/nested-error")
async def trigger_nested_error():
    """
    触发嵌套调用中的异常

    用于测试堆栈跟踪的完整性
    """
    def level_3():
        raise ValueError("嵌套调用中的错误")

    def level_2():
        level_3()

    def level_1():
        level_2()

    level_1()
    return {"message": "这行代码不会执行"}


@router.get("/protected-user")
async def protected_route_user(current_user=Depends(get_current_user)):
    """
    需要用户认证的路由

    用于测试认证后的错误信息返回
    """
    raise ValidationException("认证用户的验证错误")


@router.get("/protected-admin")
async def protected_route_admin(current_user=Depends(get_current_admin_user)):
    """
    需要管理员权限的路由

    用于测试管理员权限的错误信息返回
    """
    raise ValidationException("管理员的验证错误")
