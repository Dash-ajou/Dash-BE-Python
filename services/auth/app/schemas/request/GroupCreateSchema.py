from pydantic import BaseModel, Field


class GroupCreateSchema(BaseModel):
    """
    그룹 생성 요청 본문.
    """

    groupName: str = Field(..., description="그룹 명칭")

