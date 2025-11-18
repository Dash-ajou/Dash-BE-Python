from pydantic import BaseModel, Field


class MemberLoginSchema(BaseModel):
    """
    개인 회원 로그인 요청 본문.
    """

    phoneAuthToken: str = Field(..., description="핸드폰 인증토큰")
