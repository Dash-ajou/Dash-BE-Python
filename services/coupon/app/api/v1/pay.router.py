from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page

from libs.common import CurrentUser

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.response import PaymentLogItem

# 결제 로그 관련 라우터
router = APIRouter(prefix="/coupons/pay", tags=["Coupon Payment"])


@router.get("/log", response_model=Page[PaymentLogItem])
async def get_payment_log(
    current_user: CurrentUser,
    page: int = 1,
    size: int = 10,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    결제된 쿠폰에 대한 사용 기록을 조회합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 사용 기록 목록 반환
    - HTTP 401 Unauthorized: 인증 실패
    
    **응답 형식:**
    - `items`: 사용 로그 목록
    - `total`: 전체 개수
    - `page`: 현재 페이지
    - `size`: 페이지 크기
    - `pages`: 전체 페이지 수
    """
    subject_type, subject_id = current_user
    
    # 개인회원만 조회 가능
    if subject_type != "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개인회원만 결제 로그를 조회할 수 있습니다.",
        )
    
    # 결제 로그 조회
    result = await coupon_service.get_payment_logs_by_member(
        member_id=subject_id,
        page=page,
        size=size,
    )
    
    return result

