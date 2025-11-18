# 배포 가이드 (Deployment Guide)

이 문서는 Dash-BE-New 프로젝트를 프로덕션 환경에 배포하는 방법을 설명합니다.

## 목차

1. [배포 옵션](#배포-옵션)
2. [Kubernetes 배포](#kubernetes-배포)
3. [Docker Compose 배포](#docker-compose-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [데이터베이스 초기화](#데이터베이스-초기화)
6. [모니터링 및 로깅](#모니터링-및-로깅)

---

## 배포 옵션

이 프로젝트는 다음 두 가지 방법으로 배포할 수 있습니다:

1. **Kubernetes (권장)**: 프로덕션 환경, 스케일링, 고가용성 필요 시
2. **Docker Compose**: 소규모 배포, 단일 서버 환경

---

## Kubernetes 배포

### 사전 요구사항

- Kubernetes 클러스터 (v1.20 이상)
- `kubectl` CLI 도구
- Docker 이미지 레지스트리 접근 권한
- `kubectl` 클러스터 접근 권한

### 1단계: Docker 이미지 빌드 및 푸시

```bash
# 프로젝트 루트에서 실행
# Docker 이미지 빌드
docker build -f services/auth/Dockerfile -t your-registry/dash-auth:latest .

# 이미지 레지스트리에 푸시
docker push your-registry/dash-auth:latest

# 태그 버전 관리 (선택사항)
docker tag your-registry/dash-auth:latest your-registry/dash-auth:v1.0.0
docker push your-registry/dash-auth:v1.0.0
```

### 2단계: Kubernetes 네임스페이스 생성

```bash
kubectl apply -f k8s/namespace.yaml
```

### 3단계: Secret 생성

**MySQL Secret 생성:**

```bash
kubectl create secret generic mysql-secrets \
  --from-literal=root-password='your-secure-root-password' \
  --from-literal=username='dash_user' \
  --from-literal=password='your-secure-user-password' \
  --namespace=dash
```

**Auth Service Secret 생성 (필요시):**

```bash
kubectl create secret generic auth-secrets \
  --from-literal=database-password='your-database-password' \
  --from-literal=jwt-secret='your-jwt-secret-key' \
  --namespace=dash
```

### 4단계: ConfigMap 생성

```bash
# Auth Service ConfigMap
kubectl apply -f k8s/auth/configmap.yaml

# DDL 스크립트를 ConfigMap으로 생성
kubectl create configmap db-ddl \
  --from-file=ddl.sql=libs/schemas/ddl.sql \
  --namespace=dash
```

### 5단계: MySQL 배포

```bash
# MySQL StatefulSet 및 Service 배포
kubectl apply -f k8s/mysql/service.yaml
kubectl apply -f k8s/mysql/deployment.yaml

# MySQL이 준비될 때까지 대기
kubectl wait --for=condition=ready pod -l app=mysql -n dash --timeout=300s
```

### 6단계: 데이터베이스 초기화

```bash
# DDL ConfigMap이 생성되어 있어야 함
kubectl apply -f k8s/db-ddl-configmap.yaml  # 또는 위의 kubectl create 명령 사용

# 데이터베이스 초기화 Job 실행
kubectl apply -f k8s/db-init-job.yaml

# Job 완료 확인
kubectl wait --for=condition=complete job/db-init -n dash --timeout=300s
```

### 7단계: Auth Service 배포

```bash
# Deployment 및 Service 배포
kubectl apply -f k8s/auth/deployment.yaml
kubectl apply -f k8s/auth/service.yaml

# 배포 상태 확인
kubectl get pods -n dash -l app=auth-service
kubectl get svc -n dash
```

### 8단계: 배포 확인

```bash
# Pod 상태 확인
kubectl get pods -n dash

# 로그 확인
kubectl logs -f deployment/auth-service -n dash

# 서비스 엔드포인트 확인
kubectl get endpoints auth-service -n dash

# 포트 포워딩으로 로컬에서 테스트 (선택사항)
kubectl port-forward svc/auth-service 8000:80 -n dash
# 브라우저에서 http://localhost:8000/docs 접속
```

### 9단계: Ingress 설정 (선택사항)

외부에서 접근하려면 Ingress를 설정하세요:

```yaml
# k8s/auth/ingress.yaml 예시
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auth-ingress
  namespace: dash
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: auth-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: auth-service
            port:
              number: 80
```

```bash
kubectl apply -f k8s/auth/ingress.yaml
```

---

## Docker Compose 배포

### 사전 요구사항

- Docker 및 Docker Compose 설치
- 프로젝트 루트에 `.env.production` 파일 생성

### 1단계: 환경 변수 설정

```bash
# .env.production.example을 복사하여 수정
cp .env.production.example .env.production
# .env.production 파일을 편집하여 실제 값으로 변경
```

### 2단계: Secret 파일 생성

```bash
# secrets 디렉토리 생성
mkdir -p secrets

# MySQL 비밀번호 파일 생성
echo -n 'your-secure-root-password' > secrets/mysql_root_password.txt
echo -n 'dash_user' > secrets/mysql_user.txt
echo -n 'your-secure-user-password' > secrets/mysql_password.txt

# 파일 권한 설정 (보안)
chmod 600 secrets/*.txt
```

### 3단계: 서비스 시작

```bash
# 프로덕션 모드로 시작
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f auth

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps
```

### 4단계: 데이터베이스 초기화

DDL 스크립트가 자동으로 실행되거나, 수동으로 실행:

```bash
# MySQL 컨테이너에 접속
docker-compose -f docker-compose.prod.yml exec db mysql -u root -p

# 또는 DDL 스크립트 직접 실행
docker-compose -f docker-compose.prod.yml exec db mysql -u root -p dash_db < libs/schemas/ddl.sql
```

---

## 환경 변수 설정

### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `AUTH_DATABASE_URL` | MySQL 데이터베이스 연결 URL | `mysql+pymysql://user:pass@host:3306/dash_db` |
| `ENVIRONMENT` | 실행 환경 | `production` |
| `DEBUG` | 디버그 모드 | `false` |

### 환경별 데이터베이스 URL

- **Kubernetes**: `mysql+pymysql://root:password@mysql-service:3306/dash_db`
- **Docker Compose**: `mysql+pymysql://root:password@db:3306/dash_db`
- **로컬 개발**: `mysql+pymysql://root:password@localhost:3306/dash_db`

---

## 데이터베이스 초기화

### 자동 초기화

- **Docker Compose**: `docker-entrypoint-initdb.d` 디렉토리에 DDL 스크립트가 자동 실행됩니다.
- **Kubernetes**: `db-init-job.yaml`을 사용하여 초기화 Job을 실행합니다.

### 수동 초기화

```bash
# MySQL에 접속
mysql -h <host> -u root -p

# 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS dash_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dash_db;

# DDL 스크립트 실행
source libs/schemas/ddl.sql;
# 또는
mysql -h <host> -u root -p dash_db < libs/schemas/ddl.sql
```

---

## 모니터링 및 로깅

### Kubernetes

```bash
# Pod 로그 확인
kubectl logs -f deployment/auth-service -n dash

# 리소스 사용량 확인
kubectl top pods -n dash

# 이벤트 확인
kubectl get events -n dash --sort-by='.lastTimestamp'
```

### Docker Compose

```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 리소스 사용량 확인
docker stats
```

### 헬스 체크

애플리케이션은 다음 엔드포인트에서 헬스 체크를 제공합니다:

- `GET /`: 기본 헬스 체크
- `GET /docs`: API 문서 (Swagger UI)

---

## 트러블슈팅

### 일반적인 문제

1. **데이터베이스 연결 실패**
   - 데이터베이스 서비스가 실행 중인지 확인
   - 연결 URL과 인증 정보 확인
   - 네트워크 정책 확인 (Kubernetes)

2. **Pod가 시작되지 않음**
   - 이미지 레지스트리 접근 권한 확인
   - 리소스 제한 확인
   - 로그 확인: `kubectl logs <pod-name> -n dash`

3. **데이터베이스 초기화 실패**
   - DDL 스크립트 문법 확인
   - 데이터베이스 권한 확인
   - Job 로그 확인: `kubectl logs job/db-init -n dash`

### 유용한 명령어

```bash
# Kubernetes
kubectl describe pod <pod-name> -n dash
kubectl exec -it <pod-name> -n dash -- /bin/bash
kubectl get all -n dash

# Docker Compose
docker-compose -f docker-compose.prod.yml exec auth /bin/bash
docker-compose -f docker-compose.prod.yml exec db mysql -u root -p
```

---

## 보안 권장사항

1. **Secret 관리**
   - 민감한 정보는 Kubernetes Secret 또는 Docker Secret으로 관리
   - Git에 Secret 파일 커밋 금지
   - 정기적으로 비밀번호 변경

2. **네트워크 보안**
   - 프로덕션 환경에서는 데이터베이스 포트를 외부에 노출하지 않음
   - Ingress를 통한 HTTPS 사용
   - 네트워크 정책으로 트래픽 제한

3. **이미지 보안**
   - 정기적으로 베이스 이미지 업데이트
   - 취약점 스캔 실행
   - 최신 보안 패치 적용

---

## 롤백 방법

### Kubernetes

```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/auth-service -n dash

# 특정 리비전으로 롤백
kubectl rollout undo deployment/auth-service --to-revision=2 -n dash

# 롤백 상태 확인
kubectl rollout status deployment/auth-service -n dash
```

### Docker Compose

```bash
# 이전 이미지 태그로 변경 후 재시작
docker-compose -f docker-compose.prod.yml down
# docker-compose.prod.yml에서 이미지 태그 변경
docker-compose -f docker-compose.prod.yml up -d
```

---

## 추가 리소스

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)

