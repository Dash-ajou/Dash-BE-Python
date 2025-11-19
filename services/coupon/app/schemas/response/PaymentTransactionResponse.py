from pydantic import BaseModel, Field


class PaymentTransactionResponse(BaseModel):
    """결제코드 조회 응답 스키마"""
    couponId: int = Field(..., description="쿠폰 고유 식별자")
    productName: str = Field(..., description="상품명")
    vendorName: str = Field(..., description="벤더(회원) 이름")
    createdAt: str = Field(..., description="쿠폰 생성 일시 (YYYY-MM-DD HH:MM:SS)")
    expiredAt: str = Field(..., description="쿠폰 만료 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

