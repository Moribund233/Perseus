from typing import Any, Dict, List, Optional, Sequence
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

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
    async def ensure_build_for_commit(
        db: AsyncSession,
        repo_id: uuid.UUID,
        branch: str,
        commit_sha: str,
        triggered_by: uuid.UUID,
        commit_message: Optional[str] = None,
    ) -> Optional[BuildStatus]:
        """
        按 (repo, branch, commit_sha) 去重建 build。

        已存在同 key 的 build（如 PR merge 已创建）时返回 None，避免重复触发。
        """
        result = await db.execute(
            select(BuildStatus).where(
                BuildStatus.repo_id == repo_id,
                BuildStatus.branch == branch,
                BuildStatus.commit_sha == commit_sha,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return None
        return await BuildService.create_build(
            db=db,
            repo_id=repo_id,
            branch=branch,
            commit_sha=commit_sha,
            triggered_by=triggered_by,
            commit_message=commit_message,
        )

    @staticmethod
    async def get_build(db: AsyncSession, build_id: uuid.UUID) -> BuildStatus:
        result = await db.execute(
            select(BuildStatus).filter(BuildStatus.id == build_id)
        )
        build = result.scalar_one_or_none()
        if not build:
            raise NotFoundException(detail="Build not found", error_code="build_not_found")
        return build

    @staticmethod
    async def get_builds_for_repository(
        db: AsyncSession,
        repo_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        branch: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BuildStatus]:
        stmt = select(BuildStatus).filter(BuildStatus.repo_id == repo_id)
        if branch:
            stmt = stmt.filter(BuildStatus.branch == branch)
        if status:
            stmt = stmt.filter(BuildStatus.status == status)
        stmt = stmt.order_by(desc(BuildStatus.created_at)).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_build_status(
        db: AsyncSession,
        build_id: uuid.UUID,
        status: str,
        details_url: Optional[str] = None,
        logs: Optional[str] = None,
        log_entries: Optional[List[Any]] = None,
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

        # log_entries: 增量追加到子表 (不再整串覆盖), 若回调同时带了整串 logs
        # 仍按旧语义落 build.logs; 子表是本功能的权威增量来源 (6.2 P2)
        if log_entries:
            await BuildService.append_build_log_entries(
                db=db, build_id=build_id, entries=log_entries
            )

        await db.commit()
        await db.refresh(build)
        return build

    @staticmethod
    async def append_build_log_entries(
        db: AsyncSession,
        build_id: uuid.UUID,
        entries: Sequence[Dict[str, str]],
    ) -> int:
        """追加写入 build_log_entries 子表, 返回新写入行的最大 seq。

        每批 entries 的 seq 都从“该 build 当前最大 seq + 1”开始, 批内依次 +1,
        保证外部 CI runner 分步回调的顺序在 seq 上单调递增 (增量边界 after_seq 的权威)。

        Args:
            db: 数据库会话
            build_id: 构建 ID (build_status.id)
            entries: [{stream, line}, ...]; stream 只接受 stdout/stderr

        Returns:
            int: 本批写入的最大 seq (若 entries 为空返回 0)
        """
        from models.build_log_entry import BuildLogEntry

        if not entries:
            return 0

        # 当前 build 的最大 seq —— 无行则为 0
        max_stmt = (
            select(func.max(BuildLogEntry.seq))
            .filter(BuildLogEntry.build_id == build_id)
        )
        max_res = await db.execute(max_stmt)
        current_max = max_res.scalar() or 0

        now = datetime.now(timezone.utc)
        rows = []
        for offset, entry in enumerate(entries, start=1):
            # pydantic LogEntryIn 模型或裸 dict 都兼容
            stream = getattr(entry, "stream", None) or entry.get("stream") or "stdout"
            if stream not in ("stdout", "stderr"):
                raise ValueError(
                    f"Invalid log stream: {stream!r}. Valid streams: stdout, stderr"
                )
            line = getattr(entry, "line", None) or entry.get("line") or ""
            rows.append(
                BuildLogEntry(
                    build_id=build_id,
                    seq=current_max + offset,
                    stream=stream,
                    line=line,
                    logged_at=now,
                )
            )

        db.add_all(rows)
        await db.flush()
        return current_max + len(rows)

    @staticmethod
    async def get_build_log_entries_after_seq(
        db: AsyncSession,
        build_id: uuid.UUID,
        after_seq: int,
        limit: int = 500,
    ) -> tuple[list[dict], int]:
        """增量拉取 build 日志子表：seq > after_seq 的行 + 下一个边界 seq。

        Returns:
            (entries, next_seq):
              entries 按 seq 升序，每条 {seq, stream, line, logged_at};
              next_seq 为返回条目最大 seq（若 after_seq 之后无新行则 == after_seq，
              调用方比对 next_seq>from_seq 判定是否有增量）。
        """
        from models.build_log_entry import BuildLogEntry

        stmt = (
            select(BuildLogEntry)
            .filter(
                BuildLogEntry.build_id == build_id,
                BuildLogEntry.seq > after_seq,
            )
            .order_by(BuildLogEntry.seq)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        entries = [
            {
                "seq": row.seq,
                "stream": row.stream,
                "line": row.line,
                "logged_at": row.logged_at.isoformat() if row.logged_at else None,
            }
            for row in rows
        ]
        next_seq = entries[-1]["seq"] if entries else after_seq
        return entries, next_seq
