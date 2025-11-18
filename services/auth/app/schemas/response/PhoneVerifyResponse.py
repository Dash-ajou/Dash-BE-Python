from pydantic import BaseModel, Field


class PhoneVerifyResponse(BaseModel):
    """
    휴대폰 인증 완료 응답.
    """

    phoneAuthToken: str = Field(..., description="휴대폰 인증 성공 시 발급되는 토큰")

