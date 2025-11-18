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

@router.post("/join/member", response_model=JoinResponse, status_code=status.HTTP_201_CREATED)
async def join_member(payload: MemberJoinSchema):
    """
    회원가입 (개인회원)
    
    사용: [P_OB-3] 회원가입
    """
    _not_implemented("개인회원 회원가입")


@router.post("/join/partner", response_model=JoinResponse, status_code=status.HTTP_201_CREATED)
async def join_partner(payload: PartnerJoinSchema):
    """
    회원가입 (파트너)
    
    사용: [P_OB-3] 회원가입
    """
    _not_implemented("파트너 회원가입")

