"""
Pydantic 데이터 모델 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# 요청 스키마
# ============================================================
class ChatRequest(BaseModel):
    """텍스트 채팅 요청"""
    user_id: str = Field(..., description="사용자 ID")
    text: str = Field(..., description="사용자 입력 텍스트")
    session_id: Optional[str] = Field(None, description="대화 세션 ID")


class ImageAnalysisRequest(BaseModel):
    """이미지 분석 요청"""
    user_id: str
    prompt: Optional[str] = "이 사진에 대해 설명해주세요."


# ============================================================
# 응답 스키마
# ============================================================
class TaskResponse(BaseModel):
    """비동기 태스크 응답"""
    task_id: str = Field(..., description="Celery 태스크 ID")
    status: str = Field(..., description="작업 상태 (processing, success, failed)")
    message: str = Field(..., description="상태 메시지")


class ChatResponse(BaseModel):
    """채팅 응답"""
    task_id: str
    status: str
    message: str


class TaskResult(BaseModel):
    """태스크 결과"""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class AudioChatResult(BaseModel):
    """음성 채팅 결과"""
    status: str
    user_text: str = Field(..., description="사용자 음성 인식 텍스트")
    ai_reply: str = Field(..., description="AI 답변 텍스트")
    audio_url: str = Field(..., description="TTS 생성 음성 파일 경로")


class TextChatResult(BaseModel):
    """텍스트 채팅 결과"""
    status: str
    user_text: str
    ai_reply: str


class ImageAnalysisResult(BaseModel):
    """이미지 분석 결과"""
    status: str
    analysis: str = Field(..., description="이미지 분석 내용")


# ============================================================
# 데이터베이스 모델 (향후 확장용)
# ============================================================
class User(BaseModel):
    """사용자 모델"""
    user_id: str
    name: str
    age: Optional[int] = None
    created_at: datetime


class Conversation(BaseModel):
    """대화 기록"""
    conversation_id: str
    user_id: str
    session_id: str
    user_text: str
    ai_reply: str
    audio_url: Optional[str] = None
    created_at: datetime


class Memory(BaseModel):
    """회상 치료 기억 저장"""
    memory_id: str
    user_id: str
    title: str
    content: str
    images: Optional[List[str]] = None
    created_at: datetime
