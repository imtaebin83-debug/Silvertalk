"""
FastAPI(EC2)용 Celery Producer 설정
- Worker를 실행하지 않고 Task만 전송하는 용도
- AI 라이브러리(torch, TTS 등) 불필요
"""
from celery import Celery
from common.config import settings

def get_celery_app() -> Celery:
    """
    Celery Producer 앱 생성 (EC2 FastAPI용)
    
    특징:
    - Worker 실행하지 않음 (send_task만 사용)
    - AI 라이브러리 import 없음 (가벼움)
    - settings.redis_url로 Upstash/Local 자동 전환
    
    Returns:
        Celery: Producer 전용 Celery 앱
    """
    app = Celery(
        "silvertalk_producer",
        broker=settings.redis_url,
        backend=settings.redis_url
    )
    
    # Producer 전용 설정
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Seoul",
        enable_utc=True,
        
        # Producer는 결과를 바로 확인하지 않음
        result_expires=3600,
        
        # Task 라우팅 (RunPod Worker의 ai_tasks 큐로 전송)
        task_routes={
            "worker.tasks.*": {"queue": "ai_tasks"},
        },
    )
    
    return app


# 전역 인스턴스
celery_producer = get_celery_app()
