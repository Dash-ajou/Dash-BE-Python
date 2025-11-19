from pydantic import BaseModel, Field


class CouponRegisterSchema(BaseModel):
    """쿠폰 등록 요청 스키마"""
    registrationCode: str = Field(..., description="쿠폰 등록 코드")
    signatureCode: str = Field(..., description="서명 이미지 코드")

    class Config:
        from_attributes = True

