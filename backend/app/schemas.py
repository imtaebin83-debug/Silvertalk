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
# 첫 인사 생성 태스크 결과 (Greeting) - 신규 추가
# ============================================================
class GreetingTaskResult(BaseModel):
    """generate_greeting 태스크 결과"""
    status: str = Field(..., description="작업 상태 (success, failure)")
    ai_greeting: str = Field(..., description="AI가 생성한 첫 인사 멘트")
    analysis: Optional[str] = Field(None, description="Vision AI의 이미지 분석 결과 (디버깅용)")
    session_id: str = Field(..., description="세션 UUID (문자열)")


# ============================================================
# 기억 인사이트 추출 태스크 결과 (Memory Insight)
# ============================================================
class MemoryInsightItem(BaseModel):
    """개별 기억 인사이트 항목"""
    category: str = Field(..., description="카테고리 (family, travel, food, hobby, emotion, other)")
    fact: str = Field(..., description="추출된 사실 (예: '손주와 함께 부산 바닷가에 다녀왔다')")
    importance: int = Field(..., ge=1, le=5, description="중요도 (1-5)")


class InsightTaskResult(BaseModel):
    """extract_memory_insights 태스크 결과"""
    status: str = Field("success", description="작업 상태 (success, failure)")
    session_id: str = Field(..., description="세션 UUID (문자열)")
    insights: List[MemoryInsightItem] = Field(default=[], description="추출된 인사이트 목록")
    error: Optional[str] = Field(None, description="에러 메시지 (실패 시)")


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
