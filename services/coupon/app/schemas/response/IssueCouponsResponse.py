from pydantic import BaseModel, Field


class VendorInfoInCoupons(BaseModel):
    """벤더(요청자) 정보 (쿠폰 내역용)"""
    memberId: int = Field(..., description="회원 ID")
    memberName: str = Field(..., description="회원 이름")
    number: str = Field(..., description="전화번호")

    class Config:
        from_attributes = True


class PartnerInfoInCoupons(BaseModel):
    """파트너 정보 (쿠폰 내역용)"""
    partnerId: int | None = Field(None, description="파트너 ID")
    partnerName: str | None = Field(None, description="파트너명")
    number: str | None = Field(None, description="대표 전화번호")

    class Config:
        from_attributes = True


class ProductInfoInCoupons(BaseModel):
    """상품 정보 (쿠폰 내역용)"""
    productId: int | None = Field(None, description="상품 ID")
    productName: str = Field(..., description="상품명")
    count: int = Field(..., description="승인된 수량")

    class Config:
        from_attributes = True


class IssueInfo(BaseModel):
    """승인된 발행기록 정보"""
    requestedIssueCount: int = Field(..., description="요청 발행 수량")
    approvedIssueCount: int = Field(..., description="승인된 발행 수량")
    validDays: int = Field(..., description="쿠폰 유효 일수")
    vendor: VendorInfoInCoupons = Field(..., description="벤더(요청자) 정보")
    partner: PartnerInfoInCoupons = Field(..., description="파트너 정보")
    products: list[ProductInfoInCoupons] = Field(..., description="상품 목록")
    requestedAt: str = Field(..., description="발행 요청 일시 (YYYY.MM.DD HH:MM:SS)")
    decidedAt: str = Field(..., description="발행 승인 일시 (YYYY.MM.DD HH:MM:SS)")
    expiredAt: str = Field(..., description="쿠폰 만료 일시 (YYYY.MM.DD HH:MM:SS)")

    class Config:
        from_attributes = True


class RejectInfo(BaseModel):
    """반려된 발행기록 정보"""
    requestedIssueCount: int = Field(..., description="요청 발행 수량")
    reason: str = Field(..., description="반려 사유")
    requestedAt: str = Field(..., description="발행 요청 일시 (YYYY.MM.DD HH:MM:SS)")
    decidedAt: str = Field(..., description="발행 거절 일시 (YYYY.MM.DD HH:MM:SS)")

    class Config:
        from_attributes = True


class IssueCouponsResponse(BaseModel):
    """발행기록 쿠폰 내역/반려 정보 응답"""
    isApproved: bool = Field(..., description="승인 여부")
    issueInfo: IssueInfo | None = Field(None, description="승인된 경우 발행기록 정보")
    rejectInfo: RejectInfo | None = Field(None, description="반려된 경우 반려 정보")

    class Config:
        from_attributes = True

