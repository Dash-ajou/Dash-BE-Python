"""
파트너 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status

from libs.common import CurrentUser

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.response import PartnerListResponse

router = APIRouter(prefix="/partners", tags=["Partners"])


@router.get("", response_model=PartnerListResponse, status_code=status.HTTP_200_OK)
async def get_partners(
    current_user: CurrentUser,
    keyword: str | None = None,
    page: int = 1,
    size: int = 10,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    파트너 계정을 파트너 상호명을 기반으로 검색합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `keyword`: 검색 키워드 (파트너 상호명, 선택)
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 파트너 목록 반환
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    """
    subject_type, subject_id = current_user
    
    # 파트너 목록 조회
    result = await coupon_service.get_partners_by_keyword(
        keyword=keyword,
        page=page,
        size=size,
    )
    
    return result

