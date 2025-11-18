from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    .env 파일에서 환경 변수를 읽어오는 Pydantic 설정 모델
    """
    
    # DB 접속 정보 (MySQL)
    # 'AUTH_' 접두사를 추가하여 다른 서비스의 변수와 충돌 방지
    AUTH_DATABASE_URL: str

    class Config:
        env_file = "../../../../.env" # 루트 디렉터리의 .env 파일을 읽도록 경로 수정
        env_file_encoding = 'utf-8'

# settings 인스턴스를 생성하여 다른 파일에서 import 해서 사용
settings = Settings()