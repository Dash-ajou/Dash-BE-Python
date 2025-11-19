from pydantic import BaseModel, Field


class PaymentQrResponse(BaseModel):
    """결제 QR 생성 응답 스키마"""
    codeImg: str = Field(..., description="QR 코드 이미지 URL")
    expiredAt: str = Field(..., description="만료 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

