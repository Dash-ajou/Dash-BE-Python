import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Protocol

from libs.schemas import Member, PartnerUser

from services.auth.app.core.PhoneService import PhoneService, PhoneVerificationError


class MemberRepositoryPort(Protocol):
    async def find_member_by_phone(self, phone: str) -> Member | None: ...

    async def find_member_by_id(self, member_id: int) -> Member | None: ...


class NullMemberRepository(MemberRepositoryPort):
    async def find_member_by_phone(self, phone: str) -> Member | None:
        return None

    async def find_member_by_id(self, member_id: int) -> Member | None:
        return None


class PartnerRepositoryPort(Protocol):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None: ...

    async def find_partner_by_id(self, partner_id: int) -> PartnerUser | None: ...


class PartnerPinRepositoryPort(Protocol):
    async def find_partner_id_by_pin_hash(self, pin_hash: str) -> int | None: ...


class NullPartnerRepository(PartnerRepositoryPort):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None:
        return None

    async def find_partner_by_id(self, partner_id: int) -> PartnerUser | None:
        return None


class NullPartnerPinRepository(PartnerPinRepositoryPort):
    async def find_partner_id_by_pin_hash(self, pin_hash: str) -> int | None:
        return None


@dataclass
class RefreshTokenEntry:
    subject_type: str
    subject_id: int
    token: str
    expires_at: datetime


class RefreshTokenStorePort(Protocol):
    async def save_token(self, entry: RefreshTokenEntry) -> None: ...

    async def consume_token(self, token: str) -> RefreshTokenEntry | None: ...

    async def revoke_subject_tokens(self, subject_type: str, subject_id: int) -> None: ...


class InMemoryRefreshTokenStore(RefreshTokenStorePort):
    def __init__(self):
        self._tokens: Dict[str, RefreshTokenEntry] = {}
        self._subject_index: Dict[tuple[str, int], set[str]] = {}

    async def save_token(self, entry: RefreshTokenEntry) -> None:
        key = (entry.subject_type, entry.subject_id)
        subject_tokens = self._subject_index.setdefault(key, set())
        subject_tokens.add(entry.token)
        self._tokens[entry.token] = entry

    async def consume_token(self, token: str) -> RefreshTokenEntry | None:
        entry = self._tokens.pop(token, None)
        if entry:
            key = (entry.subject_type, entry.subject_id)
            subject_tokens = self._subject_index.get(key)
            if subject_tokens and token in subject_tokens:
                subject_tokens.remove(token)
        return entry

    async def revoke_subject_tokens(self, subject_type: str, subject_id: int) -> None:
        key = (subject_type, subject_id)
        tokens = self._subject_index.pop(key, set())
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
    SUBJECT_MEMBER = "member"
    SUBJECT_PARTNER = "partner"

    def __init__(
        self,
        member_repository: MemberRepositoryPort | None = None,
        partner_repository: PartnerRepositoryPort | None = None,
        partner_pin_repository: PartnerPinRepositoryPort | None = None,
        refresh_store: RefreshTokenStorePort | None = None,
        phone_service: PhoneService | None = None,
    ):
        self.member_repository = member_repository or NullMemberRepository()
        self.partner_repository = partner_repository or NullPartnerRepository()
        self.partner_pin_repository = partner_pin_repository or NullPartnerPinRepository()
        self.refresh_store = refresh_store or InMemoryRefreshTokenStore()
        self.phone_service = phone_service or PhoneService()

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
            member_id = await self._consume_refresh_token(
                refresh_token, self.SUBJECT_MEMBER
            )

        return await self._issue_tokens(member_id, self.SUBJECT_MEMBER)

    async def login_partner(
        self,
        phone_auth_token: str | None,
        pin_hash: str | None,
        refresh_token: str | None,
    ) -> LoginTokens:
        if phone_auth_token:
            phone = await self._consume_phone_token(phone_auth_token)
            partner = await self.partner_repository.find_partner_by_phone(phone)
            if partner is None:
                raise LoginError("ERR-IVD-PARAM", "등록되지 않은 파트너입니다.")
            
            # PIN 검증이 필요한 경우 (phone_auth_token과 pin_hash가 함께 전달된 경우)
            if pin_hash:
                # pin_hash를 phone을 key로 사용하여 암호화 후 검증
                encrypted_pin_hash = self._encrypt_pin_with_phone(pin_hash, phone)
                verified_partner_id = await self._verify_partner_pin(encrypted_pin_hash)
                if verified_partner_id != partner.partnerId:
                    raise LoginError("ERR-IVD-PARAM", "PIN이 유효하지 않습니다.")
            
            partner_id = partner.partnerId
        elif pin_hash:
            # phone_auth_token 없이 pin_hash만 있는 경우는 지원하지 않음
            # (phone 정보가 필요하므로)
            raise LoginError("ERR-IVD-PARAM", "PIN 검증을 위해서는 휴대폰 인증이 필요합니다.")
        else:
            partner_id = await self._consume_refresh_token(
                refresh_token, self.SUBJECT_PARTNER
            )

        return await self._issue_tokens(partner_id, self.SUBJECT_PARTNER)

    async def _consume_phone_token(self, phone_auth_token: str) -> str:
        try:
            return await self.phone_service.consume_phone_auth_token(phone_auth_token)
        except PhoneVerificationError as exc:
            raise LoginError(exc.code, str(exc)) from exc

    async def _consume_refresh_token(
        self,
        refresh_token: str | None,
        subject_type: str,
    ) -> int:
        if not refresh_token:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 필요합니다.")

        entry = await self.refresh_store.consume_token(refresh_token)
        if entry is None:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 유효하지 않습니다.")

        if entry.subject_type != subject_type:
            raise LoginError("ERR-IVD-PARAM", "refresh token 대상이 일치하지 않습니다.")

        if entry.expires_at < datetime.now(timezone.utc):
            raise LoginError("ERR-IVD-PARAM", "refresh token이 만료되었습니다.")

        return entry.subject_id

    async def _issue_tokens(self, subject_id: int, subject_type: str) -> LoginTokens:
        await self.refresh_store.revoke_subject_tokens(subject_type, subject_id)
        now = datetime.now(timezone.utc)
        access_token = self._generate_access_token(subject_type, subject_id, now)
        refresh_token = self._generate_refresh_token(subject_type, subject_id, now)
        refresh_expires_at = now + self.REFRESH_TOKEN_TTL

        await self.refresh_store.save_token(
            RefreshTokenEntry(
                subject_type=subject_type,
                subject_id=subject_id,
                token=refresh_token,
                expires_at=refresh_expires_at,
            )
        )

        return LoginTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )

    def _generate_access_token(
        self,
        subject_type: str,
        subject_id: int,
        issued_at: datetime,
    ) -> str:
        payload = (
            f"access:{subject_type}:{subject_id}:{issued_at.isoformat()}:"
            f"{secrets.token_urlsafe(16)}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _generate_refresh_token(
        self,
        subject_type: str,
        subject_id: int,
        issued_at: datetime,
    ) -> str:
        payload = (
            f"refresh:{subject_type}:{subject_id}:{issued_at.isoformat()}:"
            f"{secrets.token_urlsafe(32)}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def _verify_partner_pin(self, encrypted_pin_hash: str) -> int:
        """
        암호화된 PIN 해시로 파트너 ID를 검증합니다.
        
        Args:
            encrypted_pin_hash: phone을 key로 암호화된 PIN 해시 값
            
        Returns:
            파트너 ID
        """
        partner_id = await self.partner_pin_repository.find_partner_id_by_pin_hash(
            encrypted_pin_hash
        )
        if partner_id is None:
            raise LoginError("ERR-IVD-PARAM", "PIN이 유효하지 않습니다.")
        return partner_id

    @staticmethod
    def _encrypt_pin_with_phone(pin_hash: str, phone: str) -> str:
        """
        pin_hash를 phone을 key로 사용하여 단방향 암호화 (HMAC-SHA256)
        JoinService와 동일한 로직 사용
        
        Args:
            pin_hash: 암호화할 PIN 해시 값
            phone: 암호화 키로 사용할 전화번호
            
        Returns:
            HMAC-SHA256으로 암호화된 PIN 해시 값 (hex 문자열)
        """
        return hmac.new(
            phone.encode('utf-8'),
            pin_hash.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()


