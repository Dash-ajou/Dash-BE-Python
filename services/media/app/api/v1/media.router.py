"""
미디어 파일 관련 라우터
"""
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from services.media.app.core.MediaService import MediaService
from services.media.app.dependencies import get_media_service
from services.media.app.schemas.request import (
    MediaGenerateSchema,
    QrCodeGenerateSchema,
)
from services.media.app.schemas.response import (
    MediaResponse,
    QrCodeResponse,
    SignatureUploadResponse,
)

router = APIRouter(tags=["Media"])


@router.post("/generate", response_model=MediaResponse, status_code=status.HTTP_200_OK)
async def generate_media(
    payload: MediaGenerateSchema,
    media_service: MediaService = Depends(get_media_service),
):
    """
    내부 MSA로부터 요청을 받아 미디어 파일을 생성합니다.
    
    **Request Body:**
    - `type`: 미디어 타입 ("pdf", "csv", "excel")
    - `data`: 미디어 생성에 필요한 데이터
      - PDF: `{"title": "제목", "content": "내용", "items": ["항목1", "항목2"]}`
      - CSV: `{"headers": ["헤더1", "헤더2"], "rows": [["값1", "값2"], ["값3", "값4"]]}`
      - Excel: `{"sheet_name": "시트명", "headers": ["헤더1", "헤더2"], "rows": [["값1", "값2"]]}`
    - `file_name`: 파일명 (선택사항)
    
    **Response:**
    - HTTP 200 OK: 미디어 생성 성공, 미디어 정보 반환
    - HTTP 400 Bad Request: 유효하지 않은 요청 `{"code": "ERR-IVD-VALUE"}`
    
    **참고:**
    - 인증이 필요하지 않습니다.
    - 내부 MSA 간 통신용입니다.
    """
    try:
        result = await media_service.generate_media(
            media_type=payload.type.value,
            data=payload.data,
            file_name=payload.file_name,
        )
        return result
    except ValueError as e:
        error_code = str(e)
        if "지원하지 않는 미디어 타입" in error_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.post("/upload", response_model=MediaResponse, status_code=status.HTTP_200_OK)
async def upload_file(
    file: UploadFile = File(...),
    media_service: MediaService = Depends(get_media_service),
):
    """
    외부에서 파일을 업로드합니다.
    
    **Request:**
    - `file`: 업로드할 파일 (multipart/form-data)
    
    **Response:**
    - HTTP 200 OK: 파일 업로드 성공, 미디어 정보 반환
    - HTTP 400 Bad Request: 유효하지 않은 파일 `{"code": "ERR-IVD-VALUE"}`
    
    **참고:**
    - 인증이 필요하지 않습니다.
    - 외부 클라이언트용입니다.
    - 허용된 파일 확장자: jpg, jpeg, png, gif, pdf, csv, xlsx, xls
    - 최대 파일 크기: 10MB
    """
    try:
        # 파일 읽기
        file_content = await file.read()
        
        # MIME 타입 확인
        mime_type = file.content_type or "application/octet-stream"
        
        # 파일 업로드
        result = await media_service.upload_file(
            file_content=file_content,
            file_name=file.filename or "uploaded_file",
            mime_type=mime_type,
        )
        return result
    except ValueError as e:
        error_code = str(e)
        if "ERR-IVD-VALUE" in error_code or "파일 크기" in error_code or "허용되지 않는" in error_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.get("/media/{file_id}", status_code=status.HTTP_200_OK)
async def get_media_file(
    file_id: str,
    media_service: MediaService = Depends(get_media_service),
):
    """
    파일 ID로 파일을 조회/다운로드합니다.
    
    **URL Parameters:**
    - `file_id`: 파일 고유 ID (UUID)
    
    **Response:**
    - HTTP 200 OK: 파일 다운로드
    - HTTP 400 Bad Request: 파일을 찾을 수 없음 `{"code": "ERR-IVD-VALUE"}`
    
    **참고:**
    - 인증이 필요하지 않습니다.
    - 파일 ID는 미디어 생성 또는 업로드 시 반환된 `fileId`를 사용합니다.
    """
    try:
        file_content, media_data = await media_service.get_media_file(file_id)
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_data["mime_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{media_data["file_name"]}"',
            },
        )
    except ValueError as e:
        error_code = str(e)
        if error_code == "ERR-IVD-VALUE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.post("/generate/qrcode", response_model=QrCodeResponse, status_code=status.HTTP_200_OK)
async def generate_qr_code(
    payload: QrCodeGenerateSchema,
    media_service: MediaService = Depends(get_media_service),
):
    """
    내부 MSA로부터 요청을 받아 QR 코드 이미지를 생성합니다.
    
    **Request Body:**
    - `data`: QR 코드에 담을 데이터 (결제코드 등)
    - `file_name`: 파일명 (선택사항)
    
    **Response:**
    - HTTP 200 OK: QR 코드 생성 성공, 파일 ID 반환
    - HTTP 400 Bad Request: QR 코드 생성 실패 `{"code": "ERR-IVD-VALUE"}`
    
    **참고:**
    - 인증이 필요하지 않습니다.
    - 내부 MSA 간 통신용입니다.
    """
    try:
        file_id = await media_service.generate_qr_code(
            data=payload.data,
            file_name=payload.file_name,
        )
        return QrCodeResponse(fileId=file_id)
    except ValueError as e:
        error_code = str(e)
        if "QR 코드 생성 실패" in error_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )


@router.post("/upload/signature", response_model=SignatureUploadResponse, status_code=status.HTTP_200_OK)
async def upload_signature(
    signature: UploadFile = File(..., alias="signature"),
    media_service: MediaService = Depends(get_media_service),
):
    """
    쿠폰에 대한 서명 이미지를 업로드합니다.
    
    **Request:**
    - `signature`: 서명 이미지 파일 (PNG, multipart/form-data)
    
    **Response:**
    - HTTP 200 OK: 업로드 성공, 서명 코드 반환
    - HTTP 400 Bad Request: 유효하지 않은 파일 `{"code": "ERR-IVD-VALUE"}`
    
    **참고:**
    - 인증이 필요하지 않습니다.
    - PNG 파일만 허용됩니다.
    - 최대 파일 크기: 10MB
    - 반환된 `signatureCode`는 쿠폰 등록 시 사용됩니다.
    """
    try:
        # 파일 읽기
        file_content = await signature.read()
        
        # MIME 타입 확인
        mime_type = signature.content_type or "application/octet-stream"
        
        # 서명 이미지 업로드
        signature_code = await media_service.upload_signature(
            file_content=file_content,
            file_name=signature.filename or "signature.png",
            mime_type=mime_type,
        )
        
        return SignatureUploadResponse(signatureCode=signature_code)
    except ValueError as e:
        error_code = str(e)
        if "ERR-IVD-VALUE" in error_code or "파일 크기" in error_code or "PNG 파일만" in error_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-IVD-VALUE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": error_code},
            )

