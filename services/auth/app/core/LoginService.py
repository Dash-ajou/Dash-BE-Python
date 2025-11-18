import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Protocol

from libs.schemas import Member

from app.core.PhoneService import PhoneService, PhoneVerificationError, get_phone_service


class MemberRepositoryPort(Protocol):
    async def find_member_by_phone(self, phone: str) -> Member | None: ...

    async def find_member_by_id(self, member_id: int) -> Member | None: ...


class NullMemberRepository(MemberRepositoryPort):
    async def find_member_by_phone(self, phone: str) -> Member | None:
        return None

    async def find_member_by_id(self, member_id: int) -> Member | None:
        return None


@dataclass
class RefreshTokenEntry:
    member_id: int
    token: str
    expires_at: datetime


class RefreshTokenStorePort(Protocol):
    async def save_token(self, entry: RefreshTokenEntry) -> None: ...

    async def consume_token(self, token: str) -> RefreshTokenEntry | None: ...

    async def revoke_member_tokens(self, member_id: int) -> None: ...


class InMemoryRefreshTokenStore(RefreshTokenStorePort):
    def __init__(self):
        self._tokens: Dict[str, RefreshTokenEntry] = {}
        self._member_index: Dict[int, set[str]] = {}

    async def save_token(self, entry: RefreshTokenEntry) -> None:
        member_tokens = self._member_index.setdefault(entry.member_id, set())
        member_tokens.add(entry.token)
        self._tokens[entry.token] = entry

    async def consume_token(self, token: str) -> RefreshTokenEntry | None:
        entry = self._tokens.pop(token, None)
        if entry:
            member_tokens = self._member_index.get(entry.member_id)
            if member_tokens and token in member_tokens:
                member_tokens.remove(token)
        return entry

    async def revoke_member_tokens(self, member_id: int) -> None:
        tokens = self._member_index.pop(member_id, set())
        for token in tokens:
            self._tokens.pop(token, None)


@dataclass
class LoginTokens:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


class LoginError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class LoginService:
    ACCESS_TOKEN_TTL = timedelta(minutes=30)
    REFRESH_TOKEN_TTL = timedelta(days=7)

    def __init__(
        self,
        member_repository: MemberRepositoryPort | None = None,
        refresh_store: RefreshTokenStorePort | None = None,
        phone_service: PhoneService | None = None,
    ):
        self.member_repository = member_repository or NullMemberRepository()
        self.refresh_store = refresh_store or InMemoryRefreshTokenStore()
        self.phone_service = phone_service or get_phone_service()

    async def login_member(
        self,
        phone_auth_token: str | None,
        refresh_token: str | None,
    ) -> LoginTokens:
        if phone_auth_token:
            phone = await self._consume_phone_token(phone_auth_token)
            member = await self.member_repository.find_member_by_phone(phone)
            if member is None:
                raise LoginError("ERR-IVD-PARAM", "등록되지 않은 회원입니다.")
            member_id = member.memberId
        else:
            member_id = await self._consume_refresh_token(refresh_token)

        return await self._issue_tokens(member_id)

    async def _consume_phone_token(self, phone_auth_token: str) -> str:
        try:
            return await self.phone_service.consume_phone_auth_token(phone_auth_token)
        except PhoneVerificationError as exc:
            raise LoginError(exc.code, str(exc)) from exc

    async def _consume_refresh_token(self, refresh_token: str | None) -> int:
        if not refresh_token:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 필요합니다.")

        entry = await self.refresh_store.consume_token(refresh_token)
        if entry is None:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 유효하지 않습니다.")

        if entry.expires_at < datetime.now(timezone.utc):
            raise LoginError("ERR-IVD-PARAM", "refresh token이 만료되었습니다.")

        return entry.member_id

    async def _issue_tokens(self, member_id: int) -> LoginTokens:
        await self.refresh_store.revoke_member_tokens(member_id)
        now = datetime.now(timezone.utc)
        access_token = self._generate_access_token(member_id, now)
        refresh_token = self._generate_refresh_token(member_id, now)
        refresh_expires_at = now + self.REFRESH_TOKEN_TTL

        await self.refresh_store.save_token(
            RefreshTokenEntry(
                member_id=member_id,
                token=refresh_token,
                expires_at=refresh_expires_at,
            )
        )

        return LoginTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )

    def _generate_access_token(self, member_id: int, issued_at: datetime) -> str:
        payload = f"access:{member_id}:{issued_at.isoformat()}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _generate_refresh_token(self, member_id: int, issued_at: datetime) -> str:
        payload = f"refresh:{member_id}:{issued_at.isoformat()}:{secrets.token_urlsafe(32)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_MEMORY_REFRESH_STORE = InMemoryRefreshTokenStore()


def get_login_service(
    phone_service: PhoneService | None = None,
) -> LoginService:
    return LoginService(
        refresh_store=_MEMORY_REFRESH_STORE,
        phone_service=phone_service or get_phone_service(),
    )

