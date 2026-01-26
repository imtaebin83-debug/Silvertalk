"""
Celery + Redis 연결 테스트 스크립트
- EC2 (Producer) → Upstash Redis → RunPod (Worker) 통신 확인
- FastAPI 없이 직접 Task 전송
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery
from common.config import settings
import logging
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """
    1단계: Redis 연결 테스트
    """
    logger.info("=" * 60)
    logger.info("Step 1: Redis 연결 테스트")
    logger.info("=" * 60)
    
    import redis
    
    try:
        rd = redis.from_url(settings.redis_url)
        rd.ping()
        logger.info(f"✅ Redis 연결 성공: {settings.redis_url[:30]}...")
        
        # 테스트 데이터 저장/읽기
        test_key = "test:connection"
        test_value = "Hello from EC2!"
        
        rd.set(test_key, test_value)
        retrieved = rd.get(test_key).decode('utf-8')
        
        if retrieved == test_value:
            logger.info(f"✅ Redis 읽기/쓰기 성공: '{test_value}'")
        else:
            logger.error(f"❌ Redis 데이터 불일치: expected='{test_value}', got='{retrieved}'")
        
        # 정리
        rd.delete(test_key)
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {str(e)}")
        return False


def test_celery_producer():
    """
    2단계: Celery Producer 테스트 (Task 전송)
    """
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Celery Producer 테스트")
    logger.info("=" * 60)
    
    try:
        # Celery Producer 앱 생성
        app = Celery(
            "test_producer",
            broker=settings.redis_url,
            backend=settings.redis_url
        )
        
        logger.info(f"✅ Celery Producer 앱 생성 완료")
        logger.info(f"   Broker: {settings.redis_url[:30]}...")
        
        # 더미 Task 전송 (RunPod Worker가 처리)
        task_name = "worker.tasks.process_audio"
        task_args = {
            "audio_s3_key": "test/dummy_audio.wav",
            "user_id": "test_user_123",
            "session_id": "test_session_456"
        }
        
        logger.info(f"📤 Task 전송 중: {task_name}")
        logger.info(f"   Args: {task_args}")
        
        result = app.send_task(
            task_name,
            kwargs=task_args,
            queue="ai_tasks"
        )
        
        task_id = result.id
        logger.info(f"✅ Task 전송 완료!")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Queue: ai_tasks")
        
        # Task 상태 확인 (최대 10초 대기)
        logger.info("\n⏳ RunPod Worker 응답 대기 중... (최대 10초)")
        
        max_wait = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            state = result.state
            logger.info(f"   상태: {state}")
            
            if state == "SUCCESS":
                logger.info("✅ Task 성공!")
                logger.info(f"   결과: {result.result}")
                return True
            
            elif state == "FAILURE":
                logger.error(f"❌ Task 실패: {result.info}")
                return False
            
            elif state in ["PENDING", "STARTED", "RETRY"]:
                logger.info(f"   처리 중... ({state})")
                time.sleep(2)
            
            else:
                logger.warning(f"⚠️ 알 수 없는 상태: {state}")
                time.sleep(2)
        
        # 타임아웃
        logger.warning("⚠️ 타임아웃: RunPod Worker 응답 없음")
        logger.warning("   확인 사항:")
        logger.warning("   1. RunPod Worker가 실행 중인지 확인")
        logger.warning("   2. Worker 로그 확인: screen -r celery")
        logger.warning("   3. Worker가 ai_tasks 큐를 리스닝하는지 확인")
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Celery Producer 테스트 실패: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_deployment_mode():
    """
    0단계: 환경 설정 확인
    """
    logger.info("=" * 60)
    logger.info("Step 0: 환경 설정 확인")
    logger.info("=" * 60)
    
    logger.info(f"DEPLOYMENT_MODE: {settings.DEPLOYMENT_MODE}")
    logger.info(f"Redis URL: {settings.redis_url[:50]}...")
    logger.info(f"Database URL: {settings.database_url[:50]}..." if settings.database_url else "Database URL: (미설정)")
    logger.info(f"S3 Bucket: {settings.S3_BUCKET_NAME}")
    logger.info(f"AWS Region: {settings.AWS_REGION}")
    
    if settings.DEPLOYMENT_MODE == "CLOUD":
        logger.info("✅ CLOUD 모드: Upstash Redis 사용")
    else:
        logger.info("✅ LOCAL 모드: Docker Redis 사용")


def main():
    """
    전체 테스트 실행
    """
    logger.info("🚀 SilverTalk Celery + Redis 연결 테스트 시작\n")
    
    # 0. 환경 설정 확인
    test_deployment_mode()
    
    # 1. Redis 연결 테스트
    if not test_redis_connection():
        logger.error("\n❌ Redis 연결 실패. 테스트 중단.")
        logger.error("해결 방법:")
        logger.error("1. .env 파일의 UPSTASH_REDIS_URL 확인")
        logger.error("2. Upstash Dashboard에서 Redis 상태 확인")
        logger.error("3. 방화벽 설정 확인")
        return False
    
    # 2. Celery Producer 테스트
    if not test_celery_producer():
        logger.error("\n❌ Celery Producer 테스트 실패")
        logger.error("해결 방법:")
        logger.error("1. RunPod에서 Worker 실행 확인:")
        logger.error("   celery -A worker.celery_app worker --loglevel=info --concurrency=2")
        logger.error("2. Worker 로그 확인:")
        logger.error("   screen -r celery")
        logger.error("3. Worker가 Task를 받았는지 확인")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 모든 테스트 통과!")
    logger.info("=" * 60)
    logger.info("✅ Redis 연결 OK")
    logger.info("✅ Celery Producer → Worker 통신 OK")
    logger.info("\n다음 단계: FastAPI 엔드포인트에서 Task 전송 테스트")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
