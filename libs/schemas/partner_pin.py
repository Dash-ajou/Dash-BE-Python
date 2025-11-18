from datetime import datetime

from pydantic import BaseModel, Field

from libs.schemas.partner_user import PartnerUser


class PartnerPin(BaseModel):
    """
    파트너 로그인 PIN 엔티티.
    """

    pinId: int = Field(..., description="PIN 고유 식별자")
    partnerId: int = Field(..., description="소유 파트너 식별자")
    partner: PartnerUser | None = Field(
        None,
        description="연결된 파트너 정보 (선택)",
    )
    pin: str = Field(..., description="로그인 PIN 값")
    createdAt: datetime = Field(..., description="PIN 생성 일시")

    class Config:
        orm_mode = True

