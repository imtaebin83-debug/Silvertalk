"""
공통 설정 파일
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 환경 구분
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 배포 모드 (LOCAL: docker-compose, CLOUD: EC2+RunPod)
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "LOCAL")
    
    # Redis 설정 (배포 모드에 따라 자동 선택)
    @property
    def redis_url(self) -> str:
        if self.DEPLOYMENT_MODE == "CLOUD":
            return os.getenv("UPSTASH_REDIS_URL", "")
        else:
            return os.getenv("LOCAL_REDIS_URL", "redis://localhost:6379/0")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # API 키
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # AWS 설정
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-2")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    
    # 저장소 백엔드 (LOCAL: 로컬 파일, S3: AWS S3)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "LOCAL")
    
    # 데이터베이스
    # TODO: 환경 변수 설정 
    @property
    def database_url(self) -> str:
        if self.DEPLOYMENT_MODE == "CLOUD":
            return os.getenv("PROD_DATABASE_URL", "")
        else:
            return os.getenv("LOCAL_DATABASE_URL", "")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # RunPod 설정
    RUNPOD_POD_ID: str = os.getenv("RUNPOD_POD_ID", "")
    RUNPOD_API_KEY: str = os.getenv("RUNPOD_API_KEY", "")
    
    # 로그 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 파일 경로
    DATA_DIR: str = "/app/data"
    MODELS_DIR: str = "/app/models"
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
settings = Settings()
