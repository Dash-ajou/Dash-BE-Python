from pydantic import BaseModel, Field


class DepartUpdateSchema(BaseModel):
    """
    소속정보 업데이트 요청 본문.
    """

    departAt: list[str] = Field(
        ...,
        description="소속 그룹 ID 목록 (전체 목록을 전달해야 함, 부분 업데이트 불가)",
        examples=[["DEPART_ID_A", "DEPART_ID_B", "DEPART_ID_C"]],
    )

