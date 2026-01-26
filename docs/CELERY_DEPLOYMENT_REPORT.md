# 🎯 SilverTalk EC2 + RunPod 분산 처리 구축 완료 보고서

## 📋 작업 완료 내역

### ✅ Step 1: 코드 감사 (Code Audit)
**수정 완료:**
1. `app/routers/chat.py` (Line 16-20)
   - ❌ Before: 하드코딩된 Redis URL (`redis://redis:6379/0`)
   - ✅ After: `settings.redis_url` 동적 설정 (CLOUD 모드에서 Upstash 자동 선택)

2. `worker/celery_app.py` (Line 12)
   - ❌ Before: `os.getenv("REDIS_URL")` 직접 사용
   - ✅ After: `settings.redis_url` property 사용

**통과 항목:**
- ✅ FastAPI async/await 구조 (Celery와 호환)
- ✅ 카카오 OAuth 로직 독립성
- ✅ 이미지 처리 로직 (gallery.py, generate.py는 Celery 불필요)
- ✅ DB 모델링 완성도

---

### ✅ Step 2: 환경 변수 체크리스트
**확인 완료:**
- ✅ Upstash Redis URL (rediss:// TLS 활성화)
- ✅ AWS RDS PostgreSQL
- ✅ AWS S3 (silvertalkbucket, Tokyo region)
- ✅ RunPod Pod ID & SSH Key
- ✅ Gemini API Key
- ✅ 환경 변수 파일 (`.env.ec2`, `.env.runpod`)

---

### ✅ Step 3: 코드 구현
**생성된 파일:**
1. **`app/celery_config.py`** (EC2 Producer 전용)
   - AI 라이브러리 불필요
   - `send_task()` 전용 최소 설정
   - 45 lines

2. **`worker/s3_utils.py`** (RunPod Worker용)
   - S3 파일 다운로드/업로드
   - 임시 파일 자동 정리
   - 100 lines

3. **`worker/worker_tasks_example.py`** (Task 예시)
   - `process_audio` Task 전체 파이프라인
   - S3 기반 파일 처리 Flow
   - STT → LLM → TTS 통합
   - 200 lines (주석 포함)

**수정된 파일:**
1. **`app/routers/chat.py`**
   - Celery 앱 설정을 `settings.redis_url` 사용으로 변경
   
2. **`worker/celery_app.py`**
   - `common.config.settings` import 추가
   - 동적 Redis URL 설정

---

### ✅ Step 4: 테스트 코드
**생성된 파일:**
1. **`backend/test_connection.py`** (연결 테스트)
   - Redis ping 테스트
   - Celery Task 전송 테스트
   - RunPod Worker 응답 확인
   - 250 lines

**실행 방법:**
```bash
# EC2 또는 로컬에서
cd backend
python test_connection.py
```

**예상 출력:**
```
Step 0: 환경 설정 확인
DEPLOYMENT_MODE: CLOUD
Redis URL: rediss://default:xxxxx@new-grizzly-7377...
✅ CLOUD 모드: Upstash Redis 사용

Step 1: Redis 연결 테스트
✅ Redis 연결 성공
✅ Redis 읽기/쓰기 성공

Step 2: Celery Producer 테스트
✅ Celery Producer 앱 생성 완료
📤 Task 전송 중: worker.tasks.process_audio
✅ Task 전송 완료!
   Task ID: abc123-def456-...
⏳ RunPod Worker 응답 대기 중...
✅ Task 성공!

🎉 모든 테스트 통과!
```

---

## 🚀 다음 단계 (배포)

### 1️⃣ RunPod Worker 시작
```bash
# RunPod 웹 터미널에서
cd /workspace/Silvertalk/backend

# AI 라이브러리 설치 (이미 완료했다면 생략)
pip install -r requirements.txt

# Celery Worker 시작
celery -A worker.celery_app worker --loglevel=info --concurrency=2

# 백그라운드 실행 (screen 사용)
screen -S celery
celery -A worker.celery_app worker --loglevel=info --concurrency=2
# Ctrl+A, D로 세션 분리
```

**Worker 로그 확인:**
```
[INFO] Connected to rediss://default:xxxxx@new-grizzly-7377...
[INFO] celery@territorial_amaranth_mastodon ready.
[INFO] 🚀 GPU 감지: NVIDIA GeForce RTX 3090
[INFO] ✅ Whisper 모델 로딩 완료
[INFO] ✅ XTTS 모델 로딩 완료
```

### 2️⃣ EC2 FastAPI 서버 시작
```bash
# EC2에서
cd backend
docker-compose -f docker-compose.production.yml up -d

# 또는 로컬 테스트
docker-compose up
```

### 3️⃣ 연결 테스트
```bash
# EC2 또는 로컬에서
python test_connection.py
```

### 4️⃣ FastAPI 엔드포인트에서 Task 전송 (예시)
```python
# app/routers/chat.py에서
from app.celery_config import celery_producer

@router.post("/process-voice")
async def process_voice(
    audio_file: UploadFile,
    user_id: str,
    session_id: str
):
    # 1. 음성 파일을 S3에 업로드 (FastAPI에서)
    audio_s3_key = f"audio/{user_id}/{session_id}/input.wav"
    # ... S3 업로드 로직 ...
    
    # 2. Celery Task 전송
    task = celery_producer.send_task(
        "worker.tasks.process_audio",
        kwargs={
            "audio_s3_key": audio_s3_key,
            "user_id": user_id,
            "session_id": session_id
        },
        queue="ai_tasks"
    )
    
    # 3. Task ID 반환 (클라이언트는 이를 사용해 결과 조회)
    return {
        "task_id": task.id,
        "status": "processing"
    }
```

---

## 📊 아키텍처 최종 구성

```
[모바일 앱]
    ↓ (HTTP/REST)
[EC2 FastAPI]
    ├─ 카카오 OAuth
    ├─ DB 접근 (RDS PostgreSQL)
    ├─ S3 업로드
    └─ Celery Task 전송
         ↓ (Upstash Redis)
    [RunPod Worker]
        ├─ S3 파일 다운로드
        ├─ Whisper STT (GPU)
        ├─ Gemini LLM
        ├─ XTTS TTS (GPU)
        └─ S3 업로드 (결과)
```

---

## ⚠️ 주의사항

### EC2에서 절대 설치하지 말 것
- ❌ `torch`
- ❌ `TTS`
- ❌ `faster-whisper`
- ❌ `av` (PyAV)

**이유:** GPU 없는 EC2에서 불필요하며, Docker 이미지 크기만 증가

### RunPod Worker 메모리 관리
- RTX 3090 24GB 기준:
  - Whisper Large-v3: ~3GB
  - XTTS v2: ~1.8GB
  - 여유 공간: ~19GB
- **권장:** `--concurrency=2` (동시 2개 Task)
- **안정성 우선:** `--concurrency=1`

### 환경 변수 보안
- ✅ `.env`, `.env.ec2`, `.env.runpod`는 `.gitignore`에 등록됨
- ✅ 실제 값은 절대 Git에 커밋하지 않음
- ✅ 예시 파일 (`.env.example`, `.env.production.example`)만 커밋

---

## 🎉 완료 확인

- [x] Redis 연결 동적 설정 (`settings.redis_url`)
- [x] EC2 Producer 코드 (`app/celery_config.py`)
- [x] RunPod Worker S3 유틸리티 (`worker/s3_utils.py`)
- [x] Task 예시 (`worker/worker_tasks_example.py`)
- [x] 연결 테스트 스크립트 (`test_connection.py`)
- [x] 기존 코드 호환성 확인 (OAuth, 이미지 처리 보존)

**Status: 배포 준비 완료 ✅**

---

## 📞 문제 해결

### Redis 연결 실패
```bash
# .env 파일 확인
cat .env | grep UPSTASH_REDIS_URL

# Upstash Dashboard에서 Redis 상태 확인
# 포트 6379, TLS 활성화(rediss://) 확인
```

### RunPod Worker 응답 없음
```bash
# Worker 로그 확인
screen -r celery

# GPU 사용률 확인
nvidia-smi

# Celery 재시작
screen -r celery
Ctrl+C
celery -A worker.celery_app worker --loglevel=info --concurrency=2
```

### Task 전송되지만 처리 안 됨
```bash
# Flower 대시보드 확인
http://your-ec2-ip:5555

# Task 큐 확인
# Queue: ai_tasks
# Worker: territorial_amaranth_mastodon
```

---

**작성자:** Senior Backend Engineer  
**작성일:** 2026년 1월 24일  
**프로젝트:** SilverTalk (실버톡) - 노인용 AI 챗봇 서비스
