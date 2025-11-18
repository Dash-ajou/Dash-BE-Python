from pydantic import BaseModel, Field


class PhoneRequestResponse(BaseModel):
    """
    휴대폰 인증 요청 응답.
    """

    isUsed: bool = Field(..., description="해당 번호가 이미 사용 중인지 여부")
    userType: str | None = Field(
        None,
        description="사용자 타입 (예: 'USER_TYPE/PERSONAL', 'USER_TYPE/PARTNER')",
    )

