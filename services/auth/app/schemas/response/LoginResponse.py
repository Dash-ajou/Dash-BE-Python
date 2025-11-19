from pydantic import BaseModel, Field, ConfigDict


class LoginResponse(BaseModel):
    """
    로그인 성공 응답.
    개인회원 및 파트너회원 로그인 공통 응답 형식.
    """

    accessToken: str = Field(..., description="액세스 토큰", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    userName: str = Field(..., description="사용자 이름 (개인회원: memberName, 파트너: partnerName)", examples=["홍길동", "파트너 업체명"])
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "userName": "홍길동"
            }
        }
    )

