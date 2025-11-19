from pydantic import BaseModel, Field


class PaymentConfirmSchema(BaseModel):
    """결제 확인 요청 스키마"""
    code: str = Field(..., description="결제코드", min_length=1)

    class Config:
        from_attributes = True

