import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Protocol

import jwt

from libs.schemas import Member, PartnerUser

from services.auth.app.core.PhoneService import PhoneService, PhoneVerificationError
from services.auth.app.db.connection import settings


class MemberRepositoryPort(Protocol):
    async def find_member_by_phone(self, phone: str) -> Member | None: ...

    async def find_member_by_id(self, member_id: int) -> Member | None: ...
    
    async def update_phone(self, account_id: int, new_phone: str) -> None: ...


class NullMemberRepository(MemberRepositoryPort):
    async def find_member_by_phone(self, phone: str) -> Member | None:
        return None

    async def find_member_by_id(self, member_id: int) -> Member | None:
        return None
    
    async def update_phone(self, account_id: int, new_phone: str) -> None:
        pass


class PartnerRepositoryPort(Protocol):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None: ...

    async def find_partner_by_id(self, partner_id: int) -> PartnerUser | None: ...
    
    async def update_phone(self, account_id: int, new_phone: str) -> None: ...


class PartnerPinRepositoryPort(Protocol):
    async def find_partner_id_by_pin_hash(self, pin_hash: str) -> int | None: ...


class NullPartnerRepository(PartnerRepositoryPort):
    async def find_partner_by_phone(self, phone: str) -> PartnerUser | None:
        return None

    async def find_partner_by_id(self, partner_id: int) -> PartnerUser | None:
        return None
    
    async def update_phone(self, account_id: int, new_phone: str) -> None:
        pass


class NullPartnerPinRepository(PartnerPinRepositoryPort):
    async def find_partner_id_by_pin_hash(self, pin_hash: str) -> int | None:
        return None


@dataclass
class RefreshTokenEntry:
    subject_type: str
    subject_id: int
    token: str
    expires_at: datetime
    access_token: str | None = None  # access token도 함께 저장


class RefreshTokenStorePort(Protocol):
    async def save_token(self, entry: RefreshTokenEntry) -> None: ...

    async def consume_token(self, token: str) -> RefreshTokenEntry | None: ...

    async def revoke_subject_tokens(self, subject_type: str, subject_id: int) -> None: ...
    
    async def find_by_access_token(self, access_token: str) -> RefreshTokenEntry | None: ...


class InMemoryRefreshTokenStore(RefreshTokenStorePort):
    def __init__(self):
        self._tokens: Dict[str, RefreshTokenEntry] = {}
        self._access_tokens: Dict[str, RefreshTokenEntry] = {}  # access token 인덱스
        self._subject_index: Dict[tuple[str, int], set[str]] = {}

    async def save_token(self, entry: RefreshTokenEntry) -> None:
        key = (entry.subject_type, entry.subject_id)
        subject_tokens = self._subject_index.setdefault(key, set())
        subject_tokens.add(entry.token)
        self._tokens[entry.token] = entry
        if entry.access_token:
            self._access_tokens[entry.access_token] = entry

    async def consume_token(self, token: str) -> RefreshTokenEntry | None:
        entry = self._tokens.pop(token, None)
        if entry:
            key = (entry.subject_type, entry.subject_id)
            subject_tokens = self._subject_index.get(key)
            if subject_tokens and token in subject_tokens:
                subject_tokens.remove(token)
            if entry.access_token:
                self._access_tokens.pop(entry.access_token, None)
        return entry

    async def revoke_subject_tokens(self, subject_type: str, subject_id: int) -> None:
        key = (subject_type, subject_id)
        tokens = self._subject_index.pop(key, set())
        for token in tokens:
            entry = self._tokens.pop(token, None)
            if entry and entry.access_token:
                self._access_tokens.pop(entry.access_token, None)
    
    async def find_by_access_token(self, access_token: str) -> RefreshTokenEntry | None:
        return self._access_tokens.get(access_token)


@dataclass
class LoginTokens:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    user_name: str  # 사용자 이름 추가


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
        refresh_store: RefreshTokenStorePort | None = None,  # JWT 방식으로 변경되어 더 이상 사용하지 않음
        phone_service: PhoneService | None = None,
    ):
        self.member_repository = member_repository or NullMemberRepository()
        self.partner_repository = partner_repository or NullPartnerRepository()
        self.partner_pin_repository = partner_pin_repository or NullPartnerPinRepository()
        # JWT 방식으로 변경되어 refresh_store는 더 이상 사용하지 않음
        # self.refresh_store = refresh_store or InMemoryRefreshTokenStore()
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
            user_name = member.memberName
        else:
            member_id = await self._consume_refresh_token(
                refresh_token, self.SUBJECT_MEMBER
            )
            # refresh token으로 로그인하는 경우 사용자 정보 조회
            member = await self.member_repository.find_member_by_id(member_id)
            if member is None:
                raise LoginError("ERR-IVD-PARAM", "등록되지 않은 회원입니다.")
            user_name = member.memberName

        return await self._issue_tokens(member_id, self.SUBJECT_MEMBER, user_name)

    async def login_partner(
        self,
        phone: str | None,
        pin_hash: str | None,
        refresh_token: str | None,
    ) -> LoginTokens:
        if phone:
            # 전화번호 정규화
            normalized_phone = self._normalize_phone(phone)
            partner = await self.partner_repository.find_partner_by_phone(normalized_phone)
            if partner is None:
                raise LoginError("ERR-IVD-PARAM", "등록되지 않은 파트너입니다.")
            
            # PIN 검증이 필요한 경우 (phone과 pin_hash가 함께 전달된 경우)
            if pin_hash:
                # pin_hash를 phone을 key로 사용하여 암호화 후 검증
                encrypted_pin_hash = self._encrypt_pin_with_phone(pin_hash, normalized_phone)
                verified_partner_id = await self._verify_partner_pin(encrypted_pin_hash)
                if verified_partner_id != partner.partnerId:
                    raise LoginError("ERR-IVD-PARAM", "PIN이 유효하지 않습니다.")
            
            partner_id = partner.partnerId
            user_name = partner.partnerName
        elif pin_hash:
            # phone 없이 pin_hash만 있는 경우는 지원하지 않음
            # (phone 정보가 필요하므로)
            raise LoginError("ERR-IVD-PARAM", "PIN 검증을 위해서는 휴대폰 번호가 필요합니다.")
        else:
            partner_id = await self._consume_refresh_token(
                refresh_token, self.SUBJECT_PARTNER
            )
            # refresh token으로 로그인하는 경우 사용자 정보 조회
            partner = await self.partner_repository.find_partner_by_id(partner_id)
            if partner is None:
                raise LoginError("ERR-IVD-PARAM", "등록되지 않은 파트너입니다.")
            user_name = partner.partnerName

        return await self._issue_tokens(partner_id, self.SUBJECT_PARTNER, user_name)

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
        """
        Refresh token을 JWT 방식으로 검증하고 subject_id를 반환합니다.
        DB 조회 없이 토큰 자체에서 정보를 추출합니다.
        
        Args:
            refresh_token: 검증할 refresh token (JWT)
            subject_type: 예상되는 subject_type (검증용)
            
        Returns:
            subject_id
            
        Raises:
            LoginError: 토큰이 유효하지 않은 경우
        """
        if not refresh_token:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 필요합니다.")

        try:
            # JWT 디코딩 및 검증
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 토큰에서 사용자 정보 추출
            token_subject_type = payload.get("sub_type")
            subject_id = payload.get("sub_id")
            
            if not token_subject_type or not subject_id:
                raise LoginError("ERR-IVD-PARAM", "refresh token에 필수 정보가 없습니다.")
            
            # subject_type 검증
            if token_subject_type != subject_type:
                raise LoginError("ERR-IVD-PARAM", "refresh token 대상이 일치하지 않습니다.")
            
            return int(subject_id)
        except jwt.ExpiredSignatureError:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 만료되었습니다.")
        except jwt.InvalidTokenError as e:
            raise LoginError("ERR-IVD-PARAM", "refresh token이 유효하지 않습니다.") from e

    async def _issue_tokens(self, subject_id: int, subject_type: str, user_name: str) -> LoginTokens:
        """
        토큰을 발급합니다.
        
        Args:
            subject_id: 사용자 ID
            subject_type: 사용자 타입 (member/partner)
            user_name: 사용자 이름
        """
        # JWT 방식으로 변경하여 DB에 저장하지 않음
        # 필요시 revoke를 위한 블랙리스트는 별도로 관리
        now = datetime.now(timezone.utc)
        access_token = self._generate_access_token(subject_type, subject_id, now)
        refresh_token = self._generate_refresh_token(subject_type, subject_id, now)
        refresh_expires_at = now + self.REFRESH_TOKEN_TTL

        return LoginTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
            user_name=user_name,
        )
    
    async def verify_access_token(self, access_token: str) -> tuple[str, int]:
        """
        Access token을 JWT 방식으로 검증하고 subject_type과 subject_id를 반환합니다.
        DB 조회 없이 토큰 자체에서 정보를 추출합니다.
        
        Args:
            access_token: 검증할 access token (JWT)
            
        Returns:
            (subject_type, subject_id) 튜플
            
        Raises:
            LoginError: 토큰이 유효하지 않은 경우
        """
        try:
            # JWT 디코딩 및 검증
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 토큰에서 사용자 정보 추출
            subject_type = payload.get("sub_type")
            subject_id = payload.get("sub_id")
            
            if not subject_type or not subject_id:
                raise LoginError("ERR-IVD-PARAM", "access token에 필수 정보가 없습니다.")
            
            return (subject_type, int(subject_id))
        except jwt.ExpiredSignatureError:
            raise LoginError("ERR-IVD-PARAM", "access token이 만료되었습니다.")
        except jwt.InvalidTokenError as e:
            raise LoginError("ERR-IVD-PARAM", "access token이 유효하지 않습니다.") from e
    
    async def update_phone(
        self,
        access_token: str,
        phone_auth_token: str,
    ) -> LoginTokens:
        """
        개인사용자(MEMBER) 계정의 전화번호를 업데이트하고 새 토큰을 발급합니다.
        파트너는 이 메서드를 사용할 수 없습니다.
        
        Args:
            access_token: 현재 access token
            phone_auth_token: 새 전화번호 인증 토큰
            
        Returns:
            새로 발급된 토큰
            
        Raises:
            LoginError: 토큰이 유효하지 않거나, 파트너 계정이거나, 전화번호 인증이 실패한 경우
        """
        # 1. Access token 검증 (JWT 방식, DB 조회 없이)
        subject_type, subject_id = await self.verify_access_token(access_token)
        
        # 2. 개인사용자(MEMBER)만 허용
        if subject_type != self.SUBJECT_MEMBER:
            raise LoginError("ERR-IVD-PARAM", "이 메서드는 개인사용자만 사용할 수 있습니다.")
        
        # 3. Phone auth token에서 새 전화번호 가져오기
        try:
            new_phone = await self.phone_service.consume_phone_auth_token(phone_auth_token)
        except PhoneVerificationError as exc:
            raise LoginError(exc.code, str(exc)) from exc
        
        # 4. 새 전화번호 중복 체크 (현재 계정 제외)
        existing_member = await self.member_repository.find_member_by_phone(new_phone)
        if existing_member and existing_member.memberId != subject_id:
            raise LoginError("ERR-DUP-VALUE", "이미 등록된 전화번호입니다.")
        
        # 5. 전화번호 업데이트
        await self.member_repository.update_phone(subject_id, new_phone)
        
        # 6. 사용자 정보 조회 (이름 포함)
        member = await self.member_repository.find_member_by_id(subject_id)
        if member is None:
            raise LoginError("ERR-IVD-PARAM", "등록되지 않은 회원입니다.")
        
        # 7. 새 토큰 발급
        return await self._issue_tokens(subject_id, subject_type, member.memberName)

    def _generate_access_token(
        self,
        subject_type: str,
        subject_id: int,
        issued_at: datetime,
    ) -> str:
        """
        Access token을 JWT 방식으로 생성합니다.
        토큰에 로그인된 사용자 정보를 포함합니다.
        """
        expires_at = issued_at + self.ACCESS_TOKEN_TTL
        
        payload = {
            "sub_type": subject_type,  # subject type (member/partner)
            "sub_id": subject_id,  # subject id (member_id or partner_id)
            "iat": int(issued_at.timestamp()),  # issued at
            "exp": int(expires_at.timestamp()),  # expiration time
            "type": "access",  # token type
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

    def _generate_refresh_token(
        self,
        subject_type: str,
        subject_id: int,
        issued_at: datetime,
    ) -> str:
        """
        Refresh token을 JWT 방식으로 생성합니다.
        토큰에 로그인된 사용자 정보를 포함합니다.
        """
        expires_at = issued_at + self.REFRESH_TOKEN_TTL
        
        payload = {
            "sub_type": subject_type,  # subject type (member/partner)
            "sub_id": subject_id,  # subject id (member_id or partner_id)
            "iat": int(issued_at.timestamp()),  # issued at
            "exp": int(expires_at.timestamp()),  # expiration time
            "type": "refresh",  # token type
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

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
    def _normalize_phone(raw_phone: str) -> str:
        """
        전화번호를 정규화합니다 (숫자만 추출).
        PhoneService와 동일한 로직 사용
        
        Args:
            raw_phone: 정규화할 전화번호
            
        Returns:
            정규화된 전화번호 (숫자만)
        """
        digits = re.sub(r"\D", "", raw_phone or "")
        if not digits:
            raise ValueError("휴대폰 번호가 유효하지 않습니다.")
        return digits

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


