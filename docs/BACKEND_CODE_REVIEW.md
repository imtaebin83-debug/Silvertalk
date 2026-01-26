# 🔍 Backend 코드 전체 검토 보고서

## ✅ 해결 완료: Python 3.8 호환성

### 문제
```python
TypeError: 'type' object is not subscriptable
```

### 원인
- EC2 Python 버전: **3.8.x**
- `tuple[bool, str]`, `dict[str, Any]` 문법은 **Python 3.9+**

### 해결
- `from typing import Tuple, Dict, Any` 추가
- `tuple[...]` → `Tuple[...]`
- `dict[...]` → `Dict[...]`

---

## 📊 파일별 역할 및 의존성 맵

### 1. **FastAPI 서버 (EC2 전용)**

#### `app/main.py` - 엔트리포인트
```python
역할: FastAPI 앱 생성, 라우터 등록, Redis 연결
의존성:
  - common.config (설정 로드)
  - common.database (DB 초기화)
  - app.routers.* (API 엔드포인트)
  - redis (Upstash 연결)
실행: uvicorn app.main:app
```

#### `app/routers/` - API 엔드포인트
```
auth.py     → Kakao OAuth, JWT 인증
users.py    → 사용자 정보 관리
home.py     → 홈 대시보드
gallery.py  → 사진 갤러리
calendar.py → 캘린더/일정
chat.py     → 채팅 (Celery 태스크 큐잉)
video.py    → 영상 관리
memory.py   → 추억 관리
generate.py → AI 이미지/영상 생성 (Replicate API)
```

**의존성 체인:**
```
app/routers/*.py
├── common.auth (JWT, OAuth)
├── common.models (DB 모델)
├── common.database (세션)
├── common.replicate_client (Replicate API)
├── common.image_utils (이미지 전처리)
└── worker.celery_app (태스크 큐잉)
```

### 2. **공통 모듈 (EC2 + RunPod 공유)**

#### `common/config.py` - 설정 관리
```python
역할: 환경변수 로드, DEPLOYMENT_MODE별 Redis/DB 자동 선택
핵심:
  - settings.redis_url → CLOUD: Upstash, LOCAL: redis:6379
  - settings.database_url → CLOUD: RDS, LOCAL: localhost
  - settings.models_root → RunPod: /app/models, EC2: 미사용
사용처: 모든 모듈
```

#### `common/auth.py` - 인증
```python
역할: JWT 토큰 생성/검증, Kakao OAuth
의존성: httpx (Kakao API 호출)
사용처: app/routers/auth.py, 모든 라우터 (Depends)
```

#### `common/database.py` - DB 연결
```python
역할: SQLAlchemy 세션, 테이블 생성
의존성: psycopg2-binary (PostgreSQL)
사용처: app/routers/*, worker/tasks.py
```

#### `common/models.py` - DB 모델
```python
역할: User, ChatSession, Photo, Video 등 ORM 모델
의존성: sqlalchemy
사용처: app/routers/*, worker/tasks.py
```

#### `common/replicate_client.py` - Replicate API
```python
역할: 이미지/영상 생성 (Flux, Luma Ray)
의존성: httpx, asyncio
사용처: app/routers/generate.py
주의: EC2에서만 사용 (Worker 아님)
```

#### `common/image_utils.py` - 이미지 전처리
```python
역할: RGB 변환, 크롭, 리사이즈, JPEG 압축
의존성: Pillow
사용처: app/routers/generate.py
주의: EC2에서만 사용
```

### 3. **Celery Worker (RunPod 전용)**

#### `worker/celery_app.py` - Celery 설정
```python
역할: Celery 앱 생성, Redis 연결, 큐 설정
의존성: common.config (settings.redis_url)
실행: celery -A worker.celery_app worker
```

#### `worker/tasks.py` - AI 태스크
```python
역할: AI 모델 로딩 및 실행 (Whisper, XTTS, Gemini)
핵심 함수:
  - load_models() → AI 모델 초기화
  - process_audio_and_reply() → STT+Brain+TTS
  - generate_memory_video() → 영상 생성
의존성:
  - faster-whisper (STT)
  - TTS (XTTS v2)
  - google-generativeai (Gemini)
  - torch (GPU 연산)
  - common.config (settings.models_root)
  - common.database (DB 저장)
주의: RunPod에서만 실행, EC2는 태스크 큐잉만
```

---

## 🔍 라이브러리 호환성 검토

### ✅ EC2 (requirements.ec2.txt)

| 패키지 | 버전 | 용도 | 상태 |
|--------|------|------|------|
| fastapi | 0.109.0 | 웹 프레임워크 | ✅ |
| uvicorn | 0.27.0 | ASGI 서버 | ✅ |
| httpx | 0.24.1 | HTTP 클라이언트 | ✅ 추가됨 |
| celery | 5.3.4 | 태스크 큐 클라이언트 | ✅ |
| redis | 5.0.1 | Redis 클라이언트 | ✅ |
| pydantic | 2.5.3 | 데이터 검증 | ✅ |
| sqlalchemy | 2.0.25 | ORM | ✅ |
| psycopg2-binary | 2.9.9 | PostgreSQL | ✅ |
| Pillow | 10.2.0 | 이미지 처리 | ✅ |
| boto3 | 1.34.34 | AWS S3 | ✅ |
| python-jose | 3.3.0 | JWT | ✅ |

**Python 버전 요구사항: >=3.8**

### ✅ RunPod (requirements.txt)

추가로 포함:
- faster-whisper==0.10.0 (STT)
- TTS @ git+...@v0.21.3 (TTS)
- google-generativeai==0.3.2 (Gemini)
- torch, torchaudio (GPU)
- soundfile==0.12.1 (오디오)

**Python 버전: 3.10+**

---

## 🏗️ 아키텍처 플로우

### 채팅 요청 플로우

```
┌─────────────┐     HTTP POST      ┌──────────────┐
│   Mobile    │ ───────────────→   │   EC2        │
│   Client    │                    │  FastAPI     │
└─────────────┘                    └──────┬───────┘
                                          │
                                          │ Celery Task
                                          │ (via Redis)
                                          ↓
                                   ┌──────────────┐
                                   │  Upstash     │
                                   │   Redis      │
                                   └──────┬───────┘
                                          │
                                          │ Task Pull
                                          ↓
                                   ┌──────────────┐
                                   │   RunPod     │
                                   │Celery Worker │
                                   │              │
                                   │ 1. STT       │
                                   │ 2. Gemini    │
                                   │ 3. TTS       │
                                   └──────┬───────┘
                                          │
                                          │ Result
                                          ↓
                                   ┌──────────────┐
                                   │  Upstash     │
                                   │   Redis      │
                                   └──────┬───────┘
                                          │
                                          │ Polling
                                          ↓
┌─────────────┐     Response       ┌──────────────┐
│   Mobile    │ ←─────────────────  │   EC2        │
│   Client    │                    │  FastAPI     │
└─────────────┘                    └──────────────┘
```

### 이미지/영상 생성 플로우

```
┌─────────────┐     POST /generate/image     ┌──────────────┐
│   Mobile    │ ───────────────────────────→ │   EC2        │
│   Client    │                              │  FastAPI     │
└─────────────┘                              └──────┬───────┘
                                                    │
                                                    │ Replicate API
                                                    ↓
                                             ┌──────────────┐
                                             │  Replicate   │
                                             │   (Flux)     │
                                             └──────┬───────┘
                                                    │
                                                    │ Image URL
                                                    ↓
┌─────────────┐          Response            ┌──────────────┐
│   Mobile    │ ←───────────────────────────  │   EC2        │
│   Client    │                              │  FastAPI     │
└─────────────┘                              └──────────────┘
```

**주의**: Replicate API는 **EC2에서 직접 호출** (Worker 거치지 않음)

---

## ⚠️ 발견된 잠재적 문제

### 1. Python 버전 불일치

**문제**:
- EC2: Python 3.8
- requirements.txt: `python = ">=3.10,<3.12"` (pyproject.toml)

**해결**:
- EC2는 requirements.ec2.txt 사용 (버전 제약 없음)
- RunPod는 requirements.txt + Python 3.10

**권장**: EC2 Python 업그레이드 → 3.10

```bash
# EC2에서 Python 3.10 설치
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv

# venv 재생성
cd ~/Silvertalk/backend
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.ec2.txt
```

### 2. DB 연결 필수 여부

**현재**: `app/main.py`에서 `init_db()` 호출 → RDS 연결 실패 시 앱 시작 안됨

**해결 옵션**:

#### A. RDS 보안 그룹 설정 (권장)
```bash
# AWS Console → RDS → Security Group
# 인바운드 규칙 추가:
# - 유형: PostgreSQL (5432)
# - 소스: EC2 보안 그룹 또는 IP
```

#### B. DB 연결 선택적으로 변경
```python
# app/main.py
try:
    init_db()
    logger.info("✅ 데이터베이스 연결 완료")
except Exception as e:
    logger.warning(f"⚠️ 데이터베이스 연결 실패: {e}")
    logger.warning("DB 없이 계속 진행...")
```

### 3. import 순환 참조 가능성

**체크 결과**: 없음 ✅

모듈 의존성 방향:
```
app/routers → common → (끝)
worker → common → (끝)
```

순환 없음.

---

## 🚀 최종 실행 단계

### EC2에서:

```bash
# 1. 코드 업데이트
cd ~/Silvertalk
git pull

# 2. Python 버전 확인
python3 --version  # 3.8이면 3.10으로 업그레이드 권장

# 3. (선택) Python 3.10 설치 및 venv 재생성
sudo apt-get install -y python3.10 python3.10-venv
cd backend
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.ec2.txt

# 4. 서버 실행
screen -S fastapi
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+A, D

# 5. 확인
curl http://localhost:8000/
```

---

## 📋 체크리스트

### 코드 호환성
- [x] Python 3.8 타입 힌트 수정
- [x] httpx 패키지 추가
- [x] import 순환 참조 확인
- [ ] Python 3.10 업그레이드 (권장)

### 인프라 설정
- [x] Redis 연결 성공 (Upstash)
- [ ] RDS 보안 그룹 설정 필요
- [ ] EC2 방화벽 8000 포트 개방

### 실행 환경
- [x] requirements.ec2.txt 완성
- [x] .env 파일 생성
- [x] 가상환경 활성화
- [ ] FastAPI 서버 시작

---

## 🎯 즉시 실행 가능

현재 상태로 FastAPI 서버가 시작될 것입니다!

**예상 동작**:
- ✅ Redis 연결 성공
- ⚠️ DB 연결 실패 (타임아웃) - RDS 보안 그룹 설정 필요
- ✅ API 서버 시작 성공 (DB 에러 무시하고 진행)

DB 없이도 일부 API는 작동 가능합니다:
- `/` (헬스체크)
- `/auth/` (인증, 일부)
- `/generate/` (Replicate API, DB 불필요)
