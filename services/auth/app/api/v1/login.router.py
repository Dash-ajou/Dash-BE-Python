from fastapi import APIRouter, HTTPException, status

from app.schemas.request import (
    MemberJoinSchema,
    MemberLoginSchema,
    PartnerJoinSchema,
    PartnerLoginSchema,
    PhoneRequest,
    PhoneSchema,
)
from app.schemas.response import (
    PhoneRequestResponse,
    PhoneVerifyResponse,
    LoginResponse,
    JoinResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _not_implemented(feature_name: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature_name} 엔드포인트는 아직 구현되지 않았습니다.",
    )

@router.post("/login/phone", response_model=LoginResponse)
async def login_member_with_phone(payload: MemberLoginSchema):
    """
    개인회원 로그인 (인증번호)
    
    사용: [P_OB-2] 로그인
    """
    _not_implemented("개인회원 로그인")

@router.post("/login/pin", response_model=LoginResponse)
async def login_partner_with_pin(payload: PartnerLoginSchema):
    """
    파트너회원 로그인 (PIN)
    
    사용: [P_OB-2] 로그인
    """
    _not_implemented("파트너회원 로그인")
