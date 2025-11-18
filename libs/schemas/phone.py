from enum import Enum

from pydantic import BaseModel, Field


class ContactAccountType(str, Enum):
    MEMBER = "MEMBER"
    PARTNER = "PARTNER"


class Phone(BaseModel):
    """
    회원/파트너의 연락처 정보를 나타내는 엔티티.
    """

    phoneId: int = Field(..., description="연락처 고유 식별자")
    contactAccountType: ContactAccountType = Field(
        ...,
        description="연락처 소유 타입 (개인회원/파트너)",
    )
    accountId: int = Field(..., description="연락처 소유 계정 ID")
    number: str = Field(..., description="전화번호")

    class Config:
        from_attributes = True

