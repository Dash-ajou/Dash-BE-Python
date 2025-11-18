from pydantic import BaseModel, Field


class MemberLoginSchema(BaseModel):
    """
    개인 회원 로그인 요청 본문.
    """

    phoneAuthToken: str | None = Field(
        default=None,
        description="휴대폰 인증 후 발급된 토큰 (없으면 refresh 기반 요청)",
    )
