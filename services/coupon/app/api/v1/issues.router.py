"""
이슈(쿠폰 발행 이력) 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status

from libs.common import CurrentUser

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.dependencies import get_coupon_service
from services.coupon.app.schemas.request import IssueDeleteSchema, IssueRequestSchema
from services.coupon.app.schemas.response import IssueListResponse

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.get("", response_model=IssueListResponse, status_code=status.HTTP_200_OK)
async def get_issues(
    current_user: CurrentUser,
    status: str | None = None,
    title: str | None = None,
    page: int = 1,
    size: int = 10,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    로그인된 사용자에게 권한이 부여된 쿠폰 발행기록을 조회합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `status`: 발행 상태 필터 (선택, 예: "ISSUE_STATUS/PENDING")
    - `title`: 제목 검색 필터 (선택)
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 이슈 목록 반환
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    
    **권한 규칙:**
    - 개인사용자: vendor_id가 member_id와 일치하는 경우
    - 파트너사용자: partner_id가 일치하는 경우
    """
    subject_type, subject_id = current_user
    
    # 이슈 목록 조회
    result = await coupon_service.get_issues_by_user(
        subject_type=subject_type,
        subject_id=subject_id,
        status=status,
        title=title,
        page=page,
        size=size,
    )
    
    return result


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_issues(
    payload: IssueDeleteSchema,
    current_user: CurrentUser,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    로그인된 사용자가 본인에게 권한이 부여된 쿠폰 발행기록을 삭제합니다.
    
    상태와 요청자에 따라 작업이 서로 다르게 처리됩니다:
    - (벤더요청) 파트너 승인 이전: 파트너와 벤더측 모두에서 삭제 (=DB에서 삭제)
    - (벤더요청) 파트너 승인 이후: 벤더측에서만 삭제
    - (파트너요청) 승인 이전: 벤더측에서는 거절로 처리되고 파트너측에서만 삭제
    - (파트너요청) 승인 이후: 파트너측에서만 삭제
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Request Body:**
    - `issues`: 삭제할 이슈 ID 목록
    
    **Response:**
    - HTTP 200 OK: 삭제 성공 (빈 응답)
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    - HTTP 403 Forbidden: 접근권한을 가지고 있지 않은 발행요청이 포함된 경우
      - `{"code": "ERR-NOT-YOURS"}`
    """
    subject_type, subject_id = current_user
    
    try:
        # 이슈 삭제 처리
        await coupon_service.delete_issues_by_user(
            issue_ids=payload.issues,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-NOT-YOURS":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ERR-NOT-YOURS"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.post("/requests", status_code=status.HTTP_200_OK)
async def create_issue_request(
    payload: IssueRequestSchema,
    current_user: CurrentUser,
    coupon_service: CouponService = Depends(get_coupon_service),
):
    """
    쿠폰에 대한 발행요청을 생성합니다.
    
    생성 즉시 파트너에게 전달됩니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Request Body:**
    - `title`: 발행 요청 제목
    - `partner`: 파트너 정보
      - `isNew`: 신규 파트너 여부
      - `partnerId`: 기존 파트너 ID (isNew가 false인 경우)
      - `partnerName`: 신규 파트너명 (isNew가 true인 경우)
      - `partnerPhone`: 신규 파트너 전화번호 (isNew가 true인 경우)
    - `products`: 상품 목록
      - `isNew`: 신규 상품 여부
      - `productId`: 기존 상품 ID (isNew가 false인 경우)
      - `productName`: 신규 상품명 (isNew가 true인 경우)
      - `count`: 요청 수량
    
    **Response:**
    - HTTP 200 OK: 요청 생성 성공 (빈 응답)
    - HTTP 400 Bad Request: 유효하지 않은 값인 경우 `{"code": "ERR-IVD-VALUE"}`
    - HTTP 401 Unauthorized: 인증 실패 (빈 응답)
    """
    subject_type, subject_id = current_user
    
    # 개인사용자만 요청 가능
    if subject_type != "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개인사용자만 발행 요청을 생성할 수 있습니다.",
        )
    
    try:
        # 이슈 요청 생성
        await coupon_service.create_issue_request(
            vendor_id=subject_id,
            title=payload.title,
            partner={
                "isNew": payload.partner.isNew,
                "partnerId": payload.partner.partnerId,
                "partnerName": payload.partner.partnerName,
                "partnerPhone": payload.partner.partnerPhone,
            },
            products=[
                {
                    "isNew": product.isNew,
                    "productId": product.productId,
                    "productName": product.productName,
                    "count": product.count,
                }
                for product in payload.products
            ],
        )
        return Response(status_code=status.HTTP_200_OK)
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.get("/{issueId}/requests", status_code=status.HTTP_200_OK)
async def get_issue_requests(
    issueId: int,
    current_user: CurrentUser,
    page: int = 1,
    size: int = 10,
):
    """
    특정 이슈의 요청 목록을 조회합니다.
    
    **Path Parameters:**
    - `issueId`: 이슈 ID
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 요청 목록
    - HTTP 401 Unauthorized: 인증 실패
    """
    subject_type, subject_id = current_user
    
    # TODO: 실제 구현 필요
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="이 엔드포인트는 아직 구현되지 않았습니다.",
    )


@router.get("/{issueId}/coupons", status_code=status.HTTP_200_OK)
async def get_issue_coupons(
    issueId: int,
    current_user: CurrentUser,
    page: int = 1,
    size: int = 10,
):
    """
    특정 이슈의 쿠폰 목록을 조회합니다.
    
    **Path Parameters:**
    - `issueId`: 이슈 ID
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Query Parameters:**
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    
    **Response:**
    - HTTP 200 OK: 쿠폰 목록
    - HTTP 401 Unauthorized: 인증 실패
    """
    subject_type, subject_id = current_user
    
    # TODO: 실제 구현 필요
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="이 엔드포인트는 아직 구현되지 않았습니다.",
    )


@router.get("/{issueId}/statistics", status_code=status.HTTP_200_OK)
async def get_issue_statistics(
    issueId: int,
    current_user: CurrentUser,
):
    """
    특정 이슈의 통계 정보를 조회합니다.
    
    **Path Parameters:**
    - `issueId`: 이슈 ID
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Response:**
    - HTTP 200 OK: 통계 정보
    - HTTP 401 Unauthorized: 인증 실패
    """
    subject_type, subject_id = current_user
    
    # TODO: 실제 구현 필요
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="이 엔드포인트는 아직 구현되지 않았습니다.",
    )

