import hashlib
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Protocol

from libs.common import now_kst
from libs.schemas import Member, PartnerUser
from services.auth.app.db.connection import settings

logger = logging.getLogger(__name__)


class PhoneAccountLookupPort(Protocol):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None: ...

    async def find_member_by_phone(self, phone: str) -> Member | None: ...


class NullPhoneAccountRepository:
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None:
        return None

    async def find_member_by_phone(self, phone: str) -> Member | None:
        return None


@dataclass
class PhoneVerificationResult:
    is_used: bool
    user_type: str | None
    login_request_hash: str | None
    hash_expiration: datetime | None


@dataclass
class PhoneVerificationEntry:
    phone: str
    code: str
    expires_at: datetime


class PhoneVerificationStorePort(Protocol):
    async def save_request(self, request_hash: str, entry: PhoneVerificationEntry) -> None: ...

    async def get_request(self, request_hash: str) -> PhoneVerificationEntry | None: ...

    async def delete_request(self, request_hash: str) -> None: ...


class InMemoryPhoneVerificationStore(PhoneVerificationStorePort):
    def __init__(self):
        self._store: Dict[str, PhoneVerificationEntry] = {}

    async def save_request(self, request_hash: str, entry: PhoneVerificationEntry) -> None:
        self._store[request_hash] = entry

    async def get_request(self, request_hash: str) -> PhoneVerificationEntry | None:
        entry = self._store.get(request_hash)
        if entry and entry.expires_at < now_kst():
            await self.delete_request(request_hash)
            return None
        return entry

    async def delete_request(self, request_hash: str) -> None:
        self._store.pop(request_hash, None)


class PhoneVerificationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class PhoneAuthTokenEntry:
    phone: str
    expires_at: datetime


class PhoneAuthTokenStorePort(Protocol):
    async def save_token(self, token: str, entry: PhoneAuthTokenEntry) -> None: ...

    async def consume_token(self, token: str) -> PhoneAuthTokenEntry | None: ...


class InMemoryPhoneAuthTokenStore(PhoneAuthTokenStorePort):
    def __init__(self):
        self._store: Dict[str, PhoneAuthTokenEntry] = {}

    async def save_token(self, token: str, entry: PhoneAuthTokenEntry) -> None:
        self._store[token] = entry

    async def consume_token(self, token: str) -> PhoneAuthTokenEntry | None:
        entry = self._store.pop(token, None)
        if entry and entry.expires_at < now_kst():
            return None
        return entry


class PhoneService:
    """
    휴대폰 관련 비즈니스 로직을 처리하는 서비스.
    """

    USER_TYPE_PERSONAL = "USER_TYPE/PERSONAL"
    USER_TYPE_PARTNER = "USER_TYPE/PARTNER"

    def __init__(
        self,
        account_lookup: PhoneAccountLookupPort | None = None,
        verification_store: PhoneVerificationStorePort | None = None,
        phone_auth_store: PhoneAuthTokenStorePort | None = None,
        sms_sender: Callable[[str, str], None] | None = None,
    ):
        self.account_lookup = account_lookup or NullPhoneAccountRepository()
        self.verification_store = verification_store or InMemoryPhoneVerificationStore()
        self.phone_auth_store = phone_auth_store or InMemoryPhoneAuthTokenStore()
        self._sms_sender = sms_sender or sendMessage

    async def request_phone_verification(self, raw_phone: str) -> PhoneVerificationResult:
        normalized_phone = self._normalize_phone(raw_phone)
        partner = await self.account_lookup.find_partner_by_phone(normalized_phone)

        if partner is not None:
            return PhoneVerificationResult(
                is_used=True,
                user_type=self.USER_TYPE_PARTNER,
                login_request_hash=None,
                hash_expiration=None,
            )

        member = await self.account_lookup.find_member_by_phone(normalized_phone)
        request_hash, expires_at = self._build_login_request_hash(normalized_phone)

        code = self._generate_auth_code()
        await self.verification_store.save_request(
            request_hash,
            PhoneVerificationEntry(phone=normalized_phone, code=code, expires_at=expires_at),
        )
        self._send_auth_message(normalized_phone, code)

        return PhoneVerificationResult(
            is_used=member is not None,
            user_type=self.USER_TYPE_PERSONAL if member else None,
            login_request_hash=request_hash,
            hash_expiration=expires_at,
        )

    async def verify_phone_code(self, login_request_hash: str | None, code: str) -> str:
        if not login_request_hash:
            raise PhoneVerificationError("ERR-MISSING-HASH", "인증요청 식별자가 없습니다.")

        entry = await self.verification_store.get_request(login_request_hash)
        if entry is None:
            raise PhoneVerificationError("ERR-REQ-NOT-FOUND", "인증요청 정보가 존재하지 않습니다.")

        if entry.expires_at < now_kst():
            await self.verification_store.delete_request(login_request_hash)
            raise PhoneVerificationError("ERR-REQ-EXPIRED", "인증요청이 만료되었습니다.")

        if entry.code != code:
            raise PhoneVerificationError("ERR-IVD-VALUE", "인증번호가 일치하지 않습니다.")

        await self.verification_store.delete_request(login_request_hash)
        return await self._issue_phone_auth_token(entry.phone)

    async def consume_phone_auth_token(self, phone_auth_token: str | None) -> str:
        if not phone_auth_token:
            raise PhoneVerificationError("ERR-MISSING-PHONE-AUTH", "휴대폰 인증 토큰이 없습니다.")

        entry = await self.phone_auth_store.consume_token(phone_auth_token)
        if entry is None:
            raise PhoneVerificationError("ERR-IVD-PARAM", "휴대폰 인증 토큰이 유효하지 않습니다.")

        if entry.expires_at < now_kst():
            raise PhoneVerificationError("ERR-PHONE-AUTH-EXPIRED", "휴대폰 인증 토큰이 만료되었습니다.")

        return entry.phone

    def _send_auth_message(self, normalized_phone: str, code: str) -> None:
        masked_phone = self._mask_phone(normalized_phone)
        content = f"[Dash] 인증번호: {code}"
        logger.debug("Sending verification SMS to %s", masked_phone)
        self._sms_sender(normalized_phone, content)

    @staticmethod
    def _normalize_phone(raw_phone: str) -> str:
        digits = re.sub(r"\D", "", raw_phone or "")
        if not digits:
            raise ValueError("휴대폰 번호가 유효하지 않습니다.")
        return digits

    @staticmethod
    def _build_login_request_hash(phone: str) -> tuple[str, datetime]:
        requested_at = now_kst()
        payload = f"{phone}:{requested_at.isoformat()}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest, requested_at + timedelta(minutes=5)

    @staticmethod
    def _generate_auth_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    async def _issue_phone_auth_token(self, phone: str) -> str:
        payload = f"{phone}:{now_kst().isoformat()}:{secrets.token_urlsafe(8)}"
        token = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        expires_at = now_kst() + timedelta(minutes=10)
        await self.phone_auth_store.save_token(
            token,
            PhoneAuthTokenEntry(phone=phone, expires_at=expires_at),
        )
        return token

    @staticmethod
    def _mask_phone(phone: str) -> str:
        if len(phone) < 4:
            return "*" * len(phone)
        return f"{phone[:-4]}****"


def sendMessage(phone: str, content: str) -> None:
    """
    SOLAPI를 사용하여 SMS를 발송하는 함수.
    
    Args:
        phone: 수신번호 (01000000000 형식, (-) 제외)
        content: 발송할 메시지 내용
    """
    try:
        # SOLAPI 패키지 import (선택적 import로 패키지가 없어도 동작하도록)
        from solapi import SolapiMessageService
        from solapi.model import RequestMessage
        
        # 환경 변수에서 API 키와 Secret 가져오기
        api_key = settings.SOLAPI_API_KEY
        api_secret = settings.SOLAPI_API_SECRET
        sender_number = settings.SOLAPI_SENDER_NUMBER
        
        # 환경 변수가 설정되지 않은 경우 로그만 출력
        if not api_key or not api_secret or not sender_number:
            logger.warning(
                "[SMS] SOLAPI 설정이 완료되지 않았습니다. 환경 변수를 확인하세요. "
                "(SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_SENDER_NUMBER)"
            )
            logger.info("[SMS] 수신번호: %s, 내용: %s", phone, content)
            return
        
        # SOLAPI 메시지 서비스 초기화
        message_service = SolapiMessageService(
            api_key=api_key,
            api_secret=api_secret
        )
        
        # 메시지 모델 생성
        message = RequestMessage(
            from_=sender_number,  # 발신번호 (등록된 발신번호만 사용 가능)
            to=phone,  # 수신번호 (01000000000 형식)
            text=content,  # 메시지 내용
        )
        
        # 메시지 발송
        response = message_service.send(message)
        
        logger.info(
            "[SMS] 메시지 발송 성공 - 수신번호: %s, Group ID: %s, 성공: %d, 실패: %d",
            phone,
            response.group_info.group_id,
            response.group_info.count.registered_success,
            response.group_info.count.registered_failed,
        )
        
    except ImportError:
        # solapi 패키지가 설치되지 않은 경우
        logger.warning(
            "[SMS] solapi 패키지가 설치되지 않았습니다. 'pip install solapi'를 실행하세요."
        )
        logger.info("[SMS] 수신번호: %s, 내용: %s", phone, content)
    except Exception as e:
        # SMS 발송 실패 시 로그 출력
        logger.error("[SMS] 메시지 발송 실패 - 수신번호: %s, 오류: %s", phone, str(e))
        # 프로덕션 환경에서는 예외를 다시 발생시킬 수도 있지만,
        # 현재는 로그만 출력하고 계속 진행하도록 함


_MEMORY_VERIFICATION_STORE = InMemoryPhoneVerificationStore()
_MEMORY_PHONE_AUTH_STORE = InMemoryPhoneAuthTokenStore()


def get_phone_service() -> PhoneService:
    """
    FastAPI dependency provider.
    """

    return PhoneService(
        verification_store=_MEMORY_VERIFICATION_STORE,
        phone_auth_store=_MEMORY_PHONE_AUTH_STORE,
    )

