from typing import List

from pydantic import BaseModel, Field


class MemberJoinSchema(BaseModel):
    """
    개인 회원 가입 요청 본문.
    """

    phoneAuthToken: str = Field(..., description="핸드폰 인증토큰")
    memberName: str = Field(..., description="회원 이름")
    memberBirth: str = Field(..., description="회원 생년월일 (YYYY-MM-DD)")
    departAt: List[str] = Field(..., description="선택한 소속 ID 목록")