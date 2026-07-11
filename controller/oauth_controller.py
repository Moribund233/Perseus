from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from core.config import get_config
from core.exception import AuthenticationException, NotFoundException
from models.async_db import get_async_db
from models.user import User
from services.oauth_service import OAuthService

router = APIRouter(prefix=get_route_prefix("auth"), tags=["oauth"])

# OAuth account management - under /users prefix for RESTful resource hierarchy
account_router = APIRouter(prefix=get_route_prefix("users"), tags=["oauth-accounts"])


def _get_oauth_service():
    return OAuthService(get_config())


@router.get("/{provider}/login")
async def oauth_login(provider: str):
    service = _get_oauth_service()
    try:
        return service.initiate_login(provider)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_async_db),
):
    service = _get_oauth_service()
    try:
        return await service.handle_callback(db, provider, code, state)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@account_router.get("/me/oauth")
async def list_linked_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _get_oauth_service()
    return await service.list_linked_accounts(db, current_user.id)


@account_router.delete("/me/oauth/{provider}")
async def unlink_account(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _get_oauth_service()
    try:
        await service.unlink_account(db, current_user.id, provider)
        return {"detail": f"{provider} account unlinked"}
    except NotFoundException:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Linked {provider} account not found")
