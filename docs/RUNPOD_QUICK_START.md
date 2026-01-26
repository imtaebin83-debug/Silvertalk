# RunPod 빠른 시작 가이드

## ✅ Pod 생성 완료 후 즉시 할 일

### 1. 웹 터미널 활성화 (30초)
```
Pod 상세 페이지 → Connect 탭
→ Web terminal 섹션
→ "Enable web terminal" 토글 클릭
→ 터미널 창 열림 대기
```

### 2. GPU 확인 (터미널에서)
```bash
nvidia-smi

# 출력 확인:
# - RTX 3090 표시
# - 24GB VRAM
# - CUDA Version: 11.8
```

### 3. 저장소 클론
```bash
# Git 설치 확인
git --version

# 저장소 클론 (GitHub URL로 변경)
git clone https://github.com/YOUR_USERNAME/silvertalk.git

# 디렉토리 이동
cd silvertalk/backend
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
nano .env

# 다음 내용 입력:
```

**팀원에게 받을 정보:**
```bash
# 배포 모드
DEPLOYMENT_MODE=CLOUD
CUDA_VISIBLE_DEVICES=0

# Redis (Upstash)
UPSTASH_REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379

# Database (RDS)
PROD_DATABASE_URL=postgresql://username:password@rds-endpoint:5432/silvertalk

# S3
STORAGE_BACKEND=S3
AWS_ACCESS_KEY_ID=AKIAxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxx
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=silvertalk-prod

# Gemini API
GEMINI_API_KEY=your_gemini_key
```

**Nano 편집기 사용법:**
```
1. 위 내용 붙여넣기 (Ctrl+Shift+V)
2. 실제 값으로 수정
3. Ctrl+O (저장)
4. Enter (파일명 확인)
5. Ctrl+X (종료)
```

### 5. 시스템 패키지 설치 (5분)
```bash
apt-get update
apt-get install -y git ffmpeg libsndfile1 nano screen

# 설치 확인
ffmpeg -version
```

### 6. Python 의존성 설치 (10-15분)
```bash
# requirements.txt로 설치
pip install -r requirements.txt

# 진행률 확인 (느릴 수 있음, 정상)
# - torch: 이미 설치됨 (PyTorch 템플릿)
# - TTS: 1.8GB 다운로드
# - faster-whisper: 모델 다운로드

# 설치 완료 확인
python -c "import torch; print(torch.cuda.is_available())"
# True 출력되어야 함

python -c "from TTS.api import TTS; print('TTS OK')"
# TTS OK 출력되어야 함
```

### 7. Celery Worker 시작 (테스트)
```bash
# 포그라운드 실행 (테스트)
celery -A worker.celery_app worker --loglevel=info --concurrency=2

# 성공 메시지 확인:
# - "celery@territorial_amaranth_mastodon ready."
# - "Connected to rediss://..."
# - "Task registered: ..."

# GPU 메모리 할당 로그 확인:
# - Loading Whisper model...
# - Loading XTTS model...

# Ctrl+C로 중지
```

### 8. Screen으로 백그라운드 실행
```bash
# Screen 세션 생성
screen -S celery

# Celery Worker 시작
celery -A worker.celery_app worker --loglevel=info --concurrency=2

# 세션 분리 (Worker는 계속 실행)
# Ctrl+A, 그 다음 D 키

# 세션 목록 확인
screen -ls
# 출력: 1234.celery (Detached)

# 다시 연결 (로그 확인용)
screen -r celery

# 다시 분리
# Ctrl+A, D
```

### 9. 모니터링

#### GPU 사용률
```bash
# 실시간 모니터링
watch -n 1 nvidia-smi

# 또는 1회 확인
nvidia-smi

# 확인 사항:
# - GPU-Util: 0-100%
# - Memory-Usage: /24576MiB
# - Processes: python 프로세스
```

#### Celery 로그
```bash
# Screen 세션 확인
screen -r celery

# 로그 출력:
# - Task 수신 메시지
# - AI 모델 실행 로그
# - 에러 발생 시 Traceback
```

#### EC2 Flower 대시보드
```
브라우저: http://your-ec2-ip:5555

확인 사항:
- Workers: territorial_amaranth_mastodon (온라인)
- Tasks: Active, Completed, Failed 수
- Task 상세 로그
```

### 10. 통합 테스트 (EC2에서)

```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# API 테스트 (음성 업로드)
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: multipart/form-data" \
  -F "user_id=test-user" \
  -F "audio_file=@test_audio.wav"

# 응답 확인:
{
  "task_id": "abc123...",
  "status": "processing"
}
```

**RunPod에서 로그 확인:**
```bash
screen -r celery

# 출력 예시:
[INFO] Task chat.process_audio[abc123] received
[INFO] Loading audio file from S3...
[INFO] Running Whisper STT...
[INFO] Transcription: "안녕하세요"
[INFO] Calling Gemini API...
[INFO] Running XTTS TTS...
[INFO] Uploading result to S3...
[INFO] Task completed in 15.2s
```

## ✅ 성공 기준

- [x] nvidia-smi로 RTX 3090 확인
- [x] Python에서 CUDA 사용 가능
- [x] Celery Worker 시작 성공
- [x] Upstash Redis 연결 확인
- [x] RDS PostgreSQL 연결 확인
- [x] Whisper 모델 로딩 성공
- [x] XTTS 모델 로딩 성공
- [x] S3 업로드 테스트 성공
- [x] EC2 → RunPod Task 처리 확인

## 🚨 문제 해결

### Q: pip install이 매우 느림
```bash
# 정상입니다. TTS 1.8GB 다운로드 중
# 10-15분 대기

# 진행 상황 확인
pip list | grep TTS
```

### Q: CUDA out of memory
```bash
# concurrency 줄이기
celery -A worker.celery_app worker --loglevel=info --concurrency=1

# 모델 캐싱 확인
ls ~/.cache/huggingface
```

### Q: Redis 연결 실패
```bash
# .env 파일 확인
cat .env | grep UPSTASH

# SSL 연결 확인 (rediss:// 로 시작해야 함)
# 팀원에게 Upstash URL 재확인
```

### Q: Screen 세션 종료됨
```bash
# 세션 목록 확인
screen -ls

# 없으면 다시 시작
screen -S celery
celery -A worker.celery_app worker --loglevel=info --concurrency=2
```

## 💰 비용 관리

### 작업 완료 후 Pod 중지
```
RunPod Dashboard → Pods → territorial_amaranth_mastodon
→ Stop 버튼 클릭
→ 시간당 비용 중단
→ 디스크 데이터 24시간 유지
```

### 다시 시작
```
Pods → territorial_amaranth_mastodon → Start
→ 2-3분 대기
→ 모델 재다운로드 필요 (5분)
→ Celery Worker 재시작
```

### 완전 종료 (프로젝트 종료 시)
```
Pods → territorial_amaranth_mastodon → Terminate
→ 모든 데이터 삭제
→ 비용 완전 중단
```

## 📞 지원

문제 발생 시:
1. `screen -r celery`로 Worker 로그 확인
2. `nvidia-smi`로 GPU 사용률 확인
3. Flower 대시보드에서 Task 상태 확인
4. EC2 FastAPI 로그 확인

화이팅! 🚀
