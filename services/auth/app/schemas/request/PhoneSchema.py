from pydantic import BaseModel, Field


class PhoneSchema(BaseModel):
    """
    휴대폰 인증 완료 단계에서 전달되는 정보.
    """

    code: str = Field(..., description="입력받은 인증번호")
