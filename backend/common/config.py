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
    
    # Redis 설정
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
    
    # 데이터베이스
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # 로그 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 파일 경로
    DATA_DIR: str = "/app/data"
    MODELS_DIR: str = "/app/models"
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
settings = Settings()
