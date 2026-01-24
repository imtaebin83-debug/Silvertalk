"""
인증 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from common.database import get_db
from common.models import User

router = APIRouter(prefix="/auth", tags=["로그인 (Auth)"])


# ============================================================
# 요청/응답 스키마
# ============================================================
class KakaoLoginRequest(BaseModel):
    kakao_id: str
    nickname: Optional[str] = None
    profile_image: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    kakao_id: str
    nickname: Optional[str]
    profile_image: Optional[str]
    pet_name: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================================
# 카카오 회원가입/로그인
# ============================================================
@router.post("/kakao", response_model=UserResponse, summary="카카오 회원가입")
async def kakao_login(
    request: KakaoLoginRequest,
    db: Session = Depends(get_db)
):
    """
    카카오톡 원터치 로그인
    
    - 신규 사용자: 자동 회원가입
    - 기존 사용자: 로그인 처리
    """
    # 기존 사용자 조회
    user = db.query(User).filter(User.kakao_id == request.kakao_id).first()
    
    if user:
        # 기존 사용자: 프로필 업데이트
        if request.nickname:
            user.nickname = request.nickname
        if request.profile_image:
            user.profile_image = request.profile_image
        db.commit()
        db.refresh(user)
        return user
    
    # 신규 사용자: 회원가입
    new_user = User(
        kakao_id=request.kakao_id,
        nickname=request.nickname,
        profile_image=request.profile_image,
        pet_name="복실이"  # 기본 강아지 이름
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# ============================================================
# 로그아웃
# ============================================================
@router.post("/logout", summary="로그아웃")
async def logout():
    """
    로그아웃 (클라이언트에서 토큰 삭제)
    """
    return {"message": "로그아웃되었습니다."}


# ============================================================
# 사용자 정보 조회
# ============================================================
@router.get("/me", response_model=UserResponse, summary="사용자 정보 조회")
async def get_current_user(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자 정보 조회
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return user
