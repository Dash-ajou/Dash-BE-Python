import asyncio
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import text

from services.auth.app.core.LoginService import RefreshTokenEntry, RefreshTokenStorePort
from services.auth.app.db.session import SessionLocal


class SQLRefreshTokenStore(RefreshTokenStorePort):
    def __init__(self, session_factory: Callable[[], SessionLocal] = SessionLocal):
        self._session_factory = session_factory

    async def save_token(self, entry: RefreshTokenEntry) -> None:
        def _save():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO auth_refresh_tokens (
                            token,
                            subject_type,
                            subject_id,
                            expires_at,
                            created_at
                        ) VALUES (
                            :token,
                            :subject_type,
                            :subject_id,
                            :expires_at,
                            :created_at
                        )
                        ON DUPLICATE KEY UPDATE
                            subject_type = VALUES(subject_type),
                            subject_id = VALUES(subject_id),
                            expires_at = VALUES(expires_at),
                            created_at = VALUES(created_at)
                        """
                    ),
                    {
                        "token": entry.token,
                        "subject_type": entry.subject_type,
                        "subject_id": entry.subject_id,
                        "expires_at": entry.expires_at,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                session.commit()

        await asyncio.to_thread(_save)

    async def consume_token(self, token: str) -> RefreshTokenEntry | None:
        def _consume():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT subject_type, subject_id, expires_at
                            FROM auth_refresh_tokens
                            WHERE token = :token
                            LIMIT 1
                            """
                        ),
                        {"token": token},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                session.execute(
                    text("DELETE FROM auth_refresh_tokens WHERE token = :token"),
                    {"token": token},
                )
                session.commit()
                expires_at = row["expires_at"]
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                return RefreshTokenEntry(
                    subject_type=row["subject_type"],
                    subject_id=row["subject_id"],
                    token=token,
                    expires_at=expires_at,
                )

        return await asyncio.to_thread(_consume)

    async def revoke_subject_tokens(self, subject_type: str, subject_id: int) -> None:
        def _delete():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        DELETE FROM auth_refresh_tokens
                        WHERE subject_type = :subject_type
                          AND subject_id = :subject_id
                        """
                    ),
                    {"subject_type": subject_type, "subject_id": subject_id},
                )
                session.commit()

        await asyncio.to_thread(_delete)

