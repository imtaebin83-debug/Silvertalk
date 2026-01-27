#!/bin/bash
###############################################################################
# RunPod 환경 진단 스크립트
# 목적: Worker 실행 전 필수 라이브러리 및 GPU 상태 사전 점검
###############################################################################

echo "🔍 RunPod GPU Worker 환경 진단 시작..."
echo "=============================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 체크 함수
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

FAIL_COUNT=0

# ========================================
# 1. GPU 및 CUDA 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 [1/8] GPU & CUDA 상태"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "🔹 nvidia-smi 실행 가능: "
if command -v nvidia-smi &> /dev/null; then
    check_status
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
    check_status
    ((FAIL_COUNT++))
fi
echo ""

echo -n "🔹 CUDA 런타임 감지: "
if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    check_status
    python3 -c "import torch; print(f'  └─ Device: {torch.cuda.get_device_name(0)}')"
else
    check_status
    ((FAIL_COUNT++))
fi
echo ""

# ========================================
# 2. CUDA 핵심 라이브러리 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ [2/8] CUDA 핵심 라이브러리"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# libcublas 체크 (CUDA 11.x 또는 12.x)
echo -n "🔹 libcublas (v11 or v12): "
if ldconfig -p | grep -qE "libcublas\.so\.(11|12)"; then
    check_status
    CUBLAS_VER=$(ldconfig -p | grep -E "libcublas\.so\.(11|12)" | head -1 | awk '{print $1, "=>", $NF}')
    echo "  └─ $CUBLAS_VER"
else
    check_status
    echo -e "${RED}  ⚠️  libcublas.so.11 또는 .12 필요${NC}"
    ((FAIL_COUNT++))
fi

echo -n "🔹 libcublasLt (v11 or v12): "
if ldconfig -p | grep -qE "libcublasLt\.so\.(11|12)"; then
    check_status
else
    check_status
    ((FAIL_COUNT++))
fi
echo ""

# ========================================
# 3. cuDNN 라이브러리 확인 (중요!)
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 [3/8] cuDNN 라이브러리 (필수!)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "🔹 libcudnn_ops_infer.so.8: "
if ldconfig -p | grep -q "libcudnn_ops_infer.so.8"; then
    check_status
    ldconfig -p | grep libcudnn_ops_infer.so.8 | head -1 | awk '{print "  └─", $NF}'
else
    check_status
    echo -e "${RED}  ⚠️  Whisper CUDA 실행 불가! cuDNN 설치 필요${NC}"
    ((FAIL_COUNT++))
fi

echo -n "🔹 libcudnn.so.8: "
if ldconfig -p | grep -q "libcudnn.so.8"; then
    check_status
    CUDNN_VERSION=$(dpkg -l | grep libcudnn8 | awk '{print $3}' | head -1)
    echo "  └─ Version: $CUDNN_VERSION"
else
    check_status
    ((FAIL_COUNT++))
fi
echo ""

# ========================================
# 4. FFmpeg 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 [4/8] FFmpeg (오디오 처리)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "🔹 ffmpeg 설치: "
if command -v ffmpeg &> /dev/null; then
    check_status
    ffmpeg -version | head -1 | awk '{print "  └─", $0}'
else
    check_status
    ((FAIL_COUNT++))
fi
echo ""

# ========================================
# 5. Python 환경 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 [5/8] Python 환경"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "🔹 Python 버전: "
python3 --version
check_status

echo -n "🔹 Virtual Environment 활성화: "
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "  └─ $VIRTUAL_ENV"
else
    echo -e "${YELLOW}⚠️  WARNING${NC}"
    echo "  └─ venv 미활성화 (source /workspace/venv/bin/activate)"
fi
echo ""

# ========================================
# 6. Python 패키지 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 [6/8] Python 패키지"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUIRED_PACKAGES=(
    "torch"
    "faster-whisper"
    "ctranslate2"
    "google-generativeai"
    "celery"
    "redis"
)

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    echo -n "🔹 $pkg: "
    VERSION=$(pip show $pkg 2>/dev/null | grep Version | awk '{print $2}')
    if [ -n "$VERSION" ]; then
        echo -e "${GREEN}✅ $VERSION${NC}"
    else
        echo -e "${RED}❌ NOT INSTALLED${NC}"
        ((FAIL_COUNT++))
    fi
done
echo ""

# ========================================
# 7. Whisper 모델 파일 확인
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎤 [7/8] Whisper 모델 파일"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MODEL_PATH="/workspace/models/whisper"
echo -n "🔹 모델 디렉토리 존재: "
if [ -d "$MODEL_PATH" ]; then
    check_status
    FILE_COUNT=$(find "$MODEL_PATH" -type f | wc -l)
    echo "  └─ 파일 개수: $FILE_COUNT"
    if [ $FILE_COUNT -gt 0 ]; then
        find "$MODEL_PATH" -type f -name "*.bin" -o -name "model.bin" | head -3 | while read f; do
            SIZE=$(du -h "$f" | awk '{print $1}')
            echo "     ├─ $(basename $f) ($SIZE)"
        done
    fi
else
    check_status
    echo -e "${YELLOW}  ⚠️  모델 다운로드 필요 (첫 실행 시 자동)${NC}"
fi
echo ""

# ========================================
# 8. Redis 연결 테스트
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 [8/8] Redis 연결 (Celery Broker)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "🔹 Redis 연결 테스트: "
if python3 -c "
from celery import Celery
import sys
try:
    app = Celery()
    app.config_from_object('worker.celery_app')
    # Ping test
    result = app.control.inspect().stats()
    print('PASS')
    sys.exit(0)
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "PASS"; then
    check_status
else
    echo -e "${YELLOW}⚠️  WARNING${NC}"
    echo "  └─ Redis 연결 실패 (환경변수 확인 필요)"
fi
echo ""

# ========================================
# 최종 진단 결과
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 진단 결과 요약"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 검사 통과! Worker 실행 가능${NC}"
    echo ""
    echo "👉 Worker 시작 명령어:"
    echo "   celery -A worker.celery_app worker --loglevel=info --concurrency=4"
    exit 0
else
    echo -e "${RED}❌ $FAIL_COUNT개 항목 실패${NC}"
    echo ""
    echo "🔧 수정 방법:"
    echo "   1. 누락된 라이브러리 설치:"
    echo "      bash backend/worker/setup_runpod_complete.sh"
    echo ""
    echo "   2. Python 패키지 재설치:"
    echo "      source /workspace/venv/bin/activate"
    echo "      pip install -r backend/requirements.txt"
    echo ""
    echo "   3. 재진단:"
    echo "      bash backend/worker/check_runpod_environment.sh"
    exit 1
fi
