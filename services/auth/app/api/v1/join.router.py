from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from services.auth.app.core.JoinService import JoinError, JoinService
from services.auth.app.dependencies import get_join_service
from services.auth.app.schemas.request import (
    MemberJoinSchema,
    PartnerJoinSchema,
)
from services.auth.app.schemas.response import (
    JoinResponse,
)
from services.auth.app.db.connection import settings

router = APIRouter(tags=["Authentication"])


def _set_refresh_cookie(response: Response, refresh_token: str, expires_at: datetime) -> None:
    """RefreshToken을 쿠키에 설정하는 헬퍼 함수 (로그인과 동일한 조건)"""
    max_age = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 0)
    response.set_cookie(
        key="X-REFRESH-TOKEN",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
        samesite="lax",
        max_age=max_age,
    )


def _clear_login_request_cookie(response: Response) -> None:
    """LOGIN-REQUEST-HASH 쿠키를 삭제하는 헬퍼 함수 (로그인과 동일한 조건)"""
    response.delete_cookie(
        key="LOGIN-REQUEST-HASH",
        httponly=True,
        secure=settings.cookie_secure,  # 환경 변수에 따라 자동 설정
        samesite="lax",
    )
    response.headers["clear-cookie"] = "LOGIN-REQUEST-HASH"


def _not_implemented(feature_name: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature_name} 엔드포인트는 아직 구현되지 않았습니다.",
    )


@router.post("/join/member", response_model=JoinResponse, status_code=status.HTTP_201_CREATED)
async def join_member(
    payload: MemberJoinSchema,
    response: Response,
    join_service: JoinService = Depends(get_join_service),
):
    """
    회원가입 (개인회원)
    
    사용: [P_OB-3] 회원가입
    """
    try:
        tokens = await join_service.join_member(
            phone_auth_token=payload.phoneAuthToken,
            member_name=payload.memberName,
            member_birth=payload.memberBirth,
            depart_at=payload.departAt,
        )
    except JoinError as exc:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if exc.code in ("ERR-DUP-VALUE", "ERR-IVD-VALUE")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code},
        ) from exc

    # RefreshToken을 쿠키에 설정 (로그인과 동일한 조건)
    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    # 회원가입 시 LOGIN-REQUEST-HASH 쿠키가 있을 수 있으므로 정리 (로그인과 동일)
    _clear_login_request_cookie(response)

    return JoinResponse(accessToken=tokens.access_token)


@router.post("/join/partner", response_model=JoinResponse, status_code=status.HTTP_201_CREATED)
async def join_partner(
    payload: PartnerJoinSchema,
    response: Response,
    join_service: JoinService = Depends(get_join_service),
):
    """
    회원가입 (파트너)
    
    사용: [P_OB-3] 회원가입
    """
    try:
        tokens = await join_service.join_partner(
            phone_auth_token=payload.phoneAuthToken,
            user_name=payload.userName,
            partner_name=payload.partnerName,
            pin_hash=payload.pin,
        )
    except JoinError as exc:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if exc.code in ("ERR-DUP-VALUE", "ERR-IVD-VALUE")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code},
        ) from exc

    # RefreshToken을 쿠키에 설정 (로그인과 동일한 조건)
    _set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_expires_at)
    # 회원가입 시 LOGIN-REQUEST-HASH 쿠키가 있을 수 있으므로 정리 (로그인과 동일)
    _clear_login_request_cookie(response)

    return JoinResponse(accessToken=tokens.access_token)

