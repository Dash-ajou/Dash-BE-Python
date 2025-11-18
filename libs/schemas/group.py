from pydantic import BaseModel, Field


class Group(BaseModel):
    """
    서비스 전역에서 공통으로 사용하는 그룹 정보 엔티티.
    """

    groupId: str = Field(..., description="그룹 고유 식별자")
    groupName: str | None = Field(
        None,
        description="그룹 명칭 (선택값)",
    )
    departCount: int = Field(
        ...,
        description="그룹에 속한 부서 수",
    )

    class Config:
        from_attributes = True

