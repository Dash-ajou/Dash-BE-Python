import hashlib
import hmac
from typing import Protocol

from services.auth.app.core.LoginService import (
    LoginService,
    LoginTokens,
    MemberRepositoryPort,
    PartnerRepositoryPort,
)
from services.auth.app.core.PhoneService import PhoneService, PhoneVerificationError


class JoinError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class MemberCreatePort(Protocol):
    async def create_member(
        self, member_name: str, member_birth: str, phone: str, group_ids: list[str]
    ) -> int: ...


class PartnerCreatePort(Protocol):
    async def create_partner(
        self, user_name: str, partner_name: str, phone: str, pin_hash: str
    ) -> int: ...


class IssueMappingPort(Protocol):
    """발행요청 매핑 인터페이스"""
    async def map_partner_to_issues(
        self,
        partner_id: int,
        partner_phone: str,
    ) -> None: ...


class JoinService:
    SUBJECT_MEMBER = "member"
    SUBJECT_PARTNER = "partner"

    def __init__(
        self,
        member_repository: MemberRepositoryPort | None = None,
        member_create: MemberCreatePort | None = None,
        partner_repository: PartnerRepositoryPort | None = None,
        partner_create: PartnerCreatePort | None = None,
        phone_service: PhoneService | None = None,
        login_service: LoginService | None = None,
        issue_mapper: IssueMappingPort | None = None,
    ):
        self.member_repository = member_repository
        self.member_create = member_create
        self.partner_repository = partner_repository
        self.partner_create = partner_create
        self.phone_service = phone_service or PhoneService()
        self.login_service = login_service
        self.issue_mapper = issue_mapper

    async def join_member(
        self,
        phone_auth_token: str,
        member_name: str,
        member_birth: str,
        depart_at: list[str],
    ) -> LoginTokens:
        # 1. PhoneAuthToken 검증하여 전화번호 가져오기
        phone = await self._consume_phone_token(phone_auth_token)

        # 2. phones 테이블에서 전화번호 중복 체크 (MEMBER/PARTNER 구분 없이)
        if self.member_repository:
            phone_exists = await self.member_repository.phone_exists(phone)
            if phone_exists:
                raise JoinError("ERR-DUP-VALUE", "이미 등록된 전화번호입니다.")

        # 3. Member 생성 및 Phone, Member-Group 관계 생성
        if not self.member_create:
            raise JoinError("ERR-INTERNAL", "회원 생성 기능이 설정되지 않았습니다.")

        try:
            # group_ids는 빈 리스트여도 명시적으로 전달 (None이 아닌 빈 리스트로)
            member_id = await self.member_create.create_member(
                member_name=member_name,
                member_birth=member_birth,
                phone=phone,
                group_ids=depart_at or [],
            )
        except ValueError as exc:
            # 날짜 형식 오류 등을 처리
            raise JoinError("ERR-IVD-VALUE", str(exc)) from exc

        # 4. AccessToken 및 RefreshToken 발급 (LoginService 사용)
        if not self.login_service:
            raise JoinError("ERR-INTERNAL", "로그인 서비스가 설정되지 않았습니다.")

        # 사용자 정보 조회 (이름 포함)
        if not self.member_repository:
            raise JoinError("ERR-INTERNAL", "회원 저장소가 설정되지 않았습니다.")
        member = await self.member_repository.find_member_by_id(member_id)
        if member is None:
            raise JoinError("ERR-INTERNAL", "회원 정보를 찾을 수 없습니다.")

        return await self.login_service._issue_tokens(member_id, self.SUBJECT_MEMBER, member.memberName)

    async def join_partner(
        self,
        phone_auth_token: str,
        user_name: str,
        partner_name: str,
        pin_hash: str,
    ) -> LoginTokens:
        # 1. PhoneAuthToken 검증하여 전화번호 가져오기
        phone = await self._consume_phone_token(phone_auth_token)

        # 2. phones 테이블에서 전화번호 중복 체크 (MEMBER/PARTNER 구분 없이)
        if self.partner_repository:
            phone_exists = await self.partner_repository.phone_exists(phone)
            if phone_exists:
                raise JoinError("ERR-DUP-VALUE", "이미 등록된 전화번호입니다.")

        # 3. Partner 생성 및 Phone, PartnerPin 생성
        if not self.partner_create:
            raise JoinError("ERR-INTERNAL", "파트너 생성 기능이 설정되지 않았습니다.")

        # pin_hash를 phone을 key로 사용하여 단방향 암호화 (HMAC-SHA256)
        encrypted_pin_hash = self._encrypt_pin_with_phone(pin_hash, phone)

        partner_id = await self.partner_create.create_partner(
            user_name=user_name,
            partner_name=partner_name,
            phone=phone,
            pin_hash=encrypted_pin_hash,
        )

        # 4. AccessToken 및 RefreshToken 발급 (LoginService 사용)
        if not self.login_service:
            raise JoinError("ERR-INTERNAL", "로그인 서비스가 설정되지 않았습니다.")

        # 사용자 정보 조회 (이름 포함)
        if not self.partner_repository:
            raise JoinError("ERR-INTERNAL", "파트너 저장소가 설정되지 않았습니다.")
        partner = await self.partner_repository.find_partner_by_id(partner_id)
        if partner is None:
            raise JoinError("ERR-INTERNAL", "파트너 정보를 찾을 수 없습니다.")

        # 5. 발행요청과 매핑 (있는 경우)
        if self.issue_mapper:
            try:
                await self.issue_mapper.map_partner_to_issues(
                    partner_id=partner_id,
                    partner_phone=phone,
                )
            except Exception:
                # 매핑 실패해도 가입은 성공으로 처리 (로그만 남기고 계속 진행)
                pass

        return await self.login_service._issue_tokens(partner_id, self.SUBJECT_PARTNER, partner.partnerName)

    async def _consume_phone_token(self, phone_auth_token: str) -> str:
        try:
            return await self.phone_service.consume_phone_auth_token(phone_auth_token)
        except PhoneVerificationError as exc:
            raise JoinError(exc.code, str(exc)) from exc

    @staticmethod
    def _encrypt_pin_with_phone(pin_hash: str, phone: str) -> str:
        """
        pin_hash를 phone을 key로 사용하여 단방향 암호화 (HMAC-SHA256)
        
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

