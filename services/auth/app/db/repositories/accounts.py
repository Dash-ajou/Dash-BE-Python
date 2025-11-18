import asyncio
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import text

from libs.schemas import Member, PartnerUser

from services.auth.app.db.session import SessionLocal


def _ensure_timezone(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class _SQLRepositoryBase:
    def __init__(self, session_factory: Callable[[], SessionLocal] = SessionLocal):
        self._session_factory = session_factory

    async def _run_in_thread(self, func: Callable[[], Member | PartnerUser | int | None]):
        return await asyncio.to_thread(func)


class SQLAlchemyMemberRepository(_SQLRepositoryBase):
    async def find_member_by_phone(self, phone: str) -> Member | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT
                                m.member_id,
                                m.member_name,
                                m.member_birth,
                                m.created_at
                            FROM members m
                            INNER JOIN phones p ON p.account_id = m.member_id
                            WHERE p.contact_account_type = 'MEMBER'
                              AND p.number = :phone
                            LIMIT 1
                            """
                        ),
                        {"phone": phone},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                return Member(
                    memberId=row["member_id"],
                    memberName=row["member_name"],
                    memberBirth=row["member_birth"],
                    groups=[],
                    createdAt=_ensure_timezone(row["created_at"]),
                )

        return await self._run_in_thread(_query)

    async def find_member_by_id(self, member_id: int) -> Member | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT
                                member_id,
                                member_name,
                                member_birth,
                                created_at
                            FROM members
                            WHERE member_id = :member_id
                            LIMIT 1
                            """
                        ),
                        {"member_id": member_id},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                return Member(
                    memberId=row["member_id"],
                    memberName=row["member_name"],
                    memberBirth=row["member_birth"],
                    groups=[],
                    createdAt=_ensure_timezone(row["created_at"]),
                )

        return await self._run_in_thread(_query)


class SQLAlchemyPartnerRepository(_SQLRepositoryBase):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT
                                pu.partner_id,
                                pu.partner_name,
                                pu.created_at
                            FROM partner_users pu
                            INNER JOIN phones p ON p.account_id = pu.partner_id
                            WHERE p.contact_account_type = 'PARTNER'
                              AND p.number = :phone
                            LIMIT 1
                            """
                        ),
                        {"phone": phone},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                return PartnerUser(
                    partnerId=row["partner_id"],
                    partnerName=row["partner_name"],
                    createdAt=_ensure_timezone(row["created_at"]),
                )

        return await self._run_in_thread(_query)

    async def find_partner_by_id(self, partner_id: int) -> PartnerUser | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT
                                partner_id,
                                partner_name,
                                created_at
                            FROM partner_users
                            WHERE partner_id = :partner_id
                            LIMIT 1
                            """
                        ),
                        {"partner_id": partner_id},
                    )
                    .mappings()
                    .first()
                )
                if row is None:
                    return None
                return PartnerUser(
                    partnerId=row["partner_id"],
                    partnerName=row["partner_name"],
                    createdAt=_ensure_timezone(row["created_at"]),
                )

        return await self._run_in_thread(_query)


class SQLAlchemyPartnerPinRepository(_SQLRepositoryBase):
    async def find_partner_id_by_pin_hash(self, pin_hash: str) -> int | None:
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT partner_id
                            FROM partner_pins
                            WHERE pin_hash = :pin_hash
                            LIMIT 1
                            """
                        ),
                        {"pin_hash": pin_hash},
                    )
                    .mappings()
                    .first()
                )
                return None if row is None else row["partner_id"]

        return await self._run_in_thread(_query)


class DatabasePhoneAccountLookup:
    def __init__(
        self,
        member_repository: SQLAlchemyMemberRepository,
        partner_repository: SQLAlchemyPartnerRepository,
    ):
        self.member_repository = member_repository
        self.partner_repository = partner_repository

    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None:
        return await self.partner_repository.find_partner_by_phone(phone)

    async def find_member_by_phone(self, phone: str) -> Member | None:
        return await self.member_repository.find_member_by_phone(phone)

