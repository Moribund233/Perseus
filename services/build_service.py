from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.build_status import BuildStatus, VALID_STATUSES
from core.exception import NotFoundException


class BuildService:

    @staticmethod
    async def create_build(
        db: AsyncSession,
        repo_id: uuid.UUID,
        branch: str,
        commit_sha: str,
        triggered_by: uuid.UUID,
        commit_message: Optional[str] = None,
    ) -> BuildStatus:
        build = BuildStatus(
            repo_id=repo_id,
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_message,
            status="pending",
            triggered_by=triggered_by,
        )
        db.add(build)
        await db.commit()
        await db.refresh(build)
        return build

    @staticmethod
    async def get_build(db: AsyncSession, build_id: uuid.UUID) -> BuildStatus:
        result = await db.execute(
            select(BuildStatus).filter(BuildStatus.id == build_id)
        )
        build = result.scalar_one_or_none()
        if not build:
            raise NotFoundException(detail="Build not found")
        return build

    @staticmethod
    async def get_builds_for_repository(
        db: AsyncSession,
        repo_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BuildStatus]:
        result = await db.execute(
            select(BuildStatus)
            .filter(BuildStatus.repo_id == repo_id)
            .order_by(desc(BuildStatus.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_build_status(
        db: AsyncSession,
        build_id: uuid.UUID,
        status: str,
        details_url: Optional[str] = None,
        logs: Optional[str] = None,
    ) -> BuildStatus:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Valid statuses: {', '.join(sorted(VALID_STATUSES))}")

        build = await BuildService.get_build(db=db, build_id=build_id)

        now = datetime.now(timezone.utc)
        build.status = status

        if status == "running" and build.started_at is None:
            build.started_at = now

        if status in ("success", "failure", "error", "cancelled") and build.finished_at is None:
            build.finished_at = now

        if details_url is not None:
            build.details_url = details_url
        if logs is not None:
            build.logs = logs

        await db.commit()
        await db.refresh(build)
        return build
