from datetime import datetime

from pydantic import BaseModel, Field

from libs.schemas.member import Member
from libs.schemas.partner_user import PartnerUser
from libs.schemas.product import Product
from libs.schemas.register_log import RegisterLog
from libs.schemas.use_log import UseLog


class Coupon(BaseModel):
    """
    쿠폰 엔티티 정의.
    """

    couponId: int = Field(..., description="쿠폰 고유 식별자")
    issueId: int = Field(..., description="발급 이력 식별자")

    productId: int = Field(..., description="연결된 상품 ID")
    product: Product | None = Field(None, description="연결된 상품 정보")

    registrationCode: str = Field(..., description="쿠폰 등록 코드")

    partnerId: int = Field(..., description="파트너 회원 ID")
    partnerUser: PartnerUser | None = Field(None, description="연결된 파트너 회원")

    registerId: int | None = Field(..., description="등록자(회원) ID")
    registerUser: Member | None = Field(
        default=None,
        description="등록자 회원 정보 (선택)",
    )

    useLogId: int | None = Field(None, description="사용 로그 ID")
    useLog: UseLog | None = Field(None, description="사용 로그 정보")

    registerLogId: int | None = Field(None, description="등록 로그 ID")
    registerLog: RegisterLog | None = Field(None, description="등록 로그 정보")

    createdAt: datetime = Field(..., description="쿠폰 생성 일시")
    expiredAt: datetime = Field(..., description="쿠폰 만료 일시")

    class Config:
        orm_mode = True

