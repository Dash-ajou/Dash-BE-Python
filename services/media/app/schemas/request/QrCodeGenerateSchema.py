from pydantic import BaseModel, Field


class QrCodeGenerateSchema(BaseModel):
    """QR 코드 생성 요청 스키마"""
    data: str = Field(..., description="QR 코드에 담을 데이터 (결제코드 등)")
    file_name: str | None = Field(None, description="파일명 (선택사항)")

    class Config:
        from_attributes = True

