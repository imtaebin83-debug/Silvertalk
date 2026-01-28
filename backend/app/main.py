"""
SilverTalk FastAPI 메인 애플리케이션
반려견 AI와 함께하는 회상 치료 서비스
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import redis
from common.config import settings


# 라우터 import
from app.routers import auth, users, home, gallery, calendar, chat, video, memory, generate

# 데이터베이스 초기화
from common.database import init_db

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 레디스 설정
# DEPLOYMENT_MODE에 따라 Redis 연결 방식 선택
if settings.DEPLOYMENT_MODE == "CLOUD":
    # Upstash Redis (RunPod/EC2)
    logger.info(f"🔗 CLOUD 모드: Upstash Redis 연결 - {settings.redis_url[:30]}...")
    rd = redis.from_url(settings.redis_url)
else:
    # 로컬 Docker Redis
    logger.info("🔗 LOCAL 모드: Docker Redis 연결 - redis:6379")
    rd = redis.Redis(host='redis', port=6379)

# ============================================================
# 앱 생명주기 이벤트
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    # 시작 시
    logger.info("🚀 SilverTalk API 시작 중...")
    logger.info("📊 데이터베이스 초기화 중...")
    try:
        init_db()
        logger.info("✅ 데이터베이스 연결 완료")
    except Exception as e:
        logger.warning(f"⚠️ 데이터베이스 연결 실패: {e}")
        logger.warning("DB 없이 계속 진행...")

    yield  # 앱 실행

    # 종료 시
    logger.info("👋 SilverTalk API 종료 중...")


# ============================================================
# FastAPI 앱 생성
# ============================================================
app = FastAPI(
    title="SilverTalk API",
    description="""
    ## 🐶 SilverTalk - AI 기반 회상 치료 서비스
    
    추억이 담긴 갤러리 사진을 매개로 반려견 AI 캐릭터와 대화하며 
    회상 요법 효과를 제공하고, 대화 내용을 영상으로 제작해 가족 소통을 돕습니다.
    
    ### 핵심 기능
    - 🎙️ 음성 기반 자연스러운 대화 (STT + LLM + TTS)
    - 📸 갤러리 사진 기반 회상 대화
    - 🎬 대화 내용을 영상으로 자동 생성
    - 💝 가족과의 소통 연결
    
    ### 기술 스택
    - **STT:** Faster-Whisper (Large-v3)
    - **LLM:** Google Gemini 1.5 Flash
    - **TTS:** Coqui XTTS v2
    - **Vision:** Gemini 1.5 Flash
    """,
    version="1.0.0",
    lifespan=lifespan
)

# app/main.py
@app.get("/auth/kakao/callback")
async def kakao_callback(code: str):
    # 클로드 코드(앱)가 기다리고 있는 주소로 튕겨줍니다!
    return RedirectResponse(url=f"silvertalk://auth?code={code}")

# CORS 설정 (React Native 앱 연결)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션: 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 라우터 등록
# ============================================================
app.include_router(auth.router)
# main.py의 라우터 등록 섹션 수정
#app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router)
app.include_router(home.router)
app.include_router(gallery.router, prefix="/photos", tags=["Gallery"])
app.include_router(calendar.router)
app.include_router(chat.router)
app.include_router(video.router)
app.include_router(memory.router)
app.include_router(generate.router)


# ============================================================
# 헬스체크 엔드포인트
# ============================================================
@app.get("/", tags=["System"])
async def root():
    """서비스 상태 확인"""
    redis_status = "disconnected"
    
    # Redis 연결 상태 체크 (에러 핸들링)
    try:
        rd.set("server_status", "connected")
        redis_status = rd.get("server_status").decode('utf-8')
    except Exception as e:
        logger.warning(f"⚠️ Redis 연결 실패: {e}")
        redis_status = "error"
    
    return {
        "service": "SilverTalk API",
        "status": "running",
        "version": "1.0.0",
        "redis_status": redis_status,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "environment": settings.ENVIRONMENT,
        "description": "반려견 AI와 함께하는 회상 치료 서비스",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """헬스체크 (로드 밸런서용)"""
    from common.database import engine
    
    try:
        # DB 연결 확인
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================================
# Celery 태스크 상태 조회 (공통)
# ============================================================
@app.get("/api/task/{task_id}", tags=["System"])
async def get_task_result(task_id: str):
    """
    Celery 태스크 결과 조회 (Polling용)
    
    프론트엔드에서 1초 간격으로 호출하여 AI 처리 상태 확인
    
    Returns:
        - status: pending, processing, success, error
        - 어르신 친화적인 메시지 포함
    """
    from worker.celery_app import celery_app
    
    # 어르신 친화적 메시지
    PENDING_MESSAGES = [
        "복실이가 준비하고 있어요...",
        "잠깐만요, 복실이가 귀 기울이고 있어요!",
    ]
    PROCESSING_MESSAGES = [
        "복실이가 열심히 듣고 있어요...",
        "복실이가 생각하고 있어요...",
        "복실이가 대답을 준비하고 있어요!",
    ]
    
    import random
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        # Celery 상태값을 소문자로 변환하여 비교
        state = task.state.lower() if task.state else "pending"
        logger.info(f"📋 Task {task_id} state: {state}")
        
        if state == "pending":
            return {
                "task_id": task_id,
                "status": "pending",
                "message": random.choice(PENDING_MESSAGES)
            }
        elif state == "started" or state == "progress":
            return {
                "task_id": task_id,
                "status": "processing",
                "message": random.choice(PROCESSING_MESSAGES)
            }
        elif state == "success":
            result = task.result
            logger.info(f"✅ Task {task_id} success, result: {result}")
            
            # Celery task 결과를 그대로 전달 (다양한 스키마 지원)
            response = {
                "task_id": task_id,
                "status": "success",
            }
            
            # AudioChatResult 필드
            if result.get("user_text"):
                response["user_text"] = result["user_text"]
            if result.get("ai_reply"):
                response["ai_reply"] = result["ai_reply"]
            if result.get("sentiment"):
                response["sentiment"] = result["sentiment"]
            
            # GreetingTaskResult 필드
            if result.get("ai_greeting"):
                response["ai_greeting"] = result["ai_greeting"]
            if result.get("analysis"):
                response["analysis"] = result["analysis"]
            
            # 공통 필드
            if result.get("session_id"):
                response["session_id"] = result["session_id"]
            
            return response
        elif state == "failure":
            return {
                "task_id": task_id,
                "status": "failure",
                "message": "앗, 잠깐 문제가 생겼어요. 다시 말씀해주세요!",
                "error_detail": str(task.info) if task.info else None
            }
        else:
            return {
                "task_id": task_id,
                "status": state,
                "message": "처리 중이에요..."
            }
    
    except Exception as e:
        logger.error(f"태스크 조회 오류: {str(e)}")
        return {
            "task_id": task_id,
            "status": "error",
            "message": "다시 시도해주세요.",
            "error_detail": str(e)
        }


# ============================================================
# 개발용 디버그 엔드포인트
# ============================================================
@app.get("/api/debug/celery-status", tags=["System"])
async def celery_status():
    """Celery Worker 연결 상태 확인"""
    from worker.celery_app import celery_app
    
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        return {
            "status": "connected" if stats else "disconnected",
            "workers": stats,
            "active_tasks": active
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
