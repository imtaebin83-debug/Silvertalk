"""
메인 화면 (Home) API 라우터
강아지 첫 인사 및 푸시 알림
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from common.database import get_db
from common.models import User

router = APIRouter(prefix="/home", tags=["메인 화면 (Home)"])


# ============================================================
# 스키마
# ============================================================
class GreetingResponse(BaseModel):
    """강아지 인사 메시지"""
    pet_name: str
    message: str
    voice_url: Optional[str] = None


# ============================================================
# 강아지 첫 인사 조회
# ============================================================
@router.get("/greeting", response_model=GreetingResponse, summary="강아지 첫 인사 조회")
async def get_greeting(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    앱 실행 시 강아지가 먼저 말을 거는 메시지
    
    예:
    - "할머니, 오셨어요? 심심해요 놀아주세요~"
    - "멍멍! 할머니, 저랑 사진 보면서 놀아요!"
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    pet_name = user.pet_name or "복실이"
    
    # 랜덤 인사 메시지 (추후 LLM으로 생성 가능)
    messages = [
        f"할머니, 오셨어요? {pet_name}이가 심심했어요! 놀아주세요~",
        f"멍멍! 할머니, 저랑 사진 보면서 놀아요!",
        f"{pet_name}이가 할머니 기다렸어요! 추억 이야기해주세요~",
    ]
    
    import random
    message = random.choice(messages)
    
    return GreetingResponse(
        pet_name=pet_name,
        message=message,
        voice_url=None  # 추후 TTS 생성
    )


# ============================================================
# 강아지 알림 (Push Notification)
# ============================================================
@router.post("/notification/push", summary="강아지 알림")
async def send_push_notification(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    정기적인 푸시 알림 (예: 하루 1회)
    "멍멍! 할머니, 오늘은 무슨 일 있었어요?"
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # FCM 또는 Expo Push Notification 전송 로직
    # (추후 구현)
    
    return {
        "message": "알림이 전송되었습니다.",
        "user_id": str(user.id)
    }
