from pydantic import BaseModel, Field


class PaymentQrSchema(BaseModel):
    """결제 QR 생성 요청 스키마"""
    couponId: int = Field(..., description="쿠폰 ID", gt=0)

    class Config:
        from_attributes = True

