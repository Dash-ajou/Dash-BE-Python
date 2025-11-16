#!/bin/bash

# --- 스크립트 설정 ---
# set -e : 오류 발생 시 스크립트를 즉시 중단합니다.
set -e

# 1. 루트 디렉터리 정의
ROOT_DIR="project-dash"

# 2. 생성할 마이크로서비스 목록
# 필요에 따라 이 배열에 서비스를 추가하거나 제거하세요.
SERVICES=("auth" "coupon" "partner" "vendor")

# 3. 생성할 공통 라이브러리 목록
LIBS=("common" "core_schemas")

# --- 스크립트 실행 ---

echo "🚀 Project Dash Monorepo 생성을 시작합니다..."

# 1. 루트 디렉터리 및 기본 파일 생성
mkdir -p $ROOT_DIR
cd $ROOT_DIR

touch .gitignore
touch docker-compose.yml
touch README.md

echo "✅ 루트 디렉터리 및 기본 파일 생성 완료. ($ROOT_DIR/)"

# 2. 개별 마이크로서비스 생성
mkdir -p services

for service in "${SERVICES[@]}"; do
    SERVICE_PATH="services/$service"

    # 2-1. 서비스 기본 디렉터리 생성
    # -p 옵션으로 모든 하위 디렉터리 자동 생성
    mkdir -p $SERVICE_PATH/app/api/v1
    mkdir -p $SERVICE_PATH/app/domain
    mkdir -p $SERVICE_PATH/app/core
    mkdir -p $SERVICE_PATH/app/db
    mkdir -p $SERVICE_PATH/tests

    # 2-2. 파이썬 모듈화를 위한 __init__.py 파일 생성
    touch $SERVICE_PATH/app/__init__.py
    touch $SERVICE_PATH/app/api/__init__.py
    touch $SERVICE_PATH/app/api/v1/__init__.py
    touch $SERVICE_PATH/app/domain/__init__.py
    touch $SERVICE_PATH/app/core/__init__.py
    touch $SERVICE_PATH/app/db/__init__.py
    touch $SERVICE_PATH/tests/__init__.py

    # 2-3. 서비스별 기본 파일 생성
    touch $SERVICE_PATH/app/main.py
    touch $SERVICE_PATH/app/api/v1/router.py
    touch $SERVICE_PATH/.env.example
    touch $SERVICE_PATH/Dockerfile
    touch $SERVICE_PATH/requirements.txt

    # 2-4. 도메인 핵심 파일 생성 (규칙: {service_name}_*.py)
    touch $SERVICE_PATH/app/domain/${service}_router.py
    touch $SERVICE_PATH/app/domain/${service}_service.py
    touch $SERVICE_PATH/app/domain/${service}_schemas.py

    echo "  -  servizio '$service' 생성 완료."
done

echo "✅ 모든 마이크로서비스 디렉터리 생성 완료."

# 3. 공통 라이브러리(libs) 생성
mkdir -p libs
touch libs/__init__.py

for lib in "${LIBS[@]}"; do
    LIB_PATH="libs/$lib"
    mkdir -p $LIB_PATH
    touch $LIB_PATH/__init__.py
    touch $LIB_PATH/setup.py # pip install -e 용
    echo "  - lib '$lib' 생성 완료."
done

echo "✅ 공통 라이브러리 디렉터리 생성 완료."

# 4. 완료
echo "🎉 'Project Dash' Monorepo 구조 생성이 완료되었습니다!"
echo "cd $ROOT_DIR 명령어로 이동하여 개발을 시작하세요."
