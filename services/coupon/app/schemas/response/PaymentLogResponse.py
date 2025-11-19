from pydantic import BaseModel, Field


class PaymentLogCouponInfo(BaseModel):
    """결제 로그에 포함된 쿠폰 정보"""
    couponId: int = Field(..., description="쿠폰 고유 식별자")
    productName: str = Field(..., description="상품명")
    partnerName: str = Field(..., description="파트너명")
    isUsed: bool = Field(..., description="사용 여부")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")
    expiredAt: str = Field(..., description="만료 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True


class PaymentLogItem(BaseModel):
    """결제 로그 항목"""
    useLogId: int = Field(..., description="사용 로그 식별자")
    coupon: PaymentLogCouponInfo = Field(..., description="쿠폰 정보")
    usedAt: str = Field(..., description="사용 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

