from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 결제 로그 관련 라우터
router = APIRouter(prefix="/coupons/pay", tags=["Coupon Payment"])

# Swagger UI에서 Bearer token을 입력할 수 있도록 HTTPBearer 설정
security = HTTPBearer(description="Access Token (Bearer)", auto_error=False)


@router.get("/log")
async def get_payment_log(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
):
    """
    쿠폰 결제 로그를 조회합니다.
    
    **Headers:**
    - `Authorization`: Bearer {access_token} (필수)
    
    **Response:**
    - HTTP 200 OK: 결제 로그 목록 반환
    - HTTP 401 Unauthorized: 인증 실패
    """
    # TODO: 인증 검증 및 결제 로그 조회 로직 구현
    return {"message": "쿠폰 결제 로그 조회 API - 구현 예정"}

