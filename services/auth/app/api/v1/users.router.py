from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from services.auth.app.core.LoginService import LoginError, LoginService
from services.auth.app.dependencies import get_login_service
from services.auth.app.db.connection import settings
from services.auth.app.schemas.request import PhoneUpdateSchema
from services.auth.app.schemas.response import LoginResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _set_refresh_cookie(response: Response, refresh_token: str, expires_at: datetime) -> None:
    """RefreshToken을 쿠키에 설정하는 헬퍼 함수"""
    max_age = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 0)
    response.set_cookie(
        key="X-REFRESH-TOKEN",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookies(response: Response) -> None:
    """인증 관련 쿠키를 모두 삭제하는 헬퍼 함수"""
    for cookie_name in ("LOGIN-REQUEST-HASH", "X-REFRESH-TOKEN"):
        response.delete_cookie(
            key=cookie_name,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
        )
        response.headers["clear-cookie"] = cookie_name


@router.put("/phone", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def update_phone(
    payload: PhoneUpdateSchema,
    response: Response,
    authorization: str | None = Header(default=None, alias="Authorization"),
    login_service: LoginService = Depends(get_login_service),
):
    """
    개인사용자 계정과 연결된 전화번호를 수정합니다.
    
    요청 즉시 변경되며, accessToken 및 refreshToken이 새롭게 발급됩니다.
    파트너는 이 엔드포인트를 사용할 수 없습니다.
    """
    # Authorization 헤더에서 Bearer token 추출
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 헤더가 필요합니다.",
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="올바른 Authorization 형식이 아닙니다. 'Bearer {token}' 형식을 사용하세요.",
        )
    
    access_token = authorization[7:]  # "Bearer " 제거
    
    try:
        tokens = await login_service.update_phone(
            access_token=access_token,
            phone_auth_token=payload.phoneAuthToken,
        )
    except LoginError as exc:
        # phoneAuthToken이 올바르지 않은 경우
        if exc.code in ("ERR-IVD-PARAM", "ERR-MISSING-PHONE-AUTH", "ERR-PHONE-AUTH-EXPIRED"):
            _clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "ERR-IVD-VALUE"},
            ) from exc
        # 기타 오류 (파트너 계정인 경우 포함)
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code},
        ) from exc
    
    # 새 토큰을 쿠키에 설정
    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    
    return LoginResponse(accessToken=tokens.access_token)

