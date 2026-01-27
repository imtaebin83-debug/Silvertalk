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

# 2. cuDNN 설치 (CUDA 12.x용)
echo "🧠 [2/5] cuDNN 라이브러리 설치 (CUDA 12.x)..."
apt-get install -y -qq \
    libcudnn8=8.9.7.29-1+cuda12.2 \
    libcudnn8-dev=8.9.7.29-1+cuda12.2

# cuDNN 버전 확인
echo "✅ cuDNN 설치 완료:"
dpkg -l | grep cudnn | head -3

# 3. CUDA 라이브러리 확인 (이미 설치되어 있음)
echo "⚡ [3/5] CUDA 라이브러리 상태 확인..."
echo "현재 설치된 CUDA 라이브러리:"
ldconfig -p | grep -E "libcublas|libcudnn" | head -5

# CUDA 버전 확인
CUDA_VERSION=$(nvcc --version 2>/dev/null | grep "release" | awk '{print $6}' | cut -d',' -f1 || echo "unknown")
echo "CUDA Version: $CUDA_VERSION"

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
echo "cuDNN:"
dpkg -l | grep cudnn | awk '{print $2, $3}'
echo ""
echo "CUDA Libraries (ldconfig):"
ldconfig -p | grep -E "libcublas|libcudnn" | head -5
echo ""
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg:"
    ffmpeg -version | head -1
fi
echo ""
echo "Python Packages:"
pip list | grep -E "ctranslate2|faster-whisper|torch"
echo ""
echo "🎉 RunPod 환경 세팅 완료!"
echo ""
echo "⚠️  CUDA 버전 확인 필요:"
echo "   현재: libcublas.so.11 (CUDA 11.x)"
echo "   cuDNN: 8.9.7 for CUDA 12.2"
echo ""
echo "👉 다음 단계:"
echo "   1. 진단 스크립트 실행:"
echo "      bash worker/check_runpod_environment.sh"
echo ""
echo "   2. Worker 시작:"
echo "      celery -A worker.celery_app worker --loglevel=info --concurrency=4"
