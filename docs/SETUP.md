# 🚀 SilverTalk 초기 설정 가이드

## 📋 체크리스트

### 1️⃣ 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (필수!)
# GEMINI_API_KEY=your_api_key_here
```

**Gemini API 키 발급:**
1. https://makersuite.google.com/app/apikey 접속
2. "Create API key" 클릭
3. 생성된 키를 `.env` 파일에 추가

### 2️⃣ Docker 설치 확인
```bash
# Docker 버전 확인
docker --version
docker-compose --version

# Docker가 실행 중인지 확인
docker ps
```

**Windows 사용자:**
- Docker Desktop for Windows 설치 필요
- WSL 2 백엔드 권장

**Mac 사용자:**
- Docker Desktop for Mac 설치
- Apple Silicon(M1/M2): Rosetta 2 활성화 권장

### 3️⃣ 프로젝트 빌드 및 실행
```bash
# 1. 컨테이너 빌드 (첫 실행 시)
docker-compose build

# 2. 서비스 시작
docker-compose up

# 백그라운드 실행 (선호)
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 4️⃣ 서비스 확인
브라우저에서 다음 URL 접속:
- **API 서버:** http://localhost:8000
- **API 문서:** http://localhost:8000/docs (Swagger UI)
- **Flower:** http://localhost:5555 (Celery 모니터링)

### 5️⃣ 헬스체크
```bash
# API 상태 확인
curl http://localhost:8000/health

# Celery Worker 상태 확인
curl http://localhost:8000/api/debug/celery-status
```

## 🧪 첫 번째 테스트

### 텍스트 채팅 테스트
```bash
curl -X POST http://localhost:8000/api/text-chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "text": "안녕하세요, 어렸을 때 추억을 이야기해주세요"
  }'
```

**응답 예시:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "processing",
  "message": "AI가 답변을 생성 중입니다."
}
```

### 결과 조회
```bash
# 위에서 받은 task_id로 결과 조회
curl http://localhost:8000/api/task/{task_id}
```

## 🔧 환경별 설정

### 로컬 개발 환경 (기본 설정)
**특징:** CPU 모드, GPU 없어도 작동
- Windows (No GPU) ✅
- Mac (Apple Silicon) ✅
- Linux (No GPU) ✅

**설정 확인:**
```yaml
# docker-compose.yml
environment:
  - CUDA_VISIBLE_DEVICES=""  # 이 라인이 있어야 함
```

### AWS 프로덕션 환경 (GPU)
**인스턴스:** g4dn.xlarge (NVIDIA T4)

**설정 변경:**
1. `docker-compose.yml` 파일 열기
2. Worker 서비스 수정:
   ```yaml
   # CUDA_VISIBLE_DEVICES="" 라인 삭제
   
   # GPU 설정 주석 해제
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

**AWS EC2 사전 준비:**
```bash
# NVIDIA 드라이버 설치
sudo apt-get update
sudo apt-get install -y nvidia-driver-470

# NVIDIA Docker 런타임 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# GPU 확인
nvidia-smi
```

## 📊 모니터링

### Flower 대시보드
http://localhost:5555
- 실시간 태스크 모니터링
- Worker 상태 확인
- 작업 큐 확인

### 로그 확인
```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs web
docker-compose logs worker
docker-compose logs redis

# 실시간 로그 추적
docker-compose logs -f worker
```

## 🐛 트러블슈팅

### 문제 1: "CUDA 드라이버를 찾을 수 없습니다" (Windows/Mac)
**해결:** 정상입니다! 로컬 환경은 CPU 모드로 작동하도록 설계되었습니다.

**확인 방법:**
```bash
docker-compose logs worker | grep "device"
# 출력: "💻 GPU 미감지 - CPU 모드로 실행"
```

### 문제 2: Worker가 시작되지 않음
**원인:** Redis 연결 실패

**해결:**
```bash
# Redis 컨테이너 상태 확인
docker-compose ps redis

# Redis 재시작
docker-compose restart redis
docker-compose restart worker
```

### 문제 3: 모델 다운로드 실패
**원인:** 네트워크 또는 디스크 용량 부족

**해결:**
```bash
# 디스크 용량 확인
docker system df

# 컨테이너 내부 접속하여 수동 다운로드
docker exec -it silvertalk-worker bash
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', download_root='/app/models/whisper')"
```

### 문제 4: Gemini API 오류
**오류 메시지:** "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다"

**해결:**
1. `.env` 파일에 API 키 추가
2. 컨테이너 재시작:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## 📁 디렉토리 구조
```
silvertalk/
├── .env                    # ⚠️ 생성 필요 (.env.example 복사)
├── .env.example            # 환경 변수 템플릿
├── docker-compose.yml      # Docker 설정
├── README.md               # 프로젝트 문서
├── SETUP.md                # 이 파일
├── .gitignore              # Git 제외 파일
├── data/                   # 🔒 Git 제외 (음성/이미지 저장)
├── backend/
│   ├── app/                # FastAPI 웹 서버
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── routers/
│   ├── worker/             # Celery AI Worker
│   │   ├── celery_app.py
│   │   └── tasks.py        # 핵심 AI 로직
│   ├── common/             # 공통 설정
│   │   └── config.py
│   ├── models/             # 🔒 Git 제외 (AI 모델 가중치)
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── requirements.txt
└── .github/
    └── workflows/
        └── ci.yml          # GitHub Actions
```

## 🎯 다음 단계

1. **데이터베이스 추가:**
   - PostgreSQL 컨테이너 추가
   - SQLAlchemy 모델 정의
   - Alembic 마이그레이션 설정

2. **모바일 앱 연결:**
   - React Native 앱 개발
   - WebSocket 실시간 통신
   - 음성 녹음/재생 기능

3. **프로덕션 배포:**
   - AWS EC2 인스턴스 설정
   - Nginx 리버스 프록시
   - SSL 인증서 (Let's Encrypt)
   - CI/CD 파이프라인

## 📞 문제 해결이 안 될 때

1. **Issue 생성:**
   - GitHub Issues에 오류 로그 첨부
   - 환경 정보 (OS, Docker 버전) 포함

2. **로그 수집:**
   ```bash
   docker-compose logs > logs.txt
   ```

3. **환경 정보 확인:**
   ```bash
   docker --version
   docker-compose --version
   python --version
   ```

## ✅ 설정 완료 확인

다음을 모두 확인했다면 설정 완료입니다:
- [ ] `.env` 파일 생성 및 GEMINI_API_KEY 설정
- [ ] Docker 컨테이너 실행 중 (docker-compose ps)
- [ ] http://localhost:8000 접속 가능
- [ ] http://localhost:8000/docs Swagger UI 표시
- [ ] curl 테스트 성공
- [ ] Worker 로그에서 "모델 로딩 완료" 확인

**축하합니다! 🎉 이제 개발을 시작할 수 있습니다!**
