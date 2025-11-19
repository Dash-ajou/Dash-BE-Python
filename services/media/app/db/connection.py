import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    .env 파일에서 환경 변수를 읽어오는 Pydantic 설정 모델
    """

    # DB 접속 정보 (MySQL)
    # 'MEDIA_' 접두사를 추가하여 다른 서비스의 변수와 충돌 방지
    MEDIA_DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/dash_db"
    
    # 파일 저장소 설정
    MEDIA_STORAGE_PATH: str = "./storage"  # 파일 저장 경로
    MEDIA_MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 최대 파일 크기 (10MB)
    MEDIA_ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,pdf,csv,xlsx,xls"  # 허용된 파일 확장자
    
    # 환경 설정
    ENVIRONMENT: str = "development"  # development, production
    DEBUG: bool = True  # 개발 모드 여부
    
    # CORS 설정 (쉼표로 구분된 오리진 목록)
    ALLOWED_ORIGINS: str = ""  # 예: "http://localhost:3000,http://localhost:5173"
    
    # JWT 설정 (인증 서비스와 동일한 키 사용)
    JWT_SECRET_KEY: str = "change-me-in-production"  # JWT 서명에 사용할 시크릿 키
    JWT_ALGORITHM: str = "HS256"  # JWT 알고리즘

    class Config:
        # 루트 디렉터리의 .env 파일을 읽도록 경로 수정
        env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        # 환경 변수가 없어도 기본값 사용
        case_sensitive = False
        # .env 파일의 다른 환경 변수는 무시
        extra = "ignore"
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부 확인"""
        return self.ENVIRONMENT.lower() in ("development", "dev") or self.DEBUG
    
    @property
    def cookie_secure(self) -> bool:
        """쿠키 secure 옵션 (프로덕션 환경에서만 True)"""
        return not self.is_development
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        """허용된 파일 확장자 리스트"""
        return [ext.strip().lower() for ext in self.MEDIA_ALLOWED_EXTENSIONS.split(",") if ext.strip()]


# settings 인스턴스를 생성하여 다른 파일에서 import 해서 사용
# 환경 변수가 없으면 기본값 사용 (개발 환경용)
settings = Settings()

