# 🐳 Docker 빠른 테스트 가이드

## 📋 목적

팀원이 로컬 환경에서 빠르게 전체 스택을 테스트할 수 있도록 Docker 환경 제공

---

## 🚀 빠른 시작

### 1. **환경변수 설정**

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env
GEMINI_API_KEY=your_actual_key
REPLICATE_API_TOKEN=your_actual_token
JWT_SECRET_KEY=test_secret_key_for_development
```

### 2. **Docker Compose 실행**

```bash
# 전체 스택 시작 (API + Worker + Redis)
docker-compose -f docker-compose.test.yml up --build

# 백그라운드 실행
docker-compose -f docker-compose.test.yml up -d --build

# 로그 확인
docker-compose -f docker-compose.test.yml logs -f

# 중단
docker-compose -f docker-compose.test.yml down
```

### 3. **API 테스트**

```bash
# 헬스체크
curl http://localhost:8000/

# Swagger 문서
http://localhost:8000/docs
```

### 4. **Celery 태스크 테스트**

```bash
# Docker 내부에서 실행
docker-compose -f docker-compose.test.yml exec api python << 'EOF'
from worker.celery_app import celery_app

task = celery_app.send_task(
    'worker.tasks.generate_reply_from_text',
    kwargs={'user_text': '안녕하세요', 'user_id': 'test_user'}
)
print(f"Task ID: {task.id}")
EOF

# Worker 로그 확인
docker-compose -f docker-compose.test.yml logs -f worker
```

---

## 🏗️ 개별 Dockerfile 빌드

### **FastAPI 서버만** (EC2 환경 시뮬레이션)

```bash
cd backend

# 빌드
docker build -f Dockerfile.api -t silvertalk-api .

# 실행 (외부 Redis 필요)
docker run -p 8000:8000 \
  -e DEPLOYMENT_MODE=CLOUD \
  -e REDIS_URL=rediss://your-redis-url \
  -e GEMINI_API_KEY=your_key \
  silvertalk-api
```

### **Celery Worker만** (RunPod 환경 시뮬레이션)

```bash
cd backend

# 빌드
docker build -f Dockerfile.runpod -t silvertalk-worker .

# 실행 (외부 Redis 필요)
docker run \
  -e DEPLOYMENT_MODE=CLOUD \
  -e REDIS_URL=rediss://your-redis-url \
  -e GEMINI_API_KEY=your_key \
  -e COQUI_TOS_AGREED=1 \
  silvertalk-worker
```

---

## 📊 서비스 구성

| 서비스 | 포트 | 용도 |
|--------|------|------|
| `api` | 8000 | FastAPI 웹 서버 |
| `worker` | - | Celery Worker (AI 모델) |
| `redis` | 6379 | 태스크 큐 |

---

## 🔍 디버깅

### **컨테이너 내부 접속**

```bash
# API 컨테이너
docker-compose -f docker-compose.test.yml exec api bash

# Worker 컨테이너
docker-compose -f docker-compose.test.yml exec worker bash
```

### **로그 확인**

```bash
# 전체 로그
docker-compose -f docker-compose.test.yml logs

# API만
docker-compose -f docker-compose.test.yml logs api

# Worker만
docker-compose -f docker-compose.test.yml logs worker

# 실시간 로그
docker-compose -f docker-compose.test.yml logs -f worker
```

### **Redis 확인**

```bash
# Redis CLI 접속
docker-compose -f docker-compose.test.yml exec redis redis-cli

# 키 확인
redis> KEYS *

# Celery 큐 확인
redis> LLEN celery
```

---

## ⚠️ 주의사항

### 1. **AI 모델 다운로드**

Worker 첫 실행 시 모델 다운로드로 **5-10분** 소요:
- Whisper large-v3: ~3GB
- XTTS v2: ~2GB
- Gemini: API 호출 (다운로드 없음)

볼륨 마운트로 재사용:
```bash
# 모델이 backend/models에 저장됨
ls -lh backend/models/
```

### 2. **메모리 요구사항**

최소 시스템 사양:
- RAM: 8GB 이상 (AI 모델 로드 시)
- Disk: 10GB 이상 (모델 저장)

Docker Desktop 메모리 설정:
```
Settings → Resources → Memory: 6GB 이상
```

### 3. **GPU 지원 (선택)**

로컬에서 GPU 사용 시 (NVIDIA만):

```bash
# nvidia-docker 설치 후
docker-compose -f docker-compose.test.yml up --build \
  --gpus all
```

Worker 컨테이너에 GPU 할당:
```yaml
# docker-compose.test.yml
worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

---

## 🆚 로컬 vs 프로덕션

| 구분 | 로컬 (Docker) | 프로덕션 (EC2/RunPod) |
|------|--------------|----------------------|
| Redis | Docker 컨테이너 | Upstash (Seoul) |
| DB | 로컬 PostgreSQL | RDS (Seoul) |
| AI 모델 | CPU 모드 (느림) | GPU 모드 (빠름) |
| .env | 프로젝트 루트 | `backend/.env` |

---

## 🔄 개발 워크플로우

### 1. **코드 수정 시**

```bash
# API 코드 수정 → 자동 리로드 (--reload)
# 변경사항 즉시 반영

# Worker 코드 수정 → 재시작 필요
docker-compose -f docker-compose.test.yml restart worker
```

### 2. **의존성 추가 시**

```bash
# requirements.txt 수정 후
docker-compose -f docker-compose.test.yml up --build
```

### 3. **전체 리셋**

```bash
# 컨테이너, 볼륨, 네트워크 모두 삭제
docker-compose -f docker-compose.test.yml down -v

# 이미지 재빌드
docker-compose -f docker-compose.test.yml up --build
```

---

## 📚 참고 명령어

```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.test.yml ps

# 리소스 사용량
docker stats

# 디스크 사용량
docker system df

# 사용하지 않는 이미지 정리
docker system prune -a
```

---

## 🆘 문제 해결

### **Worker가 시작 안될 때**

```bash
# 로그 확인
docker-compose -f docker-compose.test.yml logs worker

# 수동 실행 (디버그)
docker-compose -f docker-compose.test.yml run --rm worker bash
celery -A worker.celery_app worker --loglevel=debug
```

### **Redis 연결 실패**

```bash
# Redis 상태 확인
docker-compose -f docker-compose.test.yml ps redis

# Redis 재시작
docker-compose -f docker-compose.test.yml restart redis
```

### **포트 충돌**

```bash
# 포트 변경 (docker-compose.test.yml 수정)
services:
  api:
    ports:
      - "8001:8000"  # 8001로 변경
```

---

**마지막 업데이트**: 2026-01-26  
**문의**: 임태완
