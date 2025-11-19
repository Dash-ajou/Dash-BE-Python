import asyncio
from datetime import datetime
from typing import Callable

from sqlalchemy import text

from libs.common import KST_TIMEZONE, now_kst
from services.auth.app.core.PhoneService import (
    PhoneAuthTokenEntry,
    PhoneAuthTokenStorePort,
    PhoneVerificationEntry,
    PhoneVerificationStorePort,
)
from services.auth.app.db.session import SessionLocal


class _SQLStoreBase:
    def __init__(self, session_factory: Callable[[], SessionLocal] = SessionLocal):
        self._session_factory = session_factory

    async def _run_in_thread(self, func):
        return await asyncio.to_thread(func)


class SQLPhoneVerificationStore(_SQLStoreBase, PhoneVerificationStorePort):
    async def save_request(self, request_hash: str, entry: PhoneVerificationEntry) -> None:
        def _upsert():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO phone_verification_requests (
                            request_hash,
                            phone,
                            code,
                            expires_at,
                            created_at
                        ) VALUES (
                            :request_hash,
                            :phone,
                            :code,
                            :expires_at,
                            :created_at
                        )
                        ON DUPLICATE KEY UPDATE
                            phone = VALUES(phone),
                            code = VALUES(code),
                            expires_at = VALUES(expires_at),
                            created_at = VALUES(created_at)
                        """
                    ),
                    {
                        "request_hash": request_hash,
                        "phone": entry.phone,
                        "code": entry.code,
                        "expires_at": entry.expires_at,
                        "created_at": now_kst(),
                    },
                )
                session.commit()

        await self._run_in_thread(_upsert)

    async def get_request(self, request_hash: str) -> PhoneVerificationEntry | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT phone, code, expires_at
                            FROM phone_verification_requests
                            WHERE request_hash = :request_hash
                            LIMIT 1
                            """
                        ),
                        {"request_hash": request_hash},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                expires_at = row["expires_at"]
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=KST_TIMEZONE)
                return PhoneVerificationEntry(
                    phone=row["phone"],
                    code=row["code"],
                    expires_at=expires_at,
                )

        return await self._run_in_thread(_query)

    async def delete_request(self, request_hash: str) -> None:
        def _delete():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        DELETE FROM phone_verification_requests
                        WHERE request_hash = :request_hash
                        """
                    ),
                    {"request_hash": request_hash},
                )
                session.commit()

        await self._run_in_thread(_delete)


class SQLPhoneAuthTokenStore(_SQLStoreBase, PhoneAuthTokenStorePort):
    async def save_token(self, token: str, entry: PhoneAuthTokenEntry) -> None:
        def _save():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO phone_auth_tokens (
                            token,
                            phone,
                            expires_at,
                            created_at
                        ) VALUES (
                            :token,
                            :phone,
                            :expires_at,
                            :created_at
                        )
                        ON DUPLICATE KEY UPDATE
                            phone = VALUES(phone),
                            expires_at = VALUES(expires_at),
                            created_at = VALUES(created_at)
                        """
                    ),
                    {
                        "token": token,
                        "phone": entry.phone,
                        "expires_at": entry.expires_at,
                        "created_at": now_kst(),
                    },
                )
                session.commit()

        await self._run_in_thread(_save)

    async def consume_token(self, token: str) -> PhoneAuthTokenEntry | None:
        def _consume():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT phone, expires_at
                            FROM phone_auth_tokens
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
                    text(
                        """
                        DELETE FROM phone_auth_tokens
                        WHERE token = :token
                        """
                    ),
                    {"token": token},
                )
                session.commit()
                expires_at = row["expires_at"]
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=KST_TIMEZONE)
                return PhoneAuthTokenEntry(
                    phone=row["phone"],
                    expires_at=expires_at,
                )

        return await self._run_in_thread(_consume)

