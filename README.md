# 🎙️ SilverTalk - 반려견 AI와 함께하는 회상 치료 서비스

## 📋 프로젝트 개요

추억이 담긴 갤러리 사진을 매개로 반려견 AI 캐릭터와 대화하며 회상 요법(Reminiscence Therapy) 효과를 제공하고, 대화 내용을 영상으로 제작해 가족 소통을 돕는 서비스입니다.

### 핵심 가치
1. **치매 예방:** 과거의 긍정적 기억을 구체적으로 회상하며 뇌 자극
2. **정서적 고립 해소:** 언제든 말을 걸어주는 반려견 AI를 통한 고독감 완화
3. **세대 간 연결:** 생성된 회상 영상을 통해 자녀 세대와 자연스러운 대화 소재 제공

## 🛠️ 기술 스택

### Backend
- **Web Framework:** FastAPI 0.100+
- **Database:** PostgreSQL 15 + SQLAlchemy
- **Async Worker:** Celery 5.3 + Redis 7.2
- **AI Models:**
  - **STT:** Faster-Whisper (Large-v3) - 한국어 음성 인식
  - **LLM:** Google Gemini 1.5 Flash - 대화 생성
  - **TTS:** Coqui XTTS v2 - 음성 합성 (손주 목소리)
  - **Vision:** Gemini 1.5 Flash - 이미지 분석

### Frontend (Mobile)
- **Framework:** React Native Expo 50.0
- **Navigation:** React Navigation 6.x
- **Audio:** Expo AV
- **Permissions:** Expo Media Library, Calendar, Location

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Database:** PostgreSQL 15 (with pgvector for future embedding support)
- **Cloud:** AWS EC2 (g4dn.xlarge, NVIDIA T4)
- **Storage:** AWS S3 (사진 및 영상 저장)
- **CI/CD:** GitHub Actions

## 🚀 빠른 시작

### 1. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 GEMINI_API_KEY를 설정하세요
```

### 2. Docker Compose 실행
```bash
docker-compose up --build
```

### 3. 서비스 접속
- **API 서버:** http://localhost:8000
- **API 문서:** http://localhost:8000/docs
- **Flower 모니터링:** http://localhost:5555

## 🖥️ 환경별 설정

### 로컬 개발 환경 (Windows/Mac, GPU 없음)
기본 설정이 CPU 모드로 되어 있어 별도 수정 없이 실행 가능합니다.

```yaml
# docker-compose.yml에서 기본 설정
environment:
  - CUDA_VISIBLE_DEVICES=""  # CPU 모드 강제
```

### AWS 프로덕션 환경 (g4dn.xlarge, NVIDIA T4 GPU)
1. `docker-compose.yml` 수정:
   ```yaml
   # CUDA_VISIBLE_DEVICES="" 라인 삭제 또는 주석 처리
   
   # GPU 설정 주석 해제
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

2. NVIDIA Docker 런타임 설치:
   ```bash
   # AWS EC2에서 실행
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

## 📁 프로젝트 구조
```
silvertalk/
├── backend/
│   ├── app/                  # FastAPI 웹 서버
│   │   ├── main.py          # API 진입점
│   │   ├── routers/         # API 라우터 (도메인별)
│   │   │   ├── auth.py      # 인증
│   │   │   ├── users.py     # 사용자 관리
│   │   │   ├── home.py      # 메인 화면
│   │   │   ├── gallery.py   # 갤러리
│   │   │   ├── calendar.py  # 캘린더
│   │   │   ├── chat.py      # 대화 서비스
│   │   │   ├── video.py     # 영상 생성
│   │   │   └── memory.py    # 기억 인사이트
│   │   └── schemas.py       # Pydantic 모델
│   ├── worker/              # Celery AI 작업자
│   │   ├── celery_app.py   # Worker 설정
│   │   └── tasks.py        # AI 로직 (STT, Brain, TTS, 영상 생성)
│   ├── common/              # 공통 모듈
│   │   ├── database.py     # DB 연결 및 세션 관리
│   │   ├── models.py       # SQLAlchemy ORM 모델
│   │   └── config.py       # 설정 관리
│   ├── models/             # AI 모델 가중치 저장소 (Git 제외)
│   ├── Dockerfile.api      # API 컨테이너
│   ├── Dockerfile.worker   # Worker 컨테이너 (GPU 지원)
│   └── requirements.txt
├── mobile-app/             # React Native Expo 앱
│   ├── App.js             # 앱 진입점
│   ├── src/
│   │   └── screens/       # 화면 컴포넌트
│   │       ├── HomeScreen.js          # 메인 (강아지 홈)
│   │       ├── GalleryScreen.js       # 사진 선택
│   │       ├── ChatScreen.js          # 대화 (무전기)
│   │       └── VideoGalleryScreen.js  # 추억 극장
│   ├── package.json
│   └── app.json
├── data/                   # 데이터 저장소 (Git 제외)
├── docker-compose.yml
├── .env.example
├── DOCKER_SETUP.md        # Docker 설정 가이드
├── API_SPEC.md            # API 명세서
├── DB_SCHEMA.md           # DB 스키마 문서
└── README.md
```

## 🔌 API 엔드포인트

### 헬스체크
```bash
GET /
GET /health
```

### 음성 채팅
```bash
POST /api/chat
Content-Type: multipart/form-data

Fields:
- audio_file: 음성 파일 (mp3, wav 등)
- user_id: 사용자 ID
- session_id: 세션 ID (옵션)

Response:
{
  "task_id": "uuid",
  "status": "processing",
  "message": "AI가 음성을 처리 중입니다."
}
```

### 이미지 분석
```bash
POST /api/analyze-image
Content-Type: multipart/form-data

Fields:
- image: 이미지 파일
- user_id: 사용자 ID
- prompt: 분석 요청 (옵션)
```

### 태스크 결과 조회
```bash
GET /api/task/{task_id}

Response:
{
  "task_id": "uuid",
  "status": "success",
  "result": {
    "user_text": "인식된 텍스트",
    "ai_reply": "AI 답변",
    "audio_url": "/app/data/reply.wav"
  }
}
```

## 🧪 테스트

### cURL 예제
```bash
# 헬스체크
curl http://localhost:8000/health

# 텍스트 채팅
curl -X POST http://localhost:8000/api/text-chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "text": "어렸을 때 고향 이야기를 들려주세요"
  }'

# 태스크 결과 조회
curl http://localhost:8000/api/task/{task_id}
```

## 🐛 트러블슈팅

### GPU 관련 에러
```bash
# 로컬 환경에서 GPU 에러 발생 시
# docker-compose.yml에서 다음 확인:
environment:
  - CUDA_VISIBLE_DEVICES=""  # 이 라인이 있는지 확인

# AWS에서 GPU 인식 안 됨
docker exec -it silvertalk-worker nvidia-smi  # GPU 확인
```

### 모델 다운로드 실패
```bash
# Worker 로그 확인
docker logs silvertalk-worker

# 수동 다운로드 (컨테이너 내부)
docker exec -it silvertalk-worker bash
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3')"
```

## 📊 모니터링

### Flower 대시보드
Celery 작업 상태를 실시간으로 모니터링할 수 있습니다.
```
http://localhost:5555
```

### Celery 상태 확인
```bash
# API로 확인
curl http://localhost:8000/api/debug/celery-status

# CLI로 확인
docker exec -it silvertalk-worker celery -A worker.celery_app inspect active
```

## 🤝 팀 협업

### Git 브랜치 전략
- `main`: 프로덕션 배포용
- `develop`: 개발 통합
- `feature/*`: 기능 개발

### 개발 환경 동기화
```bash
# User A (Windows, No GPU)
git pull
docker-compose up --build

# User B (Mac, Apple Silicon)
git pull
docker-compose up --build
# 자동으로 CPU 모드로 실행됨
```

## 📝 TODO
- [ ] PostgreSQL 데이터베이스 통합
- [ ] 사용자 세션 관리
- [ ] 대화 히스토리 저장
- [ ] AWS S3 미디어 저장
- [ ] React Native 모바일 앱 연결
- [ ] CI/CD 파이프라인 구축

## 📄 라이선스
MIT License

## 👥 팀
- User A: Backend & DevOps (Windows)
- User B: Backend & AI (Mac)
