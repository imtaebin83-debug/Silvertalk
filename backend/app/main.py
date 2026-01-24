"""
SilverTalk FastAPI 메인 애플리케이션
반려견 AI와 함께하는 회상 치료 서비스
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from redis import Redis

# 라우터 import
from app.routers import auth, users, home, gallery, calendar, chat, video, memory

# 데이터베이스 초기화
from common.database import init_db

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 레디스 설정
rd = Redis(host='redis', port=6379)


# ============================================================
# 앱 생명주기 이벤트
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    # 시작 시
    logger.info("🚀 SilverTalk API 시작 중...")
    logger.info("📊 데이터베이스 초기화 중...")
    init_db()
    logger.info("✅ 데이터베이스 초기화 완료")
    
    yield
    
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
app.include_router(users.router)
app.include_router(home.router)
app.include_router(gallery.router)
app.include_router(calendar.router)
app.include_router(chat.router)
app.include_router(video.router)
app.include_router(memory.router)


# ============================================================
# 헬스체크 엔드포인트
# ============================================================
@app.get("/", tags=["System"])
async def root():
    
    rd.set("server_status", "connected")
    redis_status = rd.get("server_status").decode('utf-8')
    
    """서비스 상태 확인"""
    return {
        "service": "SilverTalk API",
        "status": "running",
        "version": "1.0.0",
        "redis_status": redis_status,
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
    Celery 태스크 결과 조회 (범용)
    
    Returns:
        - state: PENDING, STARTED, SUCCESS, FAILURE
        - result: 처리 결과
    """
    from worker.celery_app import celery_app
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "작업이 대기 중입니다."
            }
        elif task.state == "STARTED":
            return {
                "task_id": task_id,
                "status": "processing",
                "message": "AI가 처리 중입니다..."
            }
        elif task.state == "SUCCESS":
            return {
                "task_id": task_id,
                "status": "success",
                "result": task.result
            }
        elif task.state == "FAILURE":
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(task.info)
            }
        else:
            return {
                "task_id": task_id,
                "status": task.state.lower()
            }
    
    except Exception as e:
        logger.error(f"태스크 조회 오류: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
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
