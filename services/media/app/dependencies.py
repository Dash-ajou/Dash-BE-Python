from functools import lru_cache

from services.media.app.core.MediaService import MediaService
from services.media.app.db.repositories.media import SQLAlchemyMediaRepository


@lru_cache
def get_media_repository() -> SQLAlchemyMediaRepository:
    """미디어 Repository 의존성"""
    return SQLAlchemyMediaRepository()


@lru_cache
def get_media_service() -> MediaService:
    """미디어 서비스 의존성"""
    return MediaService(media_repository=get_media_repository())

