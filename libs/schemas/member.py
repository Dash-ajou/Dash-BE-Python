from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from libs.schemas.group import Group


class Member(BaseModel):
    """
    개인회원(Member) 엔티티 정의.
    """

    memberId: int = Field(..., description="회원 고유 식별자")
    memberName: str = Field(..., description="회원 이름")
    memberBirth: str = Field(..., description="회원 생년월일 (YYYY-MM-DD)")
    groups: List[Group] = Field(
        default_factory=list,
        description="회원이 속한 그룹 목록",
    )
    createdAt: datetime = Field(..., description="회원 생성 일시")

    class Config:
        from_attributes = True

