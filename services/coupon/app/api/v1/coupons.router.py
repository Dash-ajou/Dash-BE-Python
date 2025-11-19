from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi_pagination import Page

from libs.common import CurrentUser, security

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.request import CouponDeleteSchema
from services.coupon.app.schemas.response import CouponDetailResponse, CouponListItem

# 쿠폰 기본 CRUD 라우터
router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.get("", response_model=Page[CouponListItem])
async def get_coupons(
    current_user: CurrentUser,
    page: int = 1,
    size: int = 10,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    로그인된 사용자의 쿠폰 목록을 조회합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 쿠폰 목록 반환 (사용한 쿠폰 포함)
    - HTTP 401 Unauthorized: 인증 실패
    
    **응답 형식:**
    - `items`: 쿠폰 목록
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
            detail="개인회원만 쿠폰 목록을 조회할 수 있습니다.",
        )
    
    # 쿠폰 목록 조회
    result = await coupon_service.get_coupons_by_member(
        member_id=subject_id,
        page=page,
        size=size,
    )
    
    return result


@router.get("/{coupon_id}", response_model=CouponDetailResponse)
async def get_coupon(
    coupon_id: int,
    current_user: CurrentUser,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    특정 쿠폰의 상세 정보를 조회합니다.
    
    **Path Parameters:**
    - `coupon_id`: 조회할 쿠폰의 고유 식별자
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Response:**
    - HTTP 200 OK: 쿠폰 상세 정보 반환
    - HTTP 400 Bad Request: 유효하지 않은 쿠폰 (ERR-IVD-VALUE)
    - HTTP 401 Unauthorized: 인증 실패
    - HTTP 403 Forbidden: 본인이 등록하지 않은 쿠폰 (ERR-NOT-YOURS)
    """
    subject_type, subject_id = current_user
    
    # 개인회원만 조회 가능
    if subject_type != "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개인회원만 쿠폰 상세 정보를 조회할 수 있습니다.",
        )
    
    try:
        # 쿠폰 상세 정보 조회
        result = await coupon_service.get_coupon_detail(
            coupon_id=coupon_id,
            member_id=subject_id,
        )
        return result
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-NOT-YOURS":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ERR-NOT-YOURS"},
            )
        elif error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )


@router.post("/add")
async def add_coupon(
    current_user: CurrentUser,
):
    """
    새로운 쿠폰을 추가합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Response:**
    - HTTP 201 Created: 쿠폰 생성 성공
    - HTTP 401 Unauthorized: 인증 실패
    - HTTP 400 Bad Request: 잘못된 요청
    
    **Example:**
    ```python
    # current_user는 (subject_type, subject_id) 튜플입니다.
    subject_type, subject_id = current_user
    ```
    """
    # 공통 인증 모듈을 통해 자동으로 검증됨
    subject_type, subject_id = current_user
    # TODO: 쿠폰 생성 로직 구현
    return {
        "message": "쿠폰 추가 API - 구현 예정",
        "user_type": subject_type,
        "user_id": subject_id,
    }


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_coupons(
    payload: CouponDeleteSchema,
    current_user: CurrentUser,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    계정에 등록된 쿠폰들을 삭제합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Request Body:**
    - `coupons`: 삭제할 쿠폰 ID 목록
    
    **Response:**
    - HTTP 200 OK: 쿠폰 삭제 완료
      - 사용하지 않은 쿠폰이 있는 경우: 해당 쿠폰의 상세 정보 반환
      - 모든 쿠폰이 사용된 경우: 빈 응답
    - HTTP 400 Bad Request: 유효하지 않은 쿠폰 포함 (ERR-IVD-VALUE)
    - HTTP 401 Unauthorized: 인증 실패
    - HTTP 403 Forbidden: 본인이 등록하지 않은 쿠폰 포함 (ERR-NOT-YOURS)
    
    **참고:**
    - 실제로 쿠폰이 삭제되지 않고, 등록 기록에 삭제 여부가 기록됩니다.
    - 삭제된 쿠폰은 조회 시 제외됩니다.
    """
    subject_type, subject_id = current_user
    
    # 개인회원만 삭제 가능
    if subject_type != "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개인회원만 쿠폰을 삭제할 수 있습니다.",
        )
    
    try:
        # 쿠폰 삭제 처리
        unused_coupons = await coupon_service.delete_coupons(
            coupon_ids=payload.coupons,
            member_id=subject_id,
        )
        
        # 사용하지 않은 쿠폰이 있는 경우 첫 번째 쿠폰의 상세 정보 반환
        if unused_coupons:
            return unused_coupons[0]
        
        # 모든 쿠폰이 사용된 경우 빈 응답
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-NOT-YOURS":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ERR-NOT-YOURS"},
            )
        elif error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )

