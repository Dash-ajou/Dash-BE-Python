from pydantic import BaseModel, Field


class QrCodeResponse(BaseModel):
    """QR 코드 생성 응답 스키마"""
    fileId: str = Field(..., description="파일 고유 ID (UUID)")

    class Config:
        from_attributes = True

