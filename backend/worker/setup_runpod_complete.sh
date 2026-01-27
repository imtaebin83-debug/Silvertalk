#!/bin/bash
###############################################################################
# RunPod GPU Worker - 완전한 환경 세팅 스크립트
# 목적: CUDA 라이브러리 + cuDNN + FFmpeg + Python 패키지 일괄 설치
###############################################################################

set -e  # 에러 발생 시 즉시 중단

echo "🚀 RunPod GPU Worker 완전 세팅 시작..."
echo "=============================================="

# 1. 시스템 업데이트
echo "📦 [1/5] 시스템 패키지 업데이트..."
apt-get update -qq

# 2. CUDA 버전 자동 감지 및 cuDNN 설치
echo "🧠 [2/5] CUDA 버전 감지 및 cuDNN 설치..."

# PyTorch CUDA 버전 감지
TORCH_CUDA=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "unknown")
echo "감지된 PyTorch CUDA 버전: $TORCH_CUDA"

# 기존 cuDNN 제거 (버전 불일치 방지)
echo "기존 cuDNN 제거 중..."
apt-get remove -y libcudnn8 libcudnn8-dev 2>/dev/null || true

# CUDA 11.8용 cuDNN 설치
if [[ "$TORCH_CUDA" == "11.8"* ]] || [[ "$TORCH_CUDA" == "11"* ]]; then
    echo "CUDA 11.8용 cuDNN 설치 중..."
    apt-get install -y -qq \
        libcudnn8=8.9.7.29-1+cuda11.8 \
        libcudnn8-dev=8.9.7.29-1+cuda11.8
elif [[ "$TORCH_CUDA" == "12"* ]]; then
    echo "CUDA 12.x용 cuDNN 설치 중..."
    apt-get install -y -qq \
        libcudnn8=8.9.7.29-1+cuda12.2 \
        libcudnn8-dev=8.9.7.29-1+cuda12.2
else
    echo "⚠️  CUDA 버전 감지 실패, CUDA 11.8용 설치 진행..."
    apt-get install -y -qq \
        libcudnn8=8.9.7.29-1+cuda11.8 \
        libcudnn8-dev=8.9.7.29-1+cuda11.8
fi

# ldconfig 갱신 (라이브러리 인덱스 재생성)
echo "라이브러리 인덱스 갱신 중..."
ldconfig

# cuDNN 설치 확인
echo "✅ cuDNN 설치 완료:"
dpkg -l | grep cudnn | head -3
echo ""
echo "ldconfig 확인:"
ldconfig -p | grep libcudnn | head -3

# 3. CUDA 라이브러리 확인 (이미 설치되어 있음)
echo "⚡ [3/5] CUDA 라이브러리 상태 확인..."
echo "현재 설치된 CUDA 라이브러리:"
ldconfig -p | grep -E "libcublas|libcudnn" | head -5

# CUDA 버전 확인
CUDA_VERSION=$(nvcc --version 2>/dev/null | grep "release" | awk '{print $6}' | cut -d',' -f1 || echo "unknown")
echo "CUDA Version: $CUDA_VERSION"

# libcublas 심볼릭 링크 생성 (CUDA 11 → 12 호환)
echo ""
echo "🔗 libcublas 호환성 링크 생성..."
CUDA_LIB_PATH="/usr/local/cuda/targets/x86_64-linux/lib"

# libcublas.so.12가 없으면 .11에서 링크 생성
if [ ! -f "$CUDA_LIB_PATH/libcublas.so.12" ] && [ -f "$CUDA_LIB_PATH/libcublas.so.11" ]; then
    echo "  └─ libcublas.so.11 → libcublas.so.12 링크 생성"
    ln -sf "$CUDA_LIB_PATH/libcublas.so.11" "$CUDA_LIB_PATH/libcublas.so.12"
    ln -sf "$CUDA_LIB_PATH/libcublas.so.11.11.4.6" "$CUDA_LIB_PATH/libcublas.so.12" 2>/dev/null || true
fi

if [ ! -f "$CUDA_LIB_PATH/libcublasLt.so.12" ] && [ -f "$CUDA_LIB_PATH/libcublasLt.so.11" ]; then
    echo "  └─ libcublasLt.so.11 → libcublasLt.so.12 링크 생성"
    ln -sf "$CUDA_LIB_PATH/libcublasLt.so.11" "$CUDA_LIB_PATH/libcublasLt.so.12"
    ln -sf "$CUDA_LIB_PATH/libcublasLt.so.11.11.4.6" "$CUDA_LIB_PATH/libcublasLt.so.12" 2>/dev/null || true
fi

# LD_LIBRARY_PATH 설정 권장
echo "  └─ LD_LIBRARY_PATH 설정 권장:"
echo "     export LD_LIBRARY_PATH=$CUDA_LIB_PATH:\$LD_LIBRARY_PATH"

# ldconfig 갱신
ldconfig

echo "  └─ ldconfig 갱신 완료"
echo ""
echo "확인:"
ls -la "$CUDA_LIB_PATH"/libcublas.so.* 2>/dev/null | head -6
echo ""
ldconfig -p | grep -E "libcublas.so.(11|12)" | head -4

# 4. FFmpeg 확인 (이미 설치되어 있으면 스킵)
echo "🎬 [4/5] FFmpeg 확인..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg 이미 설치됨"
    ffmpeg -version | head -1
else
    echo "FFmpeg 설치 중..."
    apt-get install -y -qq ffmpeg
fi

# 5. Python 패키지 확인 (이미 설치되어 있으면 스킵)
echo "🐍 [5/5] Python 패키지 확인..."
source /workspace/venv/bin/activate

# CTranslate2 확인
CT2_VERSION=$(pip show ctranslate2 2>/dev/null | grep Version | awk '{print $2}')
if [ "$CT2_VERSION" == "4.0.0" ]; then
    echo "✅ CTranslate2 4.0.0 이미 설치됨"
else
    echo "CTranslate2 재설치 중..."
    pip uninstall -y ctranslate2 2>/dev/null || true
    pip install --no-cache-dir ctranslate2==4.0.0
fi

# Faster-Whisper 확인
if pip show faster-whisper &>/dev/null; then
    echo "✅ Faster-Whisper 이미 설치됨"
    pip show faster-whisper | grep Version
else
    echo "Faster-Whisper 설치 중..."
    pip install --no-cache-dir faster-whisper
fi

echo ""
echo "✅ 완료! 설치된 라이브러리:"
echo "=============================================="
echo "PyTorch CUDA Version:"
python3 -c "import torch; print(f'  └─ {torch.version.cuda}')"
echo ""
echo "cuDNN:"
dpkg -l | grep cudnn | awk '{print "  └─", $2, $3}'
echo ""
echo "CUDA Libraries (ldconfig):"
ldconfig -p | grep -E "libcublas|libcudnn" | head -8 | awk '{print "  └─", $1}'
echo ""
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg:"
    ffmpeg -version | head -1 | awk '{print "  └─", $0}'
fi
echo ""
echo "Python Packages:"
pip list | grep -E "ctranslate2|faster-whisper|torch" | awk '{print "  └─", $0}'
echo ""
echo "🎉 RunPod 환경 세팅 완료!"
echo ""
echo "✅ 권장 사항:"
echo "   - Volume에 설치되어 영구 보존됨"
echo "   - Worker 재시작 시 자동으로 사용됨"
echo ""
echo "⚠️  중요: Worker 시작 전 환경변수 설정 필수"
echo "   export LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib:\$LD_LIBRARY_PATH"
echo ""
echo "👉 다음 단계:"
echo "   1. 환경변수 설정:"
echo "      export LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib:\$LD_LIBRARY_PATH"
echo "      export \$(cat .env | xargs)"
echo ""
echo "   2. Worker 시작:"
echo "      celery -A worker.celery_app worker --loglevel=info -Q ai_tasks --concurrency=1"
