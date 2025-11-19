from pydantic import BaseModel, Field


class MediaResponse(BaseModel):
    """미디어 생성/업로드 응답 스키마"""
    mediaId: int = Field(..., description="미디어 파일 식별자")
    fileId: str = Field(..., description="파일 고유 ID (UUID)")
    fileName: str = Field(..., description="파일명")
    fileExtension: str = Field(..., description="파일 확장자")
    fileSize: int = Field(..., description="파일 크기 (바이트)")
    mimeType: str = Field(..., description="MIME 타입")
    createdAt: str = Field(..., description="생성 일시 (YYYY-MM-DD HH:MM:SS)")

    class Config:
        from_attributes = True

