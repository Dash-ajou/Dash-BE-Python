from datetime import datetime

from pydantic import BaseModel, Field

from libs.schemas.issue_status import IssueStatus
from libs.schemas.member import Member
from libs.schemas.partner_user import PartnerUser


class IssueLog(BaseModel):
    """
    쿠폰 발행 이력 엔티티.
    """

    issueId: int = Field(..., description="발행 이력 식별자")
    title: str = Field(..., description="발행 요청 제목")
    productKindCount: int = Field(..., description="요청한 상품 종류 수")
    requestedIssueCount: int = Field(..., description="요청 발행 수량")
    approvedIssueCount: int = Field(..., description="승인된 발행 수량")
    requestedAt: datetime = Field(..., description="발행 요청 일시")
    decidedAt: datetime | None = Field(None, description="발행 승인/거절 결정 일시")
    validDays: int = Field(..., description="쿠폰 유효 일수")
    status: IssueStatus = Field(..., description="발행 상태")

    vendorId: int = Field(..., description="요청 벤더 ID")
    vendor: Member | None = Field(None, description="요청 벤더 정보")

    partnerId: int | None = Field(None, description="승인 파트너 ID")
    partner: PartnerUser | None = Field(None, description="승인 파트너 정보")

    class Config:
        from_attributes = True

