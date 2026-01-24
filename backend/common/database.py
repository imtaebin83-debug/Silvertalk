"""
데이터베이스 연결 및 세션 관리
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

load_dotenv()

# 데이터베이스 URL
# - Docker: docker-compose.yml에서 postgres:5432 로 설정됨 (별도 설정 불필요)
# - 로컬 개발(컨테이너 외): localhost:5432 사용 (postgres 컨테이너 포트포워딩 5432)
# - .env에 DATABASE_URL을 넣으면 그 값을 사용
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://silvertalk:silvertalk_dev_password@localhost:5432/silvertalk"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_size=10,
    max_overflow=20
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 모델이 상속)
Base = declarative_base()


def get_db() -> Session:
    """
    데이터베이스 세션 의존성
    FastAPI 라우터에서 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    데이터베이스 초기화 (테이블 생성)
    """
    Base.metadata.create_all(bind=engine)
