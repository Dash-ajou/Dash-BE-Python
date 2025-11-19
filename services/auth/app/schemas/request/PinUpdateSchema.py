from pydantic import BaseModel, Field


class PinUpdateSchema(BaseModel):
    """
    PIN 업데이트 요청 본문.
    """

    prevPin: str = Field(..., description="현재 PIN (SHA-256으로 해시된 값)")
    newPin: str = Field(..., description="새로운 PIN (SHA-256으로 해시된 값)")

