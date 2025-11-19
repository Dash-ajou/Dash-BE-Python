from pydantic import BaseModel, Field


class CouponAddResponse(BaseModel):
    """쿠폰 등록 응답 스키마"""
    couponId: int = Field(..., description="쿠폰 고유 식별자")
    productName: str = Field(..., description="상품명")
    partnerName: str = Field(..., description="파트너명")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")
    expiredAt: str = Field(..., description="만료 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

