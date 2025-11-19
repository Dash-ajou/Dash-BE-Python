from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.coupon.app.api.v1.router import router
from services.coupon.app.db.connection import settings

app = FastAPI(
    title="Coupon Service (쿠폰 서비스)",
    description="Project Dash Coupon Micro-Service Server"
)

# CORS 설정
# 환경 변수 ALLOWED_ORIGINS가 설정되어 있으면 우선 사용
# 없으면 개발 환경일 때 기본 localhost 리스트 사용
if settings.ALLOWED_ORIGINS:
    # 환경 변수에서 오리진 목록 파싱 (쉼표로 구분)
    allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
elif settings.is_development:
    # 개발 환경: 환경 변수가 없을 때 기본 localhost 포트 허용
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",  # Vite 기본 포트
        "http://localhost:8080",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",  # Coupon 서비스 포트
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002",
    ]
else:
    # 프로덕션 환경: 환경 변수가 없으면 빈 리스트 (모든 오리진 차단)
    allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # 쿠키를 포함한 요청 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, PUT, DELETE 등)
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(router, prefix="/api/v1")

# 서비스가 살아있는지 확인하는 헬스 체크 엔드포인트
@app.get("/")
def read_root():
    return {"service": "Coupon Service", "status": "running"}

