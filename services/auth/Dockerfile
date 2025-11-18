# --- [Stage 1: Build] ---
# 목적: Python 의존성을 설치하는 빌드 전용 스테이지
# 베이스 이미지: python:3.10-slim (경량화된 Python 3.10)
# AS builder: 이 스테이지의 이름을 'builder'로 지정하여 나중에 참조
FROM python:3.10-slim AS builder

# 작업 디렉터리 설정 (가상환경 설치 경로)
WORKDIR /opt/venv

# 가상환경 생성 (Docker 이미지 내에서도 격리된 환경 사용)
RUN python -m venv .
# 이 가상환경의 bin을 PATH에 추가
ENV PATH="/opt/venv/bin:$PATH"

# pip 자체와 wheel을 업그레이드 (패키지 설치 속도 향상)
RUN pip install --upgrade pip wheel

# --- 1-1. Monorepo 공통 라이브러리 설치 (Cache Layer 1) ---
# 목적: 모든 서비스가 공유하는 'libs/'를 먼저 설치합니다.
#      'libs'가 변경되지 않으면 이 레이어가 캐시되어 빌드 속도가 빨라집니다.
WORKDIR /tmp/libs
# 루트 컨텍스트에서 'libs/' 디렉터리들을 복사
COPY libs/schemas /tmp/libs/schemas
COPY libs/common /tmp/libs/common

# 복사한 공통 라이브러리를 가상환경에 설치 (setup.py가 있다고 가정)
RUN pip install /tmp/libs/schemas /tmp/libs/common

# --- 1-2. Auth 서비스 전용 의존성 설치 (Cache Layer 2) ---
# 목적: 'auth' 서비스의 'requirements.txt'를 설치합니다.
#      'requirements.txt'가 변경되지 않으면 이 레이어가 캐시됩니다.
COPY services/auth/requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt


# --- [Stage 2: Final] ---
# 목적: 실제 앱을 실행할 최종 경량 이미지 생성
FROM python:3.10-slim

# --- 2-1. 보안 설정 (Non-Root User) ---
# 목적: 보안을 위해 root가 아닌 'appuser'라는 이름의 유저와 그룹 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 애플리케이션 작업 디렉터리 설정
WORKDIR /home/appuser

# --- 2-2. 빌드 결과물 복사 ---
# 'builder' 스테이지(/opt/venv)에서 설치한 가상환경 전체를 복사
# --chown: 파일 소유자를 'appuser'로 지정
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Monorepo 루트 구조를 유지하기 위해 필요한 디렉터리들을 복사
# libs/ 디렉터리: 전역 스키마 및 공통 라이브러리
COPY --chown=appuser:appuser libs /home/appuser/libs
# services/ 디렉터리: 서비스 코드 (import 경로를 위해 필요)
COPY --chown=appuser:appuser services /home/appuser/services

# --- 2-3. 실행 설정 ---
# 실행 유저를 'appuser'로 변경
USER appuser

# 생성한 가상환경을 PATH에 추가
ENV PATH="/opt/venv/bin:$PATH"
# PYTHONPATH를 루트로 설정하여 libs와 services를 import 가능하게 함
ENV PYTHONPATH="/home/appuser"

# 컨테이너가 노출할 포트 (Gunicorn에서 사용할 포트와 일치)
EXPOSE 8000

# --- 2-4. 컨테이너 실행 명령어 (Production용) ---
# Gunicorn을 사용하여 FastAPI 앱을 실행합니다.
# -k uvicorn.workers.UvicornWorker: Uvicorn 워커 사용
# -w 4: 4개의 워커 프로세스 사용 (서버 환경에 맞게 조절)
# -b 0.0.0.0:8000: 모든 인터페이스의 8000 포트에서 수신
# services.auth.app.main:app: 실행할 FastAPI 앱 (루트 구조를 유지한 경로)
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "services.auth.app.main:app"]