from pydantic import BaseModel, Field


class PartnerListItem(BaseModel):
    """파트너 목록 항목"""
    partnerId: int = Field(..., description="파트너 고유 식별자")
    partnerName: str = Field(..., description="파트너 상호명")
    numbers: str = Field(..., description="전화번호 (예: 010-5678-5678)")

    class Config:
        from_attributes = True


class PartnerListResponse(BaseModel):
    """파트너 목록 응답"""
    items: list[PartnerListItem] = Field(..., description="파트너 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    pages: int = Field(..., description="전체 페이지 수")

    class Config:
        from_attributes = True

