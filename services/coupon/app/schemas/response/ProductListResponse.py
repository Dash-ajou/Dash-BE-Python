from pydantic import BaseModel, Field


class ProductListItem(BaseModel):
    """상품 목록 항목"""
    productId: int = Field(..., description="상품 고유 식별자")
    productName: str = Field(..., description="상품명")

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """상품 목록 응답"""
    items: list[ProductListItem] = Field(..., description="상품 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    pages: int = Field(..., description="전체 페이지 수")

    class Config:
        from_attributes = True

