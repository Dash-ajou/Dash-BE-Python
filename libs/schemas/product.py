from pydantic import BaseModel, Field


class Product(BaseModel):
    """
    쿠폰이 연결되는 상품 엔티티.
    """

    productId: int = Field(..., description="상품 고유 식별자")
    partnerId: int = Field(..., description="상품 소속 파트너 ID")
    productName: str = Field(..., description="상품명")

    class Config:
        orm_mode = True

