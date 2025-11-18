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

@router.post("/phone/request", response_model=PhoneRequestResponse)
async def request_phone_verification(payload: PhoneRequest):
    """
    휴대폰번호 인증요청
    
    사용: [P_OB-2] 로그인,[P_US-5] 설정
    """
    _not_implemented("휴대폰번호 인증요청")


@router.post("/phone", response_model=PhoneVerifyResponse)
async def verify_phone(payload: PhoneSchema):
    """
    휴대폰번호 인증
    
    사용: [P_OB-2] 로그인,[P_US-5] 설정
    """
    _not_implemented("휴대폰번호 인증")
