from pydantic import BaseModel, Field


class IssueListItem(BaseModel):
    """이슈(쿠폰 발행 이력) 목록 항목"""
    requestId: int = Field(..., description="발행 이력 식별자")
    title: str = Field(..., description="발행 요청 제목")
    productKindCount: int = Field(..., description="요청한 상품 종류 수")
    status: str = Field(..., description="발행 상태")

    class Config:
        from_attributes = True
        populate_by_name = True


class IssueListResponse(BaseModel):
    """이슈 목록 응답"""
    items: list[IssueListItem] = Field(..., description="이슈 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    pages: int = Field(..., description="전체 페이지 수")

    class Config:
        from_attributes = True

