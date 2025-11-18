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
    ):
        self.member_repository = member_repository
        self.member_create = member_create
        self.partner_repository = partner_repository
        self.partner_create = partner_create
        self.phone_service = phone_service or PhoneService()
        self.login_service = login_service

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

        return await self.login_service._issue_tokens(member_id, self.SUBJECT_MEMBER)

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

        partner_id = await self.partner_create.create_partner(
            user_name=user_name,
            partner_name=partner_name,
            phone=phone,
            pin_hash=pin_hash,
        )

        # 4. AccessToken 및 RefreshToken 발급 (LoginService 사용)
        if not self.login_service:
            raise JoinError("ERR-INTERNAL", "로그인 서비스가 설정되지 않았습니다.")

        return await self.login_service._issue_tokens(partner_id, self.SUBJECT_PARTNER)

    async def _consume_phone_token(self, phone_auth_token: str) -> str:
        try:
            return await self.phone_service.consume_phone_auth_token(phone_auth_token)
        except PhoneVerificationError as exc:
            raise JoinError(exc.code, str(exc)) from exc

