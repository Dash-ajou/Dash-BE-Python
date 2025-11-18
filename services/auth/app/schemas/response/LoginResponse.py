from pydantic import BaseModel, Field


class LoginResponse(BaseModel):
    """
    로그인 성공 응답.
    개인회원 및 파트너회원 로그인 공통 응답 형식.
    """

    accessToken: str = Field(..., description="액세스 토큰")

