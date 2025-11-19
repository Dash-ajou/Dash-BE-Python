import asyncio
import re
from datetime import datetime
from typing import Callable

from sqlalchemy import text

from libs.common import KST_TIMEZONE, ensure_kst, now_kst
from libs.schemas import Member, PartnerUser

from services.auth.app.db.session import SessionLocal


def _ensure_timezone(value: datetime | None) -> datetime | None:
    """KST 시간대를 보장하는 함수 (기존 _ensure_timezone과 동일한 역할)"""
    return ensure_kst(value)


def _format_date_to_string(date_value) -> str:
    """DATE 또는 datetime 객체를 YYYY-MM-DD 형식의 문자열로 변환"""
    if date_value is None:
        return ""
    if hasattr(date_value, 'strftime'):
        # date 또는 datetime 객체인 경우
        return date_value.strftime("%Y-%m-%d")
    return str(date_value)


def _normalize_date(date_str: str) -> str:
    """
    다양한 날짜 형식을 YYYY-MM-DD 형식으로 정규화
    
    지원 형식:
    - '2002. 11. 27' -> '2002-11-27'
    - '2002-11-27' -> '2002-11-27'
    - '2002/11/27' -> '2002-11-27'
    - '2002.11.27' -> '2002-11-27'
    """
    if not date_str:
        raise ValueError("날짜 값이 비어있습니다.")
    
    # 숫자만 추출 (YYYY, MM, DD)
    digits = re.findall(r'\d+', date_str)
    if len(digits) < 3:
        raise ValueError(f"날짜 형식이 올바르지 않습니다: {date_str}")
    
    year = digits[0].zfill(4)  # 4자리로 맞춤
    month = digits[1].zfill(2)  # 2자리로 맞춤
    day = digits[2].zfill(2)  # 2자리로 맞춤
    
    # 유효성 검사
    try:
        datetime(int(year), int(month), int(day))
    except ValueError as e:
        raise ValueError(f"유효하지 않은 날짜입니다: {date_str}") from e
    
    return f"{year}-{month}-{day}"


class _SQLRepositoryBase:
    def __init__(self, session_factory: Callable[[], SessionLocal] = SessionLocal):
        self._session_factory = session_factory

    async def _run_in_thread(self, func: Callable[[], Member | PartnerUser | int | None | bool]):
        return await asyncio.to_thread(func)
    
    async def phone_exists(self, phone: str) -> bool:
        """phones 테이블에 해당 전화번호가 등록되어 있는지 확인 (MEMBER/PARTNER 구분 없이)"""
        def _query():
            with self._session_factory() as session:
                result = session.execute(
                    text(
                        """
                        SELECT EXISTS(
                            SELECT 1
                            FROM phones
                            WHERE number = :phone
                        ) as exists_flag
                        """
                    ),
                    {"phone": phone},
                ).scalar()
                return bool(result)
        
        return await self._run_in_thread(_query)


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
                    memberBirth=_format_date_to_string(row["member_birth"]),
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
                    memberBirth=_format_date_to_string(row["member_birth"]),
                    groups=[],
                    createdAt=_ensure_timezone(row["created_at"]),
                )

        return await self._run_in_thread(_query)

    async def get_member_with_details(self, member_id: int) -> tuple[Member, str, list[dict]] | None:
        """
        회원 정보와 전화번호, 그룹 정보를 함께 조회합니다.
        
        Returns:
            (Member, phone, groups) 튜플 또는 None
            groups는 [{"groupId": str, "groupName": str | None}] 형식
        """
        def _query():
            with self._session_factory() as session:
                # 1. 회원 기본 정보 조회
                member_row = (
                    session.execute(
                        text(
                            """
                            SELECT
                                m.member_id,
                                m.member_name,
                                m.member_birth,
                                m.created_at
                            FROM members m
                            WHERE m.member_id = :member_id
                            LIMIT 1
                            """
                        ),
                        {"member_id": member_id},
                    )
                    .mappings()
                    .first()
                )
                if member_row is None:
                    return None

                # 2. 전화번호 조회
                phone_row = (
                    session.execute(
                        text(
                            """
                            SELECT p.number
                            FROM phones p
                            WHERE p.contact_account_type = 'MEMBER'
                              AND p.account_id = :member_id
                            LIMIT 1
                            """
                        ),
                        {"member_id": member_id},
                    )
                    .mappings()
                    .first()
                )
                phone = phone_row["number"] if phone_row else ""

                # 3. 그룹 정보 조회
                group_rows = (
                    session.execute(
                        text(
                            """
                            SELECT
                                g.group_id,
                                g.group_name
                            FROM member_groups mg
                            INNER JOIN `groups` g ON g.group_id = mg.group_id
                            WHERE mg.member_id = :member_id
                            ORDER BY g.group_id
                            """
                        ),
                        {"member_id": member_id},
                    )
                    .mappings()
                    .all()
                )
                groups = [
                    {
                        "groupId": str(row["group_id"]),
                        "groupName": row["group_name"],
                    }
                    for row in group_rows
                ]

                member = Member(
                    memberId=member_row["member_id"],
                    memberName=member_row["member_name"],
                    memberBirth=_format_date_to_string(member_row["member_birth"]),
                    groups=[],  # groups는 별도로 반환
                    createdAt=_ensure_timezone(member_row["created_at"]),
                )

                return (member, phone, groups)

        return await self._run_in_thread(_query)

    async def update_phone(self, account_id: int, new_phone: str) -> None:
        """회원의 전화번호를 업데이트합니다."""
        def _update():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        UPDATE phones
                        SET number = :new_phone
                        WHERE contact_account_type = 'MEMBER'
                          AND account_id = :account_id
                        """
                    ),
                    {"new_phone": new_phone, "account_id": account_id},
                )
                session.commit()

        return await self._run_in_thread(_update)

    async def update_groups(self, member_id: int, group_ids: list[str]) -> None:
        """회원의 소속정보를 업데이트합니다. 기존 그룹을 모두 삭제하고 새로 추가합니다."""
        def _update():
            with self._session_factory() as session:
                # 1. 기존 그룹 관계 모두 삭제
                session.execute(
                    text(
                        """
                        DELETE FROM member_groups
                        WHERE member_id = :member_id
                        """
                    ),
                    {"member_id": member_id},
                )

                # 2. 새로운 그룹 관계 추가
                if group_ids and len(group_ids) > 0:
                    member_group_query = text(
                        """
                        INSERT INTO member_groups (member_id, group_id, created_at)
                        VALUES (:member_id, :group_id, :created_at)
                        """
                    )
                    for group_id in group_ids:
                        session.execute(
                            member_group_query,
                            {
                                "member_id": member_id,
                                "group_id": group_id,
                                "created_at": now_kst(),
                            },
                        )

                session.commit()

        return await self._run_in_thread(_update)

    async def validate_group_ids(self, group_ids: list[str]) -> bool:
        """그룹 ID 목록이 모두 유효한지 검증합니다."""
        if not group_ids:
            return True  # 빈 리스트는 유효함

        def _validate():
            with self._session_factory() as session:
                # 전달된 group_ids가 모두 groups 테이블에 존재하는지 확인
                result = session.execute(
                    text(
                        """
                        SELECT COUNT(*) as count
                        FROM `groups`
                        WHERE group_id IN :group_ids
                        """
                    ),
                    {"group_ids": tuple(group_ids)},
                )
                row = result.mappings().first()
                valid_count = row["count"] if row else 0
                return valid_count == len(group_ids)

        return await self._run_in_thread(_validate)

    async def create_member(
        self, member_name: str, member_birth: str, phone: str, group_ids: list[str] | None = None
    ) -> int:
        # None인 경우 빈 리스트로 변환
        if group_ids is None:
            group_ids = []
        def _create():
            with self._session_factory() as session:
                # 날짜 형식 정규화 (YYYY-MM-DD)
                normalized_birth = _normalize_date(member_birth)
                
                # 1. Member 생성
                member_query = text(
                    """
                    INSERT INTO members (member_name, member_birth, created_at)
                    VALUES (:member_name, :member_birth, :created_at)
                    """
                )
                result = session.execute(
                    member_query,
                    {
                        "member_name": member_name,
                        "member_birth": normalized_birth,
                        "created_at": now_kst(),
                    },
                )
                member_id = result.lastrowid

                # 2. Phone 생성
                phone_query = text(
                    """
                    INSERT INTO phones (contact_account_type, account_id, number, created_at)
                    VALUES ('MEMBER', :account_id, :number, :created_at)
                    """
                )
                session.execute(
                    phone_query,
                    {
                        "account_id": member_id,
                        "number": phone,
                        "created_at": now_kst(),
                    },
                )

                # 3. Member-Group 관계 생성
                if group_ids and len(group_ids) > 0:
                    member_group_query = text(
                        """
                        INSERT INTO member_groups (member_id, group_id, created_at)
                        VALUES (:member_id, :group_id, :created_at)
                        """
                    )
                    for group_id in group_ids:
                        session.execute(
                            member_group_query,
                            {
                                "member_id": member_id,
                                "group_id": group_id,
                                "created_at": now_kst(),
                            },
                        )

                session.commit()
                return member_id

        return await self._run_in_thread(_create)


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

    async def update_phone(self, account_id: int, new_phone: str) -> None:
        """파트너의 전화번호를 업데이트합니다."""
        def _update():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        UPDATE phones
                        SET number = :new_phone
                        WHERE contact_account_type = 'PARTNER'
                          AND account_id = :account_id
                        """
                    ),
                    {"new_phone": new_phone, "account_id": account_id},
                )
                session.commit()

        return await self._run_in_thread(_update)

    async def create_partner(
        self, user_name: str, partner_name: str, phone: str, pin_hash: str
    ) -> int:
        def _create():
            with self._session_factory() as session:
                # 1. PartnerUser 생성
                partner_query = text(
                    """
                    INSERT INTO partner_users (partner_name, created_at)
                    VALUES (:partner_name, :created_at)
                    """
                )
                result = session.execute(
                    partner_query,
                    {
                        "partner_name": partner_name,
                        "created_at": now_kst(),
                    },
                )
                partner_id = result.lastrowid

                # 2. Phone 생성
                phone_query = text(
                    """
                    INSERT INTO phones (contact_account_type, account_id, number, created_at)
                    VALUES ('PARTNER', :account_id, :number, :created_at)
                    """
                )
                session.execute(
                    phone_query,
                    {
                        "account_id": partner_id,
                        "number": phone,
                        "created_at": now_kst(),
                    },
                )

                # 3. PartnerPin 생성
                pin_query = text(
                    """
                    INSERT INTO partner_pins (partner_id, pin, created_at)
                    VALUES (:partner_id, :pin, :created_at)
                    """
                )
                session.execute(
                    pin_query,
                    {
                        "partner_id": partner_id,
                        "pin": pin_hash,
                        "created_at": now_kst(),
                    },
                )

                session.commit()
                return partner_id

        return await self._run_in_thread(_create)

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

    async def get_partner_phone(self, partner_id: int) -> str | None:
        """파트너의 전화번호를 조회합니다."""
        def _query():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT p.number
                            FROM phones p
                            WHERE p.contact_account_type = 'PARTNER'
                              AND p.account_id = :partner_id
                            LIMIT 1
                            """
                        ),
                        {"partner_id": partner_id},
                    )
                    .mappings()
                    .first()
                )
                return row["number"] if row else None

        return await self._run_in_thread(_query)

    async def update_pin(self, partner_id: int, encrypted_pin_hash: str) -> None:
        """파트너의 PIN을 업데이트합니다."""
        def _update():
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        UPDATE partner_pins
                        SET pin = :pin_hash
                        WHERE partner_id = :partner_id
                        """
                    ),
                    {"pin_hash": encrypted_pin_hash, "partner_id": partner_id},
                )
                session.commit()

        return await self._run_in_thread(_update)

    async def get_partner_phones(self, partner_id: int) -> list[str]:
        """파트너의 모든 전화번호를 조회합니다."""
        def _query():
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        text(
                            """
                            SELECT p.number
                            FROM phones p
                            WHERE p.contact_account_type = 'PARTNER'
                              AND p.account_id = :partner_id
                            ORDER BY p.phone_id
                            """
                        ),
                        {"partner_id": partner_id},
                    )
                    .mappings()
                    .all()
                )
                return [row["number"] for row in rows]

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
                            WHERE pin = :pin_hash
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

