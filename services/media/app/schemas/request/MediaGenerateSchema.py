from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """미디어 생성 타입"""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"


class MediaGenerateSchema(BaseModel):
    """미디어 생성 요청 스키마"""
    type: MediaType = Field(..., description="생성할 미디어 타입")
    data: dict[str, Any] = Field(..., description="미디어 생성에 필요한 데이터")
    file_name: str | None = Field(None, description="파일명 (선택사항)")

    class Config:
        from_attributes = True

