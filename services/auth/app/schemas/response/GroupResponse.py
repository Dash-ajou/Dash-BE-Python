from pydantic import BaseModel, Field


class GroupItem(BaseModel):
    """그룹 정보 항목"""
    groupId: str = Field(..., description="그룹 고유 식별자")
    groupName: str | None = Field(None, description="그룹 명칭")

    class Config:
        from_attributes = True

