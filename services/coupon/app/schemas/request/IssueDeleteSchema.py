from pydantic import BaseModel, Field


class IssueDeleteSchema(BaseModel):
    """이슈 삭제 요청 스키마"""
    issues: list[int] = Field(..., description="삭제할 이슈 ID 목록", min_length=1)

    class Config:
        from_attributes = True

