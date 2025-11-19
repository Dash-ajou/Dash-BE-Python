from pydantic import BaseModel, Field


class PhoneUpdateSchema(BaseModel):
    """
    전화번호 변경 요청 본문.
    """
    phoneAuthToken: str = Field(..., description="휴대폰 인증 토큰")

