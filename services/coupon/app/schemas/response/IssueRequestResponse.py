from pydantic import BaseModel, Field


class VendorInfo(BaseModel):
    """벤더(요청자) 정보"""
    memberId: int = Field(..., description="회원 ID")
    memberName: str = Field(..., description="회원 이름")
    number: str = Field(..., description="전화번호")

    class Config:
        from_attributes = True


class PartnerInfoInRequest(BaseModel):
    """파트너 정보 (발행요청서용)"""
    partnerId: int | None = Field(None, description="파트너 ID (파트너가 아직 가입하지 않은 경우 null)")
    partnerName: str | None = Field(None, description="파트너명 (파트너가 아직 가입하지 않은 경우 null)")
    number: str | None = Field(None, description="대표 전화번호 (파트너가 아직 가입하지 않은 경우 null)")

    class Config:
        from_attributes = True


class ProductInfoInRequest(BaseModel):
    """상품 정보 (발행요청서용)"""
    productId: int | None = Field(None, description="상품 ID (신규 상품인 경우 null)")
    productName: str = Field(..., description="상품명")
    count: int = Field(..., description="요청 수량")

    class Config:
        from_attributes = True


class IssueRequestResponse(BaseModel):
    """발행요청서 정보 응답"""
    issueId: int = Field(..., description="발행 이력 식별자")
    title: str = Field(..., description="발행 요청 제목")
    status: str = Field(..., description="발행 상태")
    vendor: VendorInfo = Field(..., description="벤더(요청자) 정보")
    partner: PartnerInfoInRequest = Field(..., description="파트너 정보")
    products: list[ProductInfoInRequest] = Field(..., description="상품 목록")
    requestedAt: str = Field(..., description="발행 요청 일시 (YYYY.MM.DD HH:MM:SS 형식)")

    class Config:
        from_attributes = True

