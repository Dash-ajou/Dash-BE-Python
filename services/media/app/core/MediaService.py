"""
미디어 서비스
파일 생성, 업로드, 조회 등의 비즈니스 로직을 처리합니다.
"""
import io
from pathlib import Path
from typing import Protocol

from services.media.app.db.repositories.media import MediaRepositoryPort
from services.media.app.schemas.response import MediaResponse
from services.media.app.storage.FileStorage import FileStorage
from services.media.app.db.connection import settings


class MediaService:
    """미디어 서비스"""
    
    def __init__(
        self,
        media_repository: MediaRepositoryPort,
        file_storage: FileStorage | None = None,
    ):
        """
        Args:
            media_repository: 미디어 Repository
            file_storage: 파일 저장소 (None이면 기본값 사용)
        """
        self.media_repository = media_repository
        self.file_storage = file_storage or FileStorage()
    
    async def generate_media(
        self,
        media_type: str,
        data: dict,
        file_name: str | None = None,
    ) -> MediaResponse:
        """
        미디어 파일을 생성합니다 (PDF, CSV, Excel 등).
        
        Args:
            media_type: 미디어 타입 ('pdf', 'csv', 'excel')
            data: 미디어 생성에 필요한 데이터
            file_name: 파일명 (선택사항)
            
        Returns:
            생성된 미디어 정보
            
        Raises:
            ValueError: 지원하지 않는 미디어 타입이거나 생성 실패
        """
        # 미디어 타입에 따라 파일 생성
        if media_type.lower() == "pdf":
            file_content, mime_type, extension = await self._generate_pdf(data)
        elif media_type.lower() == "csv":
            file_content, mime_type, extension = await self._generate_csv(data)
        elif media_type.lower() == "excel":
            file_content, mime_type, extension = await self._generate_excel(data)
        else:
            raise ValueError(f"지원하지 않는 미디어 타입: {media_type}")
        
        # 파일 저장
        file_id, file_path = self.file_storage.save_file(
            file_content=file_content,
            file_extension=extension,
            subdirectory=media_type.lower(),
        )
        
        # 파일명 결정
        final_file_name = file_name or f"generated_{file_id}.{extension}"
        
        # DB에 저장
        media_id = await self.media_repository.create_media_file(
            file_id=file_id,
            file_name=final_file_name,
            file_extension=extension,
            file_size=len(file_content),
            mime_type=mime_type,
            file_path=str(file_path),
            source_type="GENERATE",
        )
        
        # 미디어 정보 조회
        media_data = await self.media_repository.find_media_file_by_id(media_id)
        
        return MediaResponse(
            mediaId=media_data["media_id"],
            fileId=media_data["file_id"],
            fileName=media_data["file_name"],
            fileExtension=media_data["file_extension"],
            fileSize=media_data["file_size"],
            mimeType=media_data["mime_type"],
            createdAt=media_data["created_at"],
        )
    
    async def upload_signature(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
    ) -> str:
        """
        서명 이미지를 업로드합니다.
        
        Args:
            file_content: 파일 내용
            file_name: 파일명
            mime_type: MIME 타입
            
        Returns:
            서명 코드 (file_id)
            
        Raises:
            ValueError: 파일 크기 초과 또는 PNG가 아닌 경우
        """
        # PNG 파일만 허용
        if mime_type != "image/png":
            raise ValueError("서명 이미지는 PNG 파일만 허용됩니다.")
        
        # 파일 확장자 확인
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
        if file_extension != "png":
            raise ValueError("서명 이미지는 PNG 파일만 허용됩니다.")
        
        # 파일 크기 검증
        if len(file_content) > settings.MEDIA_MAX_FILE_SIZE:
            raise ValueError(f"파일 크기가 최대 크기({settings.MEDIA_MAX_FILE_SIZE} bytes)를 초과합니다.")
        
        # 파일 저장
        file_id, file_path = self.file_storage.save_file(
            file_content=file_content,
            file_extension="png",
            subdirectory="signatures",
        )
        
        # DB에 저장
        await self.media_repository.create_media_file(
            file_id=file_id,
            file_name=file_name,
            file_extension="png",
            file_size=len(file_content),
            mime_type="image/png",
            file_path=str(file_path),
            source_type="UPLOAD",
        )
        
        return file_id
    
    async def generate_qr_code(
        self,
        data: str,
        file_name: str | None = None,
    ) -> str:
        """
        QR 코드 이미지를 생성합니다.
        
        Args:
            data: QR 코드에 담을 데이터 (결제코드 등)
            file_name: 파일명 (선택사항)
            
        Returns:
            파일 ID (file_id)
            
        Raises:
            ValueError: QR 코드 생성 실패
        """
        try:
            import qrcode
            from io import BytesIO
            
            # QR 코드 생성
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # 이미지 생성
            img = qr.make_image(fill_color="black", back_color="white")
            
            # BytesIO로 변환
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file_content = buffer.read()
            
            # 파일 저장
            file_id, file_path = self.file_storage.save_file(
                file_content=file_content,
                file_extension="png",
                subdirectory="qrcodes",
            )
            
            # 파일명 결정
            final_file_name = file_name or f"qr_{file_id}.png"
            
            # DB에 저장
            await self.media_repository.create_media_file(
                file_id=file_id,
                file_name=final_file_name,
                file_extension="png",
                file_size=len(file_content),
                mime_type="image/png",
                file_path=str(file_path),
                source_type="GENERATE",
            )
            
            return file_id
        except Exception as e:
            raise ValueError(f"QR 코드 생성 실패: {str(e)}")
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
    ) -> MediaResponse:
        """
        파일을 업로드합니다.
        
        Args:
            file_content: 파일 내용
            file_name: 파일명
            mime_type: MIME 타입
            
        Returns:
            업로드된 미디어 정보
            
        Raises:
            ValueError: 파일 크기 초과 또는 허용되지 않는 확장자
        """
        # 파일 크기 검증
        if len(file_content) > settings.MEDIA_MAX_FILE_SIZE:
            raise ValueError(f"파일 크기가 최대 크기({settings.MEDIA_MAX_FILE_SIZE} bytes)를 초과합니다.")
        
        # 파일 확장자 추출
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
        
        # 허용된 확장자 검증
        if file_extension not in settings.allowed_extensions_list:
            raise ValueError(f"허용되지 않는 파일 확장자: {file_extension}")
        
        # 파일 저장
        file_id, file_path = self.file_storage.save_file(
            file_content=file_content,
            file_extension=file_extension,
            subdirectory="uploads",
        )
        
        # DB에 저장
        media_id = await self.media_repository.create_media_file(
            file_id=file_id,
            file_name=file_name,
            file_extension=file_extension,
            file_size=len(file_content),
            mime_type=mime_type,
            file_path=str(file_path),
            source_type="UPLOAD",
        )
        
        # 미디어 정보 조회
        media_data = await self.media_repository.find_media_file_by_id(media_id)
        
        return MediaResponse(
            mediaId=media_data["media_id"],
            fileId=media_data["file_id"],
            fileName=media_data["file_name"],
            fileExtension=media_data["file_extension"],
            fileSize=media_data["file_size"],
            mimeType=media_data["mime_type"],
            createdAt=media_data["created_at"],
        )
    
    async def get_media_file(self, file_id: str) -> tuple[bytes, dict]:
        """
        파일을 조회합니다.
        
        Args:
            file_id: 파일 고유 ID (UUID)
            
        Returns:
            (파일 내용, 미디어 정보) 튜플
            
        Raises:
            ValueError: 파일을 찾을 수 없는 경우
        """
        # DB에서 미디어 정보 조회
        media_data = await self.media_repository.find_media_file_by_file_id(file_id)
        
        if media_data is None:
            raise ValueError("ERR-IVD-VALUE")
        
        # DB에 저장된 file_path를 사용하여 파일 읽기
        # file_path는 상대 경로이므로 base_path를 기준으로 계산
        stored_path = media_data["file_path"]
        
        # 절대 경로인지 확인
        if Path(stored_path).is_absolute():
            file_path = Path(stored_path)
        else:
            # 상대 경로인 경우 base_path 기준으로 계산
            # stored_path가 "storage/signatures/xxx.png" 형식이면
            # base_path가 "./storage"일 때 "./storage/storage/signatures/xxx.png"가 되지 않도록 처리
            if stored_path.startswith("storage/"):
                # "storage/" 접두사 제거
                stored_path = stored_path.replace("storage/", "", 1)
            file_path = self.file_storage.base_path / stored_path
        
        # 파일이 존재하는지 확인
        if not file_path.exists():
            raise ValueError("ERR-IVD-VALUE")
        
        # 파일 읽기
        file_content = file_path.read_bytes()
        
        return file_content, media_data
    
    async def _generate_pdf(self, data: dict) -> tuple[bytes, str, str]:
        """
        PDF 파일을 생성합니다.
        
        Args:
            data: PDF 생성에 필요한 데이터
                - title: 제목 (선택사항)
                - content: 내용 (선택사항)
                - items: 항목 리스트 (선택사항)
                
        Returns:
            (파일 내용, MIME 타입, 확장자) 튜플
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # 제목
        title = data.get("title", "Generated PDF")
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, title)
        
        # 내용
        y = 700
        content = data.get("content", "")
        if content:
            p.setFont("Helvetica", 12)
            for line in content.split("\n"):
                p.drawString(100, y, line)
                y -= 20
        
        # 항목 리스트
        items = data.get("items", [])
        if items:
            p.setFont("Helvetica", 12)
            for item in items:
                p.drawString(100, y, str(item))
                y -= 20
        
        p.save()
        buffer.seek(0)
        
        return buffer.read(), "application/pdf", "pdf"
    
    async def _generate_csv(self, data: dict) -> tuple[bytes, str, str]:
        """
        CSV 파일을 생성합니다.
        
        Args:
            data: CSV 생성에 필요한 데이터
                - headers: 헤더 리스트 (선택사항)
                - rows: 행 데이터 리스트 (선택사항)
                
        Returns:
            (파일 내용, MIME 타입, 확장자) 튜플
        """
        import csv
        
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # 헤더
        headers = data.get("headers", [])
        if headers:
            writer.writerow(headers)
        
        # 행 데이터
        rows = data.get("rows", [])
        for row in rows:
            writer.writerow(row)
        
        csv_content = buffer.getvalue().encode("utf-8-sig")  # BOM 포함 (Excel 호환)
        
        return csv_content, "text/csv", "csv"
    
    async def _generate_excel(self, data: dict) -> tuple[bytes, str, str]:
        """
        Excel 파일을 생성합니다.
        
        Args:
            data: Excel 생성에 필요한 데이터
                - sheet_name: 시트명 (선택사항)
                - headers: 헤더 리스트 (선택사항)
                - rows: 행 데이터 리스트 (선택사항)
                
        Returns:
            (파일 내용, MIME 타입, 확장자) 튜플
        """
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = data.get("sheet_name", "Sheet1")
        
        # 헤더
        headers = data.get("headers", [])
        if headers:
            ws.append(headers)
        
        # 행 데이터
        rows = data.get("rows", [])
        for row in rows:
            ws.append(row)
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"

