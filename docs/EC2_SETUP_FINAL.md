# EC2 최종 설정 가이드

## 🎯 환경 차이 정리

| 구분 | RunPod (Worker) | EC2 (API) | 로컬 개발 |
|------|----------------|-----------|----------|
| **환경** | Docker 컨테이너 | 베어메탈 Ubuntu | venv |
| **경로** | `/app/` | `/home/ubuntu/Silvertalk/` | `./backend/` |
| **GPU** | ✅ CUDA | ❌ CPU only | ❌ CPU only |
| **PyAV** | 11.0.0 (FFmpeg 최신) | **불필요** (soundfile 사용) | **불필요** |
| **TTS** | 0.21.3 (GitHub) | 0.21.3 (GitHub) | 0.21.3 (GitHub) |

## 🚀 EC2 설정 단계

### 1. 환경 변수 설정

```bash
cd ~/Silvertalk

# .env.production.example을 .env로 복사
cp .env.production.example .env

# .env 편집
nano .env
```

**반드시 수정해야 할 값:**
```env
DEPLOYMENT_MODE=CLOUD
MODELS_ROOT=/home/ubuntu/Silvertalk/backend/models
UPSTASH_REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_HOST.upstash.io:6379?ssl_cert_reqs=required
GEMINI_API_KEY=your_actual_key
```

### 2. 필수 디렉토리 생성

```bash
# 모델 저장 디렉토리
mkdir -p ~/Silvertalk/backend/models/whisper
mkdir -p ~/Silvertalk/backend/models/tts

# 데이터 디렉토리
mkdir -p ~/Silvertalk/backend/data
```

### 3. 가상환경 재생성 (Conda 충돌 제거)

```bash
# Conda 완전 비활성화
conda deactivate 2>/dev/null || true
conda config --set auto_activate_base false
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Python venv 패키지 설치
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# 기존 venv 삭제 및 재생성
cd ~/Silvertalk/backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### 4. 패키지 설치

```bash
# 최신 코드 받기
cd ~/Silvertalk
git pull

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치 (TTS는 GitHub에서 빌드되므로 시간 소요)
pip install -r backend/requirements.txt

# 설치 확인
python -c "from TTS.api import TTS; print('TTS 설치 성공')"
python -c "from faster_whisper import WhisperModel; print('Whisper 설치 성공')"
```

### 5. FastAPI 서버 실행

```bash
cd ~/Silvertalk/backend
source venv/bin/activate

# 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Celery Worker 실행 (EC2에서도 가능)

EC2에서도 CPU 모드로 Celery Worker를 실행할 수 있습니다 (테스트용):

```bash
# 별도 터미널
cd ~/Silvertalk/backend
source venv/bin/activate

celery -A worker.celery_app worker --loglevel=info --queue=ai_tasks
```

## ⚠️ 주의사항

### PyAV는 EC2에 설치하지 않습니다!
- **이유**: FFmpeg 4.2.7과 호환 문제
- **대안**: TTS가 자동으로 soundfile 백엔드 사용
- **RunPod**: PyAV 11.0.0 사용 (FFmpeg 최신 버전)
- **결론**: 두 환경 모두 정상 작동

### Ubuntu 20.04 vs 22.04
**현재 Ubuntu 20.04로 충분합니다!**
- Python 3.10 지원 ✅
- FFmpeg 4.2.7 (PyAV 없이 사용) ✅
- TTS 0.21.3 호환 ✅

**EC2 재생성 불필요**. Conda 충돌만 제거하면 됩니다.

## 🔧 트러블슈팅

### Conda 경로가 계속 나타날 때
```bash
# ~/.bashrc 편집
nano ~/.bashrc

# conda 관련 줄 주석 처리 또는 삭제
# >>> conda initialize >>>
# ... (이 섹션 전체 삭제 또는 주석)

# 저장 후
source ~/.bashrc
```

### 모델 다운로드가 느릴 때
- 첫 실행 시 Whisper large-v3 (몇 GB) 다운로드
- TTS XTTS v2 모델 다운로드
- 정상적인 현상입니다 (5-10분 소요 가능)

### 메모리 부족 시
```bash
# EC2 인스턴스 타입 확인
free -h

# 최소 권장: t3.large (8GB RAM)
# Whisper large-v3는 CPU 모드에서도 4-6GB 사용
```

## ✅ 성공 확인

### FastAPI 서버
```bash
curl http://localhost:8000/
# 응답: {"message": "SilverTalk API"}
```

### Redis 연결
```bash
python -c "from common.config import settings; import redis; r = redis.from_url(settings.redis_url); print(r.ping())"
# 출력: True
```

### Celery Worker (RunPod)
RunPod 터미널에서:
```bash
celery -A worker.celery_app worker --loglevel=info
# AI 모델 로딩 로그 확인
```
