from pydantic import BaseModel, Field


class PartnerInfo(BaseModel):
    """파트너 정보"""
    partnerId: int = Field(..., description="파트너 고유 식별자")
    partnerName: str = Field(..., description="파트너명")
    phones: list[str] = Field(default_factory=list, description="전화번호 목록")

    class Config:
        from_attributes = True


class RegisterInfo(BaseModel):
    """등록자 정보"""
    memberId: int = Field(..., description="회원 고유 식별자")
    memberName: str = Field(..., description="회원 이름")
    memberBirth: str = Field(..., description="회원 생년월일 (YYYY-MM-DD)")

    class Config:
        from_attributes = True


class RegisterLogInfo(BaseModel):
    """등록 로그 정보"""
    registerLogId: int = Field(..., description="등록 로그 식별자")
    registeredAt: str | None = Field(None, description="등록 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True


class UseLogInfo(BaseModel):
    """사용 로그 정보"""
    useLogId: int = Field(..., description="사용 로그 식별자")
    usedAt: str | None = Field(None, description="사용 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True


class CouponDetailResponse(BaseModel):
    """쿠폰 상세 정보 응답"""
    id: int = Field(..., description="쿠폰 고유 식별자")
    productName: str = Field(..., description="상품명")
    partner: PartnerInfo = Field(..., description="파트너 정보")
    register: RegisterInfo = Field(..., description="등록자 정보", serialization_alias="register")
    registerLog: RegisterLogInfo | None = Field(None, description="등록 로그 정보")
    isUsed: bool = Field(..., description="사용 여부")
    useLog: UseLogInfo | None = Field(None, description="사용 로그 정보 (사용한 경우만)")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")
    expiredAt: str = Field(..., description="만료 일시 (YYYY-MM-DD HH:MM:SS)")
    
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

