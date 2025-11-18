from datetime import datetime, timezone

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status

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
from app.core.LoginService import LoginError, LoginService, get_login_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
        secure=True,
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookies(response: Response) -> None:
    for cookie_name in ("LOGIN-REQUEST-HASH", "X-REFRESH-TOKEN"):
        response.delete_cookie(
            key=cookie_name,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        response.headers.add("clear-cookie", cookie_name)


def _clear_login_request_cookie(response: Response) -> None:
    response.delete_cookie(
        key="LOGIN-REQUEST-HASH",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.headers.add("clear-cookie", "LOGIN-REQUEST-HASH")

@router.post("/login/phone", response_model=LoginResponse)
async def login_member_with_phone(
    payload: MemberLoginSchema | None = Body(default=None),
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="X-REFRESH-TOKEN"),
    login_request_hash: str | None = Cookie(default=None, alias="LOGIN-REQUEST-HASH"),
    login_service: LoginService = Depends(get_login_service),
):
    """
    개인회원 로그인 (인증번호)
    
    사용: [P_OB-2] 로그인
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

    return LoginResponse(accessToken=tokens.access_token)

@router.post("/login/pin", response_model=LoginResponse)
async def login_partner_with_pin(
    payload: PartnerLoginSchema | None = Body(default=None),
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="X-REFRESH-TOKEN"),
    login_request_hash: str | None = Cookie(default=None, alias="LOGIN-REQUEST-HASH"),
    login_service: LoginService = Depends(get_login_service),
):
    """
    파트너회원 로그인 (PIN)
    
    사용: [P_OB-2] 로그인
    """
    del login_request_hash

    phone_auth_token = payload.phoneAuthToken if payload else None
    pin_hash = payload.pin if payload else None

    try:
        tokens = await login_service.login_partner(
            phone_auth_token=phone_auth_token,
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

    return LoginResponse(accessToken=tokens.access_token)
