"""
캘린더 관리 API 라우터
일정 동기화 및 조회
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from common.database import get_db
from common.models import User, UserCalendar

router = APIRouter(prefix="/calendars", tags=["Calendar"])


# ============================================================
# 스키마
# ============================================================
class CalendarEventRequest(BaseModel):
    """캘린더 일정"""
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    is_all_day: bool = False


class CalendarSyncRequest(BaseModel):
    """캘린더 동기화"""
    events: List[CalendarEventRequest]


class CalendarResponse(BaseModel):
    id: str
    title: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    location: Optional[str]
    is_all_day: bool
    
    class Config:
        from_attributes = True


# ============================================================
# 캘린더 일정 동기화
# ============================================================
@router.post("/sync", summary="캘린더 일정 동기화")
async def sync_calendar(
    kakao_id: str,
    request: CalendarSyncRequest,
    db: Session = Depends(get_db)
):
    """
    모바일 디바이스의 캘린더 일정을 서버로 동기화
    
    - Android Calendar API / iOS EventKit 연동
    - EXIF 매칭 실패 시 일정 기반으로 사진 날짜 추정
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 기존 일정 삭제 (재동기화)
    db.query(UserCalendar).filter(UserCalendar.user_id == user.id).delete()
    
    # 새 일정 추가
    for event in request.events:
        new_event = UserCalendar(
            user_id=user.id,
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            is_all_day=event.is_all_day
        )
        db.add(new_event)
    
    db.commit()
    
    return {
        "message": "캘린더가 동기화되었습니다.",
        "count": len(request.events)
    }


# ============================================================
# 일정 목록 조회
# ============================================================
@router.get("/", response_model=List[CalendarResponse], summary="일정 목록 조회")
async def get_calendars(
    kakao_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    사용자의 캘린더 일정 조회
    
    - start_date, end_date로 기간 필터링 가능
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    query = db.query(UserCalendar).filter(UserCalendar.user_id == user.id)
    
    if start_date:
        query = query.filter(UserCalendar.start_time >= start_date)
    if end_date:
        query = query.filter(UserCalendar.end_time <= end_date)
    
    calendars = query.order_by(UserCalendar.start_time.desc()).all()
    
    return calendars
