from pydantic import BaseModel, Field


class PartnerLoginSchema(BaseModel):
    """
    파트너 회원 PIN 로그인 요청 본문.
    """

    phoneAuthToken: str = Field(..., description="핸드폰 인증토큰")
    pin: str = Field(..., min_length=6, max_length=6, description="6자리 로그인 PIN")
