from pydantic import BaseModel, Field


class JoinResponse(BaseModel):
    """
    회원가입 성공 응답.
    개인회원 및 파트너회원 가입 공통 응답 형식.
    HTTP 201 Created 상태 코드와 함께 액세스 토큰을 반환합니다.
    """

    accessToken: str = Field(..., description="액세스 토큰")

