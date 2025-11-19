from pydantic import BaseModel, Field


class CouponDeleteSchema(BaseModel):
    """쿠폰 삭제 요청 스키마"""
    coupons: list[int] = Field(..., description="삭제할 쿠폰 ID 목록", min_length=1)

    class Config:
        from_attributes = True

