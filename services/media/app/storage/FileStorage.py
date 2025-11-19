"""
파일 저장소 모듈
파일 저장, 조회, 삭제 등의 기능을 제공합니다.
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from services.media.app.db.connection import settings


class FileStorage:
    """파일 저장소 클래스"""
    
    def __init__(self, base_path: str | None = None):
        """
        Args:
            base_path: 파일 저장 기본 경로 (None이면 settings에서 가져옴)
        """
        self.base_path = Path(base_path or settings.MEDIA_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(
        self,
        file_content: bytes | BinaryIO,
        file_extension: str,
        subdirectory: str | None = None,
    ) -> tuple[str, Path]:
        """
        파일을 저장하고 파일 ID와 경로를 반환합니다.
        
        Args:
            file_content: 파일 내용 (bytes 또는 BinaryIO)
            file_extension: 파일 확장자 (예: "pdf", "csv")
            subdirectory: 하위 디렉터리 (선택사항, 예: "pdfs", "images")
            
        Returns:
            (file_id, file_path) 튜플
        """
        # 고유한 파일 ID 생성
        file_id = str(uuid.uuid4())
        
        # 파일 확장자 정규화 (점 제거, 소문자)
        ext = file_extension.lstrip(".").lower()
        
        # 저장 경로 결정
        if subdirectory:
            save_dir = self.base_path / subdirectory
        else:
            save_dir = self.base_path
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명: {file_id}.{extension}
        file_path = save_dir / f"{file_id}.{ext}"
        
        # 파일 저장
        if isinstance(file_content, bytes):
            file_path.write_bytes(file_content)
        else:
            # BinaryIO인 경우
            file_path.write_bytes(file_content.read())
        
        return file_id, file_path
    
    def get_file_path(self, file_id: str, file_extension: str | None = None) -> Path | None:
        """
        파일 ID로 파일 경로를 조회합니다.
        
        Args:
            file_id: 파일 ID
            file_extension: 파일 확장자 (선택사항, 없으면 모든 확장자 검색)
            
        Returns:
            파일 경로 또는 None (파일이 없는 경우)
        """
        if file_extension:
            # 확장자가 지정된 경우
            ext = file_extension.lstrip(".").lower()
            
            # 먼저 base_path에서 검색
            file_path = self.base_path / f"{file_id}.{ext}"
            if file_path.exists():
                return file_path
            
            # 하위 디렉터리도 검색
            for subdir in self.base_path.iterdir():
                if subdir.is_dir():
                    file_path = subdir / f"{file_id}.{ext}"
                    if file_path.exists():
                        return file_path
        else:
            # 확장자가 없는 경우 모든 확장자 검색
            for ext in settings.allowed_extensions_list:
                # 먼저 base_path에서 검색
                file_path = self.base_path / f"{file_id}.{ext}"
                if file_path.exists():
                    return file_path
                
                # 하위 디렉터리도 검색
                for subdir in self.base_path.iterdir():
                    if subdir.is_dir():
                        file_path = subdir / f"{file_id}.{ext}"
                        if file_path.exists():
                            return file_path
        
        return None
    
    def read_file(self, file_id: str, file_extension: str | None = None) -> bytes | None:
        """
        파일을 읽어서 bytes로 반환합니다.
        
        Args:
            file_id: 파일 ID
            file_extension: 파일 확장자 (선택사항)
            
        Returns:
            파일 내용 (bytes) 또는 None (파일이 없는 경우)
        """
        file_path = self.get_file_path(file_id, file_extension)
        if file_path is None:
            return None
        
        return file_path.read_bytes()
    
    def delete_file(self, file_id: str, file_extension: str | None = None) -> bool:
        """
        파일을 삭제합니다.
        
        Args:
            file_id: 파일 ID
            file_extension: 파일 확장자 (선택사항)
            
        Returns:
            삭제 성공 여부
        """
        file_path = self.get_file_path(file_id, file_extension)
        if file_path is None:
            return False
        
        try:
            file_path.unlink()
            return True
        except OSError:
            return False
    
    def file_exists(self, file_id: str, file_extension: str | None = None) -> bool:
        """
        파일이 존재하는지 확인합니다.
        
        Args:
            file_id: 파일 ID
            file_extension: 파일 확장자 (선택사항)
            
        Returns:
            파일 존재 여부
        """
        return self.get_file_path(file_id, file_extension) is not None

