"""
Celery 앱 설정 및 초기화
"""
from celery import Celery
from common.config import settings

# Celery 앱 생성 (settings.redis_url은 DEPLOYMENT_MODE에 따라 동적 선택)
celery_app = Celery(
    "silvertalk_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks"]  # 태스크 모듈 자동 로드
)

# Celery 설정
celery_app.conf.update(
    # 태스크 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    
    # 성능 최적화
    task_acks_late=True,  # 태스크 완료 후 ACK
    worker_prefetch_multiplier=1,  # AI 작업은 한 번에 하나씩
    
    # 결과 저장 설정
    result_expires=3600,  # 1시간 후 결과 삭제
    
    # 타임아웃 설정 (AI 모델 로딩 시간 고려)
    task_time_limit=600,  # 10분
    task_soft_time_limit=540,  # 9분
)

# 워커 시작 시 실행
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """주기적 작업 설정 (필요 시)"""
    pass
