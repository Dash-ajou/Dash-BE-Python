from datetime import datetime

from pydantic import BaseModel, Field


class PartnerUser(BaseModel):
    """
    파트너회원(PartnerUser) 엔티티 정의.
    """

    partnerId: int = Field(..., description="파트너 고유 식별자")
    partnerName: str = Field(..., description="파트너 회원 이름")
    createdAt: datetime = Field(..., description="파트너 생성 일시")

    class Config:
        orm_mode = True

