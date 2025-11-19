from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from fastapi_pagination import Page

from libs.common import CurrentUser

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.request import (
    PaymentConfirmSchema,
    PaymentTransactionSchema,
)
from services.coupon.app.schemas.response import (
    PaymentLogItem,
    PaymentTransactionResponse,
)

# 결제 로그 관련 라우터
router = APIRouter(prefix="/payments", tags=["Payment"])


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


@router.get("/transaction", response_model=PaymentTransactionResponse, status_code=status.HTTP_200_OK)
async def get_payment_transaction(
    current_user: CurrentUser,
    payload: PaymentTransactionSchema = Body(...),
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    결제QR에서 추출한 결제코드를 조회합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Request Body:**
    - `code`: 결제코드
    
    **Response:**
    - HTTP 200 OK: 쿠폰 정보 반환
    - HTTP 400 Bad Request: 올바르지 않은 결제코드 `{"code": "ERR-IVD-VALUE"}`
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    - HTTP 406 Not Acceptable: 이미 사용한 경우 (빈 응답)
    """
    subject_type, subject_id = current_user
    
    try:
        # 결제코드로 쿠폰 정보 조회
        result = await coupon_service.get_payment_transaction(
            payment_code=payload.code,
        )
        return result
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        elif error_code == "ERR-ALREADY-USED":
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.post("/transaction/confirm", status_code=status.HTTP_200_OK)
async def confirm_payment_transaction(
    payload: PaymentConfirmSchema,
    current_user: CurrentUser,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    쿠폰을 결제처리합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Request Body:**
    - `code`: 결제코드
    
    **Response:**
    - HTTP 200 OK: 결제 성공 (빈 응답)
    - HTTP 400 Bad Request: 올바르지 않은 결제코드 `{"code": "ERR-IVD-VALUE"}`
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    - HTTP 406 Not Acceptable: 이미 사용한 경우 (빈 응답)
    
    **처리 내용:**
    - use_logs 테이블에 사용 기록 생성
    - coupons 테이블의 use_log_id 업데이트
    - 해당 issue_id의 모든 쿠폰이 결제되었으면 issue_logs의 status를 'ISSUE_STATUS/COMPLETED'로 변경
    """
    subject_type, subject_id = current_user
    
    try:
        # 결제코드로 쿠폰 결제 처리
        await coupon_service.confirm_payment_transaction(
            payment_code=payload.code,
        )
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        elif error_code == "ERR-ALREADY-USED":
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )

