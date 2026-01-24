"""
기억 및 인사이트 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import uuid

from common.database import get_db
from common.models import User, MemoryInsight

router = APIRouter(prefix="/memories", tags=["기억 및 인사이트 (Insight)"])


# ============================================================
# 스키마
# ============================================================
class MemoryResponse(BaseModel):
    id: int
    category: Optional[str]
    fact: Optional[str]
    importance: int
    updated_at: str
    
    class Config:
        from_attributes = True


# ============================================================
# 핵심 기억 목록 조회
# ============================================================
@router.get("/", response_model=List[MemoryResponse], summary="핵심 기억 목록 조회")
async def get_memories(
    kakao_id: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    사용자의 핵심 기억/인사이트 조회
    
    예:
    - "손주 이름: 민수"
    - "좋아하는 음식: 떡볶이"
    - "자주 가는 장소: 동네 공원"
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    query = db.query(MemoryInsight).filter(MemoryInsight.user_id == user.id)
    
    if category:
        query = query.filter(MemoryInsight.category == category)
    
    memories = query.order_by(
        MemoryInsight.importance.desc(),
        MemoryInsight.updated_at.desc()
    ).all()
    
    return memories


# ============================================================
# 카테고리별 기억 조회
# ============================================================
@router.get("/{category}", response_model=List[MemoryResponse], summary="카테고리별 기억 조회")
async def get_memories_by_category(
    kakao_id: str,
    category: str,
    db: Session = Depends(get_db)
):
    """
    특정 카테고리의 기억만 조회
    
    카테고리 예시:
    - family: 가족
    - travel: 여행
    - food: 음식
    - hobby: 취미
    """
    return await get_memories(kakao_id, category, db)


# ============================================================
# 사진별 누적 분석 조회
# ============================================================
@router.get("/photos/{photo_id}/analysis", summary="사진별 누적 분석 조회")
async def get_photo_analysis(
    photo_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 사진에 대한 AI 분석 결과 조회
    
    - Vision AI 분석 결과
    - 관련 대화 기록
    """
    from common.models import UserPhoto
    
    photo = db.query(UserPhoto).filter(UserPhoto.id == uuid.UUID(photo_id)).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")
    
    return {
        "photo_id": str(photo.id),
        "taken_at": photo.taken_at,
        "location_name": photo.location_name,
        "ai_analysis": photo.ai_analysis,
        "view_count": photo.view_count,
        "last_chat_session_id": str(photo.last_chat_session_id) if photo.last_chat_session_id else None
    }
