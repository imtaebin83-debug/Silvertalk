"""
SQLAlchemy 데이터베이스 모델
DB 스키마 기반 정의
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .database import Base


# ============================================================
# Enum 타입 정의
# ============================================================
class VideoStatus(str, enum.Enum):
    """영상 생성 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionStatus(str, enum.Enum):
    """대화 세션 상태"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ============================================================
# 사용자 관련 모델
# ============================================================
class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kakao_id = Column(String, unique=True, nullable=False, index=True)
    nickname = Column(String, nullable=True)
    profile_image = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 반려견 설정
    pet_name = Column(String, nullable=True)  # 강아지 이름
    birth_date = Column(DateTime, nullable=True)  # 사용자 생년월일 (연령대 파악용)
    
    # 관계
    photos = relationship("UserPhoto", back_populates="user", cascade="all, delete-orphan")
    calendars = relationship("UserCalendar", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("GeneratedVideo", back_populates="user", cascade="all, delete-orphan")
    memory_insights = relationship("MemoryInsight", back_populates="user", cascade="all, delete-orphan")


class UserPhoto(Base):
    """사용자 갤러리 사진 메타데이터"""
    __tablename__ = "user_photos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # MVP: 로컬 경로만 저장 (사진 원본은 클라이언트에 유지)
    local_uri = Column(Text, nullable=True)  # 로컬 파일 경로
    s3_url = Column(Text, nullable=True)      # S3 URL (추후 업로드 시)
    
    # 촬영 날짜/시간
    taken_at = Column(DateTime, nullable=True)
    
    # 위치 정보
    location_name = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Vision AI 분석 결과
    ai_analysis = Column(Text, nullable=True)  # JSON 형태로 저장
    
    # 연결된 대화 세션
    last_chat_session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    view_count = Column(Integer, default=0)  # 사진이 대화에 사용된 횟수
    
    # 관계
    user = relationship("User", back_populates="photos")
    last_chat_session = relationship("ChatSession", foreign_keys=[last_chat_session_id])


class UserCalendar(Base):
    """사용자 캘린더 일정"""
    __tablename__ = "user_calendars"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    title = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    location = Column(Text, nullable=True)
    is_all_day = Column(Boolean, default=False)
    
    # 관계
    user = relationship("User", back_populates="calendars")


# ============================================================
# 대화 관련 모델
# ============================================================
class ChatSession(Base):
    """대화 세션 (하나의 사진에 대한 전체 대화)"""
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 메인 사진
    main_photo_id = Column(UUID(as_uuid=True), ForeignKey("user_photos.id"), nullable=True)
    
    # 대화 요약 (영상 생성용)
    summary = Column(Text, nullable=True)
    
    # 세션 상태
    is_completed = Column(Boolean, default=False)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    turn_count = Column(Integer, default=0)  # 대화 턴 수
    
    # 관계
    user = relationship("User", back_populates="chat_sessions")
    main_photo = relationship("UserPhoto", foreign_keys=[main_photo_id])
    logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")
    videos = relationship("GeneratedVideo", back_populates="session")


class ChatLog(Base):
    """대화 로그 (개별 메시지)"""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    
    role = Column(String, nullable=False)  # "user" 또는 "assistant"
    content = Column(Text, nullable=False)
    
    # 음성 파일 (TTS 생성 결과)
    voice_url = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    session = relationship("ChatSession", back_populates="logs")


# ============================================================
# 영상 관련 모델
# ============================================================
class GeneratedVideo(Base):
    """생성된 추억 영상"""
    __tablename__ = "generated_videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    
    # S3 URL
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # 생성 상태
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.PENDING)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="videos")
    session = relationship("ChatSession", back_populates="videos")


# ============================================================
# 기억 인사이트 모델
# ============================================================
class MemoryInsight(Base):
    """대화에서 추출된 기억/인사이트"""
    __tablename__ = "memory_insights"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    category = Column(String, nullable=True)  # "family", "travel", "food" 등
    fact = Column(Text, nullable=True)  # "손주 이름: 민수", "좋아하는 음식: 떡볶이"
    
    # 출처 (어느 대화 로그에서 추출되었는지)
    source_log_id = Column(Integer, ForeignKey("chat_logs.id"), nullable=True)
    
    importance = Column(Integer, default=1)  # 중요도 (1-5)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="memory_insights")
    source_log = relationship("ChatLog")
