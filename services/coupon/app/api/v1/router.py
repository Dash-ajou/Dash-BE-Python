from fastapi import APIRouter

# 기본 라우터 생성
router = APIRouter(tags=["Coupon"])


@router.get("/")
def read_root():
    """쿠폰 서비스 루트 엔드포인트"""
    return {"service": "Coupon Service", "status": "running"}

