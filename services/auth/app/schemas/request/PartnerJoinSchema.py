from pydantic import BaseModel, Field


class PartnerJoinSchema(BaseModel):
    """
    파트너 회원 가입 요청 본문.
    """

    phoneAuthToken: str = Field(..., description="핸드폰 인증토큰")
    userName: str = Field(..., description="파트너 담당자 이름")
    partnerName: str = Field(..., description="파트너 업체명 또는 점포명")
    pin: str = Field(..., description="해시된 파트너 가입 PIN (userName으로 hash된 값)")