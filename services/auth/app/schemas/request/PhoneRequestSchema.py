from pydantic import BaseModel, Field


class PhoneRequest(BaseModel):
    """
    휴대폰 인증 요청 단계에서 필요한 최소 정보.
    """

    phone: str = Field(..., description="인증을 요청하는 휴대폰 번호")
