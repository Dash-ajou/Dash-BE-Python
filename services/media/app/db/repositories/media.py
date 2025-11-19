"""
미디어 파일 Repository 구현
"""
import asyncio
from typing import Callable, Protocol
from sqlalchemy import text

from services.media.app.db.session import session_scope
from libs.common import now_kst


class MediaRepositoryPort(Protocol):
    """미디어 Repository 인터페이스"""
    
    async def create_media_file(
        self,
        file_id: str,
        file_name: str,
        file_extension: str,
        file_size: int,
        mime_type: str,
        file_path: str,
        source_type: str,
    ) -> int:
        """
        미디어 파일 정보를 DB에 저장합니다.
        
        Args:
            file_id: 파일 고유 ID (UUID)
            file_name: 원본 파일명
            file_extension: 파일 확장자
            file_size: 파일 크기 (바이트)
            mime_type: MIME 타입
            file_path: 파일 저장 경로
            source_type: 파일 소스 타입 ('UPLOAD' 또는 'GENERATE')
            
        Returns:
            생성된 media_id
        """
        ...
    
    async def find_media_file_by_id(self, media_id: int) -> dict | None:
        """
        media_id로 미디어 파일 정보를 조회합니다.
        
        Args:
            media_id: 미디어 파일 식별자
            
        Returns:
            미디어 파일 정보 딕셔너리 또는 None
        """
        ...
    
    async def find_media_file_by_file_id(self, file_id: str) -> dict | None:
        """
        file_id로 미디어 파일 정보를 조회합니다.
        
        Args:
            file_id: 파일 고유 ID (UUID)
            
        Returns:
            미디어 파일 정보 딕셔너리 또는 None
        """
        ...


class _SQLRepositoryBase:
    """SQL Repository 기본 클래스"""
    def __init__(self, session_factory: Callable = session_scope):
        self._session_factory = session_factory

    async def _run_in_thread(self, func: Callable):
        """동기 함수를 비동기로 실행"""
        return await asyncio.to_thread(func)


class SQLAlchemyMediaRepository(_SQLRepositoryBase):
    """SQLAlchemy를 사용한 미디어 Repository 구현"""
    
    async def create_media_file(
        self,
        file_id: str,
        file_name: str,
        file_extension: str,
        file_size: int,
        mime_type: str,
        file_path: str,
        source_type: str,
    ) -> int:
        """미디어 파일 정보를 DB에 저장합니다."""
        def _create():
            with self._session_factory() as session:
                now = now_kst()
                
                query = text("""
                    INSERT INTO media_files (
                        file_id, file_name, file_extension, file_size,
                        mime_type, file_path, source_type, created_at, updated_at
                    )
                    VALUES (
                        :file_id, :file_name, :file_extension, :file_size,
                        :mime_type, :file_path, :source_type, :created_at, :updated_at
                    )
                """)
                
                result = session.execute(
                    query,
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "file_extension": file_extension,
                        "file_size": file_size,
                        "mime_type": mime_type,
                        "file_path": file_path,
                        "source_type": source_type,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                session.commit()
                return result.lastrowid
        
        return await self._run_in_thread(_create)
    
    async def find_media_file_by_id(self, media_id: int) -> dict | None:
        """media_id로 미디어 파일 정보를 조회합니다."""
        def _query():
            with self._session_factory() as session:
                query = text("""
                    SELECT 
                        media_id,
                        file_id,
                        file_name,
                        file_extension,
                        file_size,
                        mime_type,
                        file_path,
                        source_type,
                        DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') as updated_at
                    FROM media_files
                    WHERE media_id = :media_id
                    LIMIT 1
                """)
                
                result = session.execute(
                    query,
                    {"media_id": media_id}
                ).fetchone()
                
                if result is None:
                    return None
                
                return {
                    "media_id": result[0],
                    "file_id": result[1],
                    "file_name": result[2],
                    "file_extension": result[3],
                    "file_size": result[4],
                    "mime_type": result[5],
                    "file_path": result[6],
                    "source_type": result[7],
                    "created_at": result[8],
                    "updated_at": result[9],
                }
        
        return await self._run_in_thread(_query)
    
    async def find_media_file_by_file_id(self, file_id: str) -> dict | None:
        """file_id로 미디어 파일 정보를 조회합니다."""
        def _query():
            with self._session_factory() as session:
                query = text("""
                    SELECT 
                        media_id,
                        file_id,
                        file_name,
                        file_extension,
                        file_size,
                        mime_type,
                        file_path,
                        source_type,
                        DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') as updated_at
                    FROM media_files
                    WHERE file_id = :file_id
                    LIMIT 1
                """)
                
                result = session.execute(
                    query,
                    {"file_id": file_id}
                ).fetchone()
                
                if result is None:
                    return None
                
                return {
                    "media_id": result[0],
                    "file_id": result[1],
                    "file_name": result[2],
                    "file_extension": result[3],
                    "file_size": result[4],
                    "mime_type": result[5],
                    "file_path": result[6],
                    "source_type": result[7],
                    "created_at": result[8],
                    "updated_at": result[9],
                }
        
        return await self._run_in_thread(_query)

