from pydantic import BaseModel, Field
from typing import Optional


class ProductDecisionSchema(BaseModel):
    """상품 결정 스키마"""
    isNew: bool = Field(..., description="신규 상품 여부")
    productId: Optional[int] = Field(None, description="기존 상품 ID (isNew가 false인 경우 필수)")
    productName: Optional[str] = Field(None, description="신규 상품명 (isNew가 true인 경우 필수)")
    count: int = Field(..., description="승인 수량", gt=0)

    class Config:
        from_attributes = True


class IssueDecisionSchema(BaseModel):
    """이슈 결정 스키마"""
    issueId: int = Field(..., description="발행기록 ID")
    isApproved: bool = Field(..., description="승인 여부")
    products: Optional[list[ProductDecisionSchema]] = Field(None, description="승인된 상품 목록 (isApproved가 true인 경우 필수)")
    reason: Optional[str] = Field(None, description="반려 사유 (isApproved가 false인 경우 필수)")

    class Config:
        from_attributes = True

