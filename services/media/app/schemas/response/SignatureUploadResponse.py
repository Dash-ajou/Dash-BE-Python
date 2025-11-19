from pydantic import BaseModel, Field


class SignatureUploadResponse(BaseModel):
    """서명 이미지 업로드 응답 스키마"""
    signatureCode: str = Field(..., description="서명 코드 (파일 ID)")

    class Config:
        from_attributes = True

