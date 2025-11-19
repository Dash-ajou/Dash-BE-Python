from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status

from libs.common import now_kst

from services.auth.app.schemas.request import (
    MemberJoinSchema,
    MemberLoginSchema,
    PartnerJoinSchema,
    PartnerLoginSchema,
    PhoneRequest,
    PhoneSchema,
)
from services.auth.app.schemas.response import (
    PhoneRequestResponse,
    PhoneVerifyResponse,
    LoginResponse,
    JoinResponse,
)
from services.auth.app.core.PhoneService import PhoneService, PhoneVerificationError
from services.auth.app.dependencies import get_phone_service
from services.auth.app.db.connection import settings

router = APIRouter(tags=["Authentication"])


def _not_implemented(feature_name: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature_name} 엔드포인트는 아직 구현되지 않았습니다.",
    )

@router.post("/phone/request", response_model=PhoneRequestResponse)
async def request_phone_verification(
    payload: PhoneRequest,
    response: Response,
    phone_service: PhoneService = Depends(get_phone_service),
):
    """
    휴대폰번호 인증요청
    
    사용: [P_OB-2] 로그인,[P_US-5] 설정
    """
    try:
        result = await phone_service.request_phone_verification(payload.phone)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if result.login_request_hash:
        cookie_kwargs = {
            "key": "LOGIN-REQUEST-HASH",
            "value": result.login_request_hash,
            "httponly": True,
            "secure": settings.cookie_secure,  # 환경 변수에 따라 자동 설정
            "samesite": "lax",
        }
        if result.hash_expiration:
            delta = result.hash_expiration - now_kst()
            cookie_kwargs["max_age"] = max(int(delta.total_seconds()), 0)

        response.set_cookie(**cookie_kwargs)
        response.headers["LOGIN-REQUEST-HASH"] = result.login_request_hash

    return PhoneRequestResponse(isUsed=result.is_used, userType=result.user_type)


@router.post("/phone", response_model=PhoneVerifyResponse)
async def verify_phone(
    payload: PhoneSchema,
    response: Response,
    login_request_hash_cookie: str | None = Cookie(
        default=None,
        alias="LOGIN-REQUEST-HASH",
        description="인증 요청 해시 (쿠키에서 자동으로 읽어옴)",
    ),
    login_request_hash_header: str | None = Header(
        default=None,
        alias="LOGIN-REQUEST-HASH",
        description="인증 요청 해시 (헤더에서 읽어옴, Swagger 테스트용)",
    ),
    phone_service: PhoneService = Depends(get_phone_service),
):
    """
    휴대폰번호 인증
    
    사용: [P_OB-2] 로그인,[P_US-5] 설정
    
    주의: Swagger UI에서 테스트할 때는 헤더에 "LOGIN-REQUEST-HASH"를 추가하세요.
    """
    # 쿠키 또는 헤더에서 login_request_hash 가져오기
    login_request_hash = login_request_hash_cookie or login_request_hash_header
    
    try:
        phone_auth_token = await phone_service.verify_phone_code(login_request_hash, payload.code)
    except PhoneVerificationError as exc:
        status_code = status.HTTP_401_UNAUTHORIZED if exc.code == "ERR-IVD-VALUE" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc

    response.delete_cookie(
        key="LOGIN-REQUEST-HASH",
        httponly=True,
        secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
        samesite="lax",
    )
    response.headers["clear-cookie"] = "LOGIN-REQUEST-HASH"

    return PhoneVerifyResponse(phoneAuthToken=phone_auth_token)
