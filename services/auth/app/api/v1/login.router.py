from datetime import datetime, timezone

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status

from services.auth.app.schemas.request import (
    MemberJoinSchema,
    MemberLoginSchema,
    PartnerJoinSchema,
    PartnerLoginSchema,
    PhoneRequest,
    PhoneSchema,
)
from services.auth.app.schemas.response import (
    PhoneVerifyResponse,
    LoginResponse,
    JoinResponse,
)
from services.auth.app.core.LoginService import LoginError, LoginService
from services.auth.app.dependencies import get_login_service
from services.auth.app.db.connection import settings

router = APIRouter(tags=["Authentication"])


def _not_implemented(feature_name: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature_name} 엔드포인트는 아직 구현되지 않았습니다.",
    )


def _set_refresh_cookie(response: Response, refresh_token: str, expires_at: datetime) -> None:
    max_age = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 0)
    response.set_cookie(
        key="X-REFRESH-TOKEN",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookies(response: Response) -> None:
    for cookie_name in ("LOGIN-REQUEST-HASH", "X-REFRESH-TOKEN"):
        response.delete_cookie(
            key=cookie_name,
            httponly=True,
            secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
            samesite="lax",
        )
        response.headers["clear-cookie"] = cookie_name


def _clear_login_request_cookie(response: Response) -> None:
    response.delete_cookie(
        key="LOGIN-REQUEST-HASH",
        httponly=True,
        secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
        samesite="lax",
    )
    response.headers["clear-cookie"] = "LOGIN-REQUEST-HASH"

@router.post(
    "/login/phone",
    response_model=LoginResponse,
    responses={
        200: {
            "description": "로그인 성공",
            "content": {
                "application/json": {
                    "example": {
                        "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "userName": "홍길동"
                    }
                }
            }
        },
        400: {
            "description": "로그인 실패",
            "content": {
                "application/json": {
                    "example": {"code": "ERR-IVD-PARAM"}
                }
            }
        }
    }
)
async def login_member_with_phone(
    response: Response,
    payload: MemberLoginSchema | None = Body(default=None),
    refresh_token: str | None = Cookie(default=None, alias="X-REFRESH-TOKEN"),
    login_request_hash: str | None = Cookie(default=None, alias="LOGIN-REQUEST-HASH"),
    login_service: LoginService = Depends(get_login_service),
):
    """
    개인회원 로그인 (인증번호)
    
    사용: [P_OB-2] 로그인
    
    **응답 형식:**
    - `accessToken`: JWT 액세스 토큰
    - `userName`: 사용자 이름 (개인회원의 경우 memberName)
    """
    del login_request_hash  # cookie는 인증 완료 단계에서만 사용, 로그인에서는 제거 대상

    phone_auth_token = payload.phoneAuthToken if payload else None

    try:
        tokens = await login_service.login_member(
            phone_auth_token=phone_auth_token,
            refresh_token=refresh_token,
        )
    except LoginError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code},
        ) from exc

    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    _clear_login_request_cookie(response)

    return LoginResponse(accessToken=tokens.access_token, userName=tokens.user_name)

@router.post(
    "/login/pin",
    response_model=LoginResponse,
    responses={
        200: {
            "description": "로그인 성공",
            "content": {
                "application/json": {
                    "example": {
                        "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "userName": "파트너 업체명"
                    }
                }
            }
        },
        400: {
            "description": "로그인 실패",
            "content": {
                "application/json": {
                    "example": {"code": "ERR-IVD-PARAM"}
                }
            }
        }
    }
)
async def login_partner_with_pin(
    response: Response,
    payload: PartnerLoginSchema | None = Body(default=None),
    refresh_token: str | None = Cookie(default=None, alias="X-REFRESH-TOKEN"),
    login_request_hash: str | None = Cookie(default=None, alias="LOGIN-REQUEST-HASH"),
    login_service: LoginService = Depends(get_login_service),
):
    """
    파트너회원 로그인 (PIN)
    
    사용: [P_OB-2] 로그인
    
    **응답 형식:**
    - `accessToken`: JWT 액세스 토큰
    - `userName`: 사용자 이름 (파트너의 경우 partnerName)
    """
    del login_request_hash

    phone_number = payload.phoneNumber if payload else None
    pin_hash = payload.pin if payload else None

    try:
        tokens = await login_service.login_partner(
            phone=phone_number,
            pin_hash=pin_hash,
            refresh_token=refresh_token,
        )
    except LoginError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code},
        ) from exc

    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    _clear_login_request_cookie(response)

    return LoginResponse(accessToken=tokens.access_token, userName=tokens.user_name)
