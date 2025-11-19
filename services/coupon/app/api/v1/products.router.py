"""
상품 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status

from libs.common import CurrentUser

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.response import ProductListResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/{partner_id}", response_model=ProductListResponse, status_code=status.HTTP_200_OK)
async def get_products_by_partner(
    partner_id: int,
    current_user: CurrentUser,
    keyword: str | None = None,
    page: int = 1,
    size: int = 10,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    특정 파트너에게 등록된 제품 목록을 검색합니다.
    
    keyword가 비어있는 상태로 전달되는 경우 검색 결과를 반환하지 않습니다.
    
    **Path Parameters:**
    - `partner_id`: 검색하고자 하는 파트너 ID
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `keyword`: 검색 키워드 (상품명, 필수)
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 상품 목록 반환
    - HTTP 400 Bad Request: keyword가 비어있는 경우 `{"code": "ERR-IVD-VALUE"}`
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    """
    subject_type, subject_id = current_user
    
    # keyword가 비어있는 경우 400 Bad Request 반환
    if not keyword or keyword.strip() == "":
    raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ERR-IVD-VALUE"},
        )
    
    # 상품 목록 조회
    result = await coupon_service.get_products_by_partner_and_keyword(
        partner_id=partner_id,
        keyword=keyword.strip(),
        page=page,
        size=size,
    )
    
    return result

