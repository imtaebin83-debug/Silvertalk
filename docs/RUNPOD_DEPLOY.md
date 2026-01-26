# 🚀 RunPod Worker 배포 가이드

## 📋 사전 준비

### 완료된 사항
- ✅ RunPod Pod 생성 (RTX 3090)
- ✅ Upstash Redis URL 확보
- ✅ RDS PostgreSQL 엔드포인트 확보
- ✅ .env.runpod 파일 준비

### 필요한 정보
```bash
# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# RDS PostgreSQL
PROD_DATABASE_URL=postgresql://silvertalk:xxx@xxx.rds.amazonaws.com:5432/silvertalk

# Gemini API
GEMINI_API_KEY=AIza...

# AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxx
```

## 🔧 RunPod 배포 단계

### 1. SSH 접속
```bash
# RunPod 대시보드에서 SSH 명령어 복사
ssh root@xyz123.proxy.runpod.net -p 12345

# 비밀번호 입력 (대시보드에서 확인)
```

### 2. 시스템 업데이트
```bash
apt-get update
apt-get install -y git curl
```

### 3. 저장소 클론
```bash
cd /workspace
git clone https://github.com/YOUR_USERNAME/silvertalk.git
cd silvertalk
```

### 4. 환경 변수 설정
```bash
# .env.runpod 파일 생성
nano backend/.env

# 아래 내용 붙여넣기 (실제 값으로 변경):
```

```env
ENVIRONMENT=production
DEPLOYMENT_MODE=CLOUD

# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_HOST.upstash.io:6379
REDIS_URL=${UPSTASH_REDIS_URL}
CELERY_BROKER_URL=${UPSTASH_REDIS_URL}
CELERY_RESULT_BACKEND=${UPSTASH_REDIS_URL}

# RDS PostgreSQL
PROD_DATABASE_URL=postgresql://silvertalk:YOUR_PASSWORD@YOUR_ENDPOINT.rds.amazonaws.com:5432/silvertalk
DATABASE_URL=${PROD_DATABASE_URL}

# API Keys
GEMINI_API_KEY=your_actual_key

# AWS S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=silvertalk-media
STORAGE_BACKEND=S3

# GPU
CUDA_VISIBLE_DEVICES=0

LOG_LEVEL=INFO
```

```bash
# 저장: Ctrl+O, Enter, Ctrl+X
```

### 5. Python 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

### 6. GPU 확인
```bash
nvidia-smi

# 출력 예시:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 525.xx       Driver Version: 525.xx       CUDA Version: 12.0     |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
# | 30%   45C    P8    25W / 350W |      0MiB / 24576MiB |      0%      Default |
# +-------------------------------+----------------------+----------------------+
```

### 7. Celery Worker 시작 (테스트)
```bash
# 포그라운드 실행 (로그 확인용)
celery -A worker.celery_app worker --loglevel=info --concurrency=2

# 출력 예시:
# 🚀 GPU 감지: NVIDIA GeForce RTX 3090 - CUDA 모드 활성화
# ✅ Whisper 모델 로딩 완료 (device=cuda, compute_type=float16)
# ✅ XTTS 모델 로딩 완료 (device=cuda)
# ✅ Gemini 초기화 완료
# [2026-01-24 15:00:00,000: INFO/MainProcess] Connected to rediss://xxx.upstash.io:6379/0
# [2026-01-24 15:00:00,000: INFO/MainProcess] celery@xyz ready.
```

### 8. 백그라운드 실행 (프로덕션)
```bash
# 방법 A: nohup 사용
nohup celery -A worker.celery_app worker --loglevel=info --concurrency=2 > celery.log 2>&1 &

# 로그 확인
tail -f celery.log

# 방법 B: screen 사용 (권장)
apt-get install -y screen

# screen 세션 시작
screen -S celery

# Celery 실행
celery -A worker.celery_app worker --loglevel=info --concurrency=2

# 세션 빠져나오기: Ctrl+A, D
# 세션 복귀: screen -r celery
# 세션 종료: screen -X -S celery quit
```

## 🔍 모니터링

### Celery Worker 상태 확인
```bash
# 프로세스 확인
ps aux | grep celery

# 로그 확인
tail -f celery.log

# GPU 사용률 실시간 모니터링
watch -n 1 nvidia-smi
```

### Flower 대시보드 (EC2에서 실행)
```
http://your-ec2-ip:5555

확인 사항:
- Workers: 1 online (RunPod)
- Tasks: Pending, Active, Completed
- Success rate
```

### Upstash Redis 확인
```
Upstash Console > Database > Metrics
- Commands per second
- Storage usage
- Connection count
```

## ⚠️ 문제 해결

### Q1: "Connection refused" 에러
```bash
# Redis URL 확인
echo $CELERY_BROKER_URL

# rediss://로 시작하는지 확인 (TLS)
# Upstash Console에서 URL 재확인
```

### Q2: "CUDA out of memory"
```bash
# concurrency 줄이기
celery -A worker.celery_app worker --concurrency=1

# GPU 메모리 확인
nvidia-smi

# 모델 재로딩
killall celery
celery -A worker.celery_app worker --loglevel=info --concurrency=1
```

### Q3: "Module not found"
```bash
# 의존성 재설치
pip install -r requirements.txt

# PYTHONPATH 확인
export PYTHONPATH=/workspace/silvertalk/backend:$PYTHONPATH
```

### Q4: DB 연결 실패
```bash
# RDS 보안 그룹 확인
# Inbound rules에 RunPod IP 추가 필요

# RunPod IP 확인
curl ifconfig.me

# RDS 접근 테스트
psql -h your-rds-endpoint -U silvertalk -d silvertalk
```

## 🛑 Worker 종료

### 안전한 종료
```bash
# 현재 작업 완료 후 종료
celery -A worker.celery_app control shutdown

# 또는 screen에서 Ctrl+C
```

### 강제 종료
```bash
killall celery
```

## 💰 비용 절감

### Pod 중지 (하루 끝)
```
RunPod Dashboard > Pod > Stop

효과:
- 시간당 비용 중단
- 디스크 데이터 유지 (24시간)
- 환경 변수 유지
```

### 다음 날 재시작
```
RunPod Dashboard > Pod > Start

주의:
- AI 모델 재다운로드 (5-10분)
- Celery Worker 재시작 필요
```

## 📊 성능 벤치마크

### 예상 처리 시간 (RTX 3090)
```
Faster-Whisper (STT):
- 1분 오디오 → 3-5초

XTTS (TTS):
- 1문장 (20자) → 1-2초
- 1분 분량 → 10-15초

전체 파이프라인 (STT → LLM → TTS):
- 1분 대화 → 15-25초
```

## 다음 단계

1. ✅ Worker 정상 동작 확인
2. ✅ EC2 FastAPI와 연동 테스트
3. ✅ 실제 음성 파일 처리 테스트
4. ✅ 에러 알림 설정 (선택)
5. ✅ 모니터링 대시보드 구축 (선택)

Happy Computing! 🚀