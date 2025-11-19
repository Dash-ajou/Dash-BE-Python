from pydantic import BaseModel, Field


class CouponAddSchema(BaseModel):
    """쿠폰 등록 요청 스키마"""
    registrationCode: str = Field(..., description="쿠폰 등록 코드")

    class Config:
        from_attributes = True

