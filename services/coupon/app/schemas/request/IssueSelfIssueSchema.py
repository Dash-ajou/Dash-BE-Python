from pydantic import BaseModel, Field
from typing import Optional


class ProductSelfIssueSchema(BaseModel):
    """자체 발행 상품 스키마"""
    isNew: bool = Field(..., description="신규 상품 여부")
    productId: Optional[int] = Field(None, description="기존 상품 ID (isNew가 false인 경우 필수)")
    productName: Optional[str] = Field(None, description="신규 상품명 (isNew가 true인 경우 필수)")
    count: int = Field(..., description="발행 수량", gt=0)

    class Config:
        from_attributes = True


class IssueSelfIssueSchema(BaseModel):
    """이슈 자체 발행 스키마"""
    title: str = Field(..., description="발행 제목", min_length=1)
    products: list[ProductSelfIssueSchema] = Field(..., description="상품 목록", min_length=1)

    class Config:
        from_attributes = True

