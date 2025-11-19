from pydantic import BaseModel, Field


class CouponListItem(BaseModel):
    """쿠폰 목록 항목"""
    couponId: int = Field(..., description="쿠폰 고유 식별자")
    productName: str = Field(..., description="상품명")
    partnerName: str = Field(..., description="파트너명")
    isUsed: bool = Field(..., description="사용 여부")
    signature: str = Field(..., description="이미지 URL")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")
    expiredAt: str = Field(..., description="만료 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

