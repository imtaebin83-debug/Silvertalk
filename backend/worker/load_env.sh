#!/bin/bash
###############################################################################
# 환경변수 안전 로드 스크립트
# 한글 주석과 빈 줄 제외하고 환경변수만 export
###############################################################################

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 파일을 찾을 수 없습니다: $ENV_FILE"
    exit 1
fi

echo "📦 환경변수 로드 중: $ENV_FILE"

# 주석(#으로 시작), 빈 줄, 공백만 있는 줄 제외
# 변수=값 형태만 추출하여 export
while IFS= read -r line || [ -n "$line" ]; do
    # 주석 제거
    line="${line%%#*}"
    # 앞뒤 공백 제거
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    
    # 빈 줄 건너뛰기
    [ -z "$line" ] && continue
    
    # 변수=값 형태인지 확인
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
        # 변수 참조 해석 (${VAR} → 실제 값)
        eval "export $line"
    fi
done < "$ENV_FILE"

echo "✅ 환경변수 로드 완료"

# 주요 변수 확인
echo ""
echo "확인:"
[ -n "$GEMINI_API_KEY" ] && echo "  └─ GEMINI_API_KEY: ${GEMINI_API_KEY:0:20}..."
[ -n "$UPSTASH_REDIS_URL" ] && echo "  └─ UPSTASH_REDIS_URL: ${UPSTASH_REDIS_URL:0:50}..."
[ -n "$REDIS_URL" ] && echo "  └─ REDIS_URL: ${REDIS_URL:0:50}..."
[ -n "$DEPLOYMENT_MODE" ] && echo "  └─ DEPLOYMENT_MODE: $DEPLOYMENT_MODE"
