from pydantic import BaseModel, Field


class PartnerLoginSchema(BaseModel):
    """
    파트너 회원 PIN 로그인 요청 본문.
    """

    phoneNumber: str | None = Field(
        default=None, description="휴대폰 번호 (선택)"
    )
    pin: str | None = Field(
        default=None,
        description="SHA-256 으로 해시된 6자리 PIN (선택)",
    )
