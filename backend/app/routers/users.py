"""
사용자 관리 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from common.database import get_db
from common.models import User

router = APIRouter(prefix="/users", tags=["사용자 관리 (Users)"])


# ============================================================
# 스키마
# ============================================================
class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    pet_name: Optional[str] = None
    birth_date: Optional[datetime] = None


class UserResponse(BaseModel):
    id: str
    kakao_id: str
    nickname: Optional[str]
    profile_image: Optional[str]
    pet_name: Optional[str]
    birth_date: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================================
# 어르신 정보 조회
# ============================================================
@router.get("/me", response_model=UserResponse, summary="어르신 정보")
async def get_user_info(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """현재 사용자 정보 조회"""
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return user


# ============================================================
# 어르신 정보 수정
# ============================================================
@router.patch("/me", response_model=UserResponse, summary="어르신 정보 수정")
async def update_user_info(
    kakao_id: str,
    request: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    사용자 정보 수정
    - 닉네임, 반려견 이름, 생년월일 등
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 수정
    if request.nickname is not None:
        user.nickname = request.nickname
    if request.pet_name is not None:
        user.pet_name = request.pet_name
    if request.birth_date is not None:
        user.birth_date = request.birth_date
    
    db.commit()
    db.refresh(user)
    
    return user


# ============================================================
# 회원 탈퇴
# ============================================================
@router.delete("/me", summary="회원 탈퇴")
async def delete_user(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    회원 탈퇴 (소프트 삭제)
    is_active = False로 변경
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "회원 탈퇴가 완료되었습니다."}
