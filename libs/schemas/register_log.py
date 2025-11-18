from datetime import datetime

from pydantic import BaseModel, Field

from libs.schemas.member import Member


class RegisterLog(BaseModel):
    """
    쿠폰 등록 이력 엔티티.
    """

    registerLogId: int = Field(..., description="등록 로그 식별자")
    registerUser: Member | None = Field(None, description="등록을 수행한 회원")
    registeredAt: datetime | None = Field(None, description="등록 일시")

    class Config:
        from_attributes = True

