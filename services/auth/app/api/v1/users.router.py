from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth.app.core.LoginService import LoginError, LoginService
from services.auth.app.dependencies import get_login_service
from services.auth.app.db.connection import settings
from typing import Union

from services.auth.app.schemas.request import PhoneUpdateSchema, DepartUpdateSchema, PinUpdateSchema
from services.auth.app.schemas.response import LoginResponse, MemberInfoResponse, PartnerInfoResponse

router = APIRouter(prefix="/users", tags=["Users"])

# Swagger UI에서 Bearer token을 입력할 수 있도록 HTTPBearer 설정
security = HTTPBearer(description="Access Token (Bearer)", auto_error=False)


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


@router.patch("/phone", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def update_phone(
    payload: PhoneUpdateSchema,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
):
    """
    개인사용자 계정과 연결된 전화번호를 수정합니다.
    
    요청 즉시 변경되며, accessToken 및 refreshToken이 새롭게 발급됩니다.
    파트너는 이 엔드포인트를 사용할 수 없습니다.
    """
    # Bearer token 추출
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 헤더가 필요합니다.",
        )
    
    access_token = credentials.credentials
    
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
    
    return LoginResponse(accessToken=tokens.access_token, userName=tokens.user_name)


@router.put("/depart", status_code=status.HTTP_200_OK)
async def update_depart(
    payload: DepartUpdateSchema,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
):
    """
    계정에 설정된 소속정보를 수정합니다.
    
    전달된 소속정보로 대체되므로, 수정된 내역만 보내는 것이 아닌 
    모든 최종적으로 변경된 소속정보를 전부 보내야 합니다.
    
    **주의사항:**
    - 개인사용자(MEMBER)만 사용 가능합니다.
    - 부분 업데이트가 아닌 전체 교체입니다.
    - 올바르지 않은 소속 ID가 1개라도 있으면 400 Bad Request를 반환합니다.
    """
    # Bearer token 추출
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    access_token = credentials.credentials
    
    try:
        await login_service.update_depart(
            access_token=access_token,
            group_ids=payload.departAt,
        )
    except LoginError as exc:
        # 그룹 ID가 유효하지 않은 경우
        if exc.code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="",
            ) from exc
        # 로그인 상태가 올바르지 않은 경우 (토큰 오류, 파트너 계정 등)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        ) from exc
    
    # 성공 시 빈 응답 반환 (HTTP 200 OK)
    return Response(status_code=status.HTTP_200_OK)


@router.post("/pin", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def update_pin(
    payload: PinUpdateSchema,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
):
    """
    파트너 계정 전용; PIN을 변경합니다.
    
    현재 PIN과 새로운 PIN을 모두 입력해야 하며, 
    현재 PIN이 일치하는 경우에만 변경됩니다.
    
    요청 즉시 변경되며, accessToken 및 refreshToken이 새롭게 발급됩니다.
    
    **주의사항:**
    - 파트너 계정만 사용 가능합니다.
    - prevPin과 newPin은 모두 SHA-256으로 해시된 값이어야 합니다.
    """
    # Bearer token 추출
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    access_token = credentials.credentials
    
    try:
        tokens = await login_service.update_pin(
            access_token=access_token,
            prev_pin_hash=payload.prevPin,
            new_pin_hash=payload.newPin,
        )
    except LoginError as exc:
        # PIN이 올바르지 않은 경우
        if exc.code == "ERR-IVD-VALUE":
            # 요구사항에 따라 쿠키를 설정 (빈 값으로 삭제)
            response.delete_cookie(
                key="X-REFRESH-TOKEN",
                httponly=True,
                secure=settings.cookie_secure,
                samesite="lax",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "ERR-IVD-VALUE"},
            ) from exc
        # 기타 오류 (개인사용자 계정 등)
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code},
        ) from exc
    
    # 새 토큰을 쿠키에 설정
    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    
    return LoginResponse(accessToken=tokens.access_token, userName=tokens.user_name)


@router.get("/my", response_model=Union[MemberInfoResponse, PartnerInfoResponse])
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
):
    """
    현재 로그인되어있는 사용자 정보를 조회합니다.
    
    개인회원과 파트너회원에 따라 다른 형식의 응답을 반환합니다.
    """
    # Bearer token 추출
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    access_token = credentials.credentials
    
    try:
        user_info = await login_service.get_current_user_info(access_token)
    except LoginError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    # 응답 타입에 따라 반환
    if "memberId" in user_info:
        return MemberInfoResponse(**user_info)
    elif "partnerId" in user_info:
        return PartnerInfoResponse(**user_info)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )

