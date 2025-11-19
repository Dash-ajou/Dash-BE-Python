from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from services.auth.app.schemas.response import GroupItem


class MemberInfoResponse(BaseModel):
    """개인회원 정보 응답"""
    memberId: int = Field(..., description="회원 고유 식별자")
    memberName: str = Field(..., description="회원 이름")
    memberBirth: str = Field(..., description="회원 생년월일 (YYYY-MM-DD)")
    number: str = Field(..., description="전화번호 (010-1234-1234 형식)")
    groups: List[GroupItem] = Field(default_factory=list, description="소속 그룹 목록")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True


class PartnerInfoResponse(BaseModel):
    """파트너회원 정보 응답"""
    partnerId: int = Field(..., description="파트너 고유 식별자")
    partnerName: str = Field(..., description="파트너 이름")
    numbers: List[str] = Field(default_factory=list, description="전화번호 목록 (010-1234-1234 형식)")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

