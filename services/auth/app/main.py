from fastapi import FastAPI
from app.api.v1.router import router

app = FastAPI(
    title="Auth Service (인증 서비스)",
    description="Project Dash Auth Micro-Service Server"
)

app.include_router(router)

# 서비스가 살아있는지 확인하는 헬스 체크 엔드포인트
@app.get("/")
def read_root():
    return {"service": "Auth Service", "status": "running"}