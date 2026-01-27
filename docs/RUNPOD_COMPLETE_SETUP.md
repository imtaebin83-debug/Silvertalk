# RunPod GPU Worker - 완전 설정 가이드

## 📋 개요
RunPod GPU Worker의 모든 필수 라이브러리 및 환경을 사전 점검하고 설치하는 가이드입니다.

---

## 🚀 빠른 시작 (3단계)

### 1️⃣ 환경 진단
```bash
cd /workspace
bash backend/worker/check_runpod_environment.sh
```

**출력 예시**:
```
🔍 RunPod GPU Worker 환경 진단 시작...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 [1/8] GPU & CUDA 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 nvidia-smi 실행 가능: ✅ PASS
NVIDIA GeForce RTX 3090, 525.125.06, 24576 MiB
🔹 CUDA 런타임 감지: ✅ PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 [3/8] cuDNN 라이브러리 (필수!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 libcudnn_ops_infer.so.8: ❌ FAIL
  ⚠️  Whisper CUDA 실행 불가! cuDNN 설치 필요
```

---

### 2️⃣ 누락된 라이브러리 일괄 설치
```bash
bash backend/worker/setup_runpod_complete.sh
```

**설치 항목**:
- ✅ cuDNN 8.9.7 (CUDA 12.x용)
- ✅ libcublas-12-0, libcublasLt-12-0
- ✅ FFmpeg (오디오 처리)
- ✅ CTranslate2 (CUDA 지원 재빌드)
- ✅ Faster-Whisper (최신 버전)

**소요 시간**: 약 5-10분
**필요 용량**: ~500MB

---

### 3️⃣ 재진단 및 Worker 실행
```bash
# 재진단
bash backend/worker/check_runpod_environment.sh

# 모든 검사 통과 시
celery -A worker.celery_app worker --loglevel=info --concurrency=4
```

---

## 🛡️ 에러별 해결 가이드

### ❌ `libcudnn_ops_infer.so.8: cannot open shared object file`
**증상**: Whisper CUDA 실행 중 Worker 프로세스 SIGABRT
**원인**: cuDNN 라이브러리 미설치
**해결**:
```bash
apt-get update
apt-get install -y libcudnn8=8.9.7.29-1+cuda12.2 libcudnn8-dev=8.9.7.29-1+cuda12.2
pip uninstall -y ctranslate2 && pip install --no-cache-dir ctranslate2==4.0.0
```

**검증**:
```bash
ldconfig -p | grep libcudnn_ops_infer.so.8
# 출력: libcudnn_ops_infer.so.8 (libc6,x86-64) => /usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8
```

---

### ❌ `Library libcublas.so.12 is not found`
**원인**: CUDA 핵심 라이브러리 누락
**해결**:
```bash
apt-get install -y libcublas-12-0 libcublasLt-12-0 cuda-cudart-12-0
```

---

### ❌ FFmpeg 관련 에러
**증상**: `ffmpeg: command not found` 또는 오디오 디코딩 실패
**해결**:
```bash
apt-get install -y ffmpeg
ffmpeg -version  # 검증
```

---

### ❌ Redis 연결 실패
**증상**: `ConnectionError: Error connecting to Redis`
**원인**: 환경변수 누락 또는 Upstash 접근 불가
**해결**:
```bash
# .env 파일 확인
cat /workspace/.env | grep REDIS

# 환경변수 확인
echo $REDIS_URL
echo $REDIS_PASSWORD

# 연결 테스트
python3 -c "
from celery import Celery
app = Celery(broker='rediss://default:YOUR_PASSWORD@new-grizzly-7377.upstash.io:6379')
print(app.control.inspect().stats())
"
```

---

## 🔍 진단 스크립트 상세

### `check_runpod_environment.sh`
**8가지 체크 항목**:
1. GPU & CUDA 상태 (nvidia-smi, torch.cuda)
2. CUDA 핵심 라이브러리 (libcublas, libcublasLt)
3. cuDNN 라이브러리 (libcudnn_ops_infer.so.8) ⭐
4. FFmpeg 설치
5. Python 환경 (버전, venv 활성화)
6. Python 패키지 (torch, faster-whisper, ctranslate2 등)
7. Whisper 모델 파일
8. Redis 연결 (Celery Broker)

**종료 코드**:
- `0`: 모든 검사 통과
- `1`: 1개 이상 실패 (수정 필요)

---

## 📊 예상 성능 비교

| 항목 | CPU (int8) | CUDA (float16) | 개선율 |
|------|-----------|----------------|--------|
| STT 처리 시간 | ~15-20초 | ~2-3초 | **5-7배** |
| 메모리 사용량 | 2GB | 4GB | - |
| 전력 소비 | 낮음 | 높음 | - |

**권장**: RunPod GPU 사용 시 CUDA 필수 (비용 대비 성능)

---

## 🔧 코드 개선 사항

### `tasks.py` - cuDNN 사전 체크 강화
```python
# CUDA 시도 (cuDNN 라이브러리 사전 체크 포함)
if device == "cuda":
    try:
        # cuDNN 라이브러리 존재 여부 사전 체크
        import ctypes
        ctypes.CDLL("libcudnn_ops_infer.so.8")
        logger.info("✅ cuDNN 라이브러리 확인 완료")
        
        whisper_model = WhisperModel(...)
    
    except (OSError, Exception) as cuda_error:
        logger.warning(f"⚠️ CUDA/cuDNN 로딩 실패: {cuda_error}")
        logger.warning("⚠️ CPU 모드로 강제 전환")
        whisper_model = WhisperModel(device="cpu", compute_type="int8", ...)
```

**개선 효과**:
- ❌ 기존: WhisperModel 로딩 후 STT 실행 중 SIGABRT (프로세스 죽음)
- ✅ 개선: cuDNN 사전 체크 → 없으면 즉시 CPU fallback (안정성 ⬆️)

---

## 📝 체크리스트 (Worker 시작 전)

- [ ] GPU 인식 (`nvidia-smi` 정상 출력)
- [ ] CUDA 라이브러리 설치 (libcublas, libcublasLt)
- [ ] **cuDNN 설치** (`ldconfig -p | grep libcudnn_ops_infer.so.8`)
- [ ] FFmpeg 설치 (`ffmpeg -version`)
- [ ] Python 패키지 설치 (`pip list | grep faster-whisper`)
- [ ] Redis 연결 테스트 (환경변수 확인)
- [ ] Whisper 모델 다운로드 공간 (Volume: `/workspace/models/`)
- [ ] 진단 스크립트 통과 (`check_runpod_environment.sh`)

---

## 🆘 트러블슈팅 플로우

```
Worker 시작 실패
    │
    ├─> 진단 스크립트 실행
    │   bash backend/worker/check_runpod_environment.sh
    │
    ├─> cuDNN 에러?
    │   └─> setup_runpod_complete.sh 실행
    │
    ├─> Python 패키지 누락?
    │   └─> pip install -r backend/requirements.txt
    │
    ├─> Redis 연결 실패?
    │   └─> .env 파일 확인, 환경변수 재설정
    │
    └─> 재진단 → Worker 재시작
```

---

## 📞 지원

**로그 확인 명령어**:
```bash
# Worker 로그 실시간 확인
celery -A worker.celery_app worker --loglevel=info

# GPU 상태 모니터링
watch -n 1 nvidia-smi

# 시스템 리소스
htop
```

**디버깅 모드**:
```bash
# 상세 로그 (디버그)
celery -A worker.celery_app worker --loglevel=debug --concurrency=1
```

---

## ✅ 설치 완료 확인

**성공 로그 예시**:
```
[2026-01-28 12:00:00,000: INFO] 🚀 GPU 감지: NVIDIA GeForce RTX 3090 - CUDA 모드 활성화
[2026-01-28 12:00:01,000: INFO] ✅ cuDNN 라이브러리 확인 완료
[2026-01-28 12:00:05,000: INFO] ✅ Whisper 모델 로딩 완료 (model=medium, device=cuda, path=/workspace/models/whisper)
[2026-01-28 12:00:06,000: INFO] ✅ Gemini 1.5 Flash 초기화 완료
[2026-01-28 12:00:06,000: INFO] celery@runpod-worker ready.
```

이제 음성 메시지 처리 시 **2-3초** 내 완료됩니다! 🚀
