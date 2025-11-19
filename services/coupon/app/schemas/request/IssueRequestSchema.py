from pydantic import BaseModel, Field
from typing import Literal


class PartnerRequestSchema(BaseModel):
    """파트너 요청 스키마"""
    isNew: bool = Field(..., description="신규 파트너 여부")
    partnerId: int | None = Field(None, description="기존 파트너 ID (isNew가 false인 경우 필수)")
    partnerName: str | None = Field(None, description="신규 파트너명 (isNew가 true인 경우 필수)")
    partnerPhone: str | None = Field(None, description="신규 파트너 전화번호 (isNew가 true인 경우 필수)")

    class Config:
        from_attributes = True


class ProductRequestSchema(BaseModel):
    """상품 요청 스키마"""
    isNew: bool = Field(..., description="신규 상품 여부")
    productId: int | None = Field(None, description="기존 상품 ID (isNew가 false인 경우 필수)")
    productName: str | None = Field(None, description="신규 상품명 (isNew가 true인 경우 필수)")
    count: int = Field(..., description="요청 수량", gt=0)

    class Config:
        from_attributes = True


class IssueRequestSchema(BaseModel):
    """이슈 요청 생성 스키마"""
    title: str = Field(..., description="발행 요청 제목", min_length=1)
    partner: PartnerRequestSchema = Field(..., description="파트너 정보")
    products: list[ProductRequestSchema] = Field(..., description="상품 목록", min_length=1)

    class Config:
        from_attributes = True

