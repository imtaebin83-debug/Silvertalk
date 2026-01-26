"""
인증 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from common.database import get_db
from common.models import User
from common.auth import (
    create_access_token,
    get_kakao_user_info,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================================================
# 요청/응답 스키마
# ============================================================
class KakaoLoginRequest(BaseModel):
    """카카오 로그인 요청"""
    kakao_access_token: str  # 클라이언트에서 받은 카카오 액세스 토큰


class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: str
    kakao_id: str
    nickname: Optional[str]
    profile_image: Optional[str]
    pet_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """로그인 응답 (토큰 + 사용자 정보)"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool  # 신규 가입 여부


# ============================================================
# 카카오 로그인/회원가입
# ============================================================
@router.post("/kakao", response_model=LoginResponse, summary="카카오 로그인")
async def kakao_login(
    request: KakaoLoginRequest,
    db: Session = Depends(get_db)
):
    """
    카카오 로그인/회원가입

    1. 클라이언트에서 카카오 SDK로 받은 액세스 토큰 검증
    2. 카카오 API로 사용자 정보 조회
    3. 신규 사용자면 자동 회원가입
    4. JWT 액세스 토큰 발급

    Request Body:
        - kakao_access_token: 카카오 SDK에서 받은 액세스 토큰

    Returns:
        - access_token: 서버 JWT 토큰 (이후 API 호출에 사용)
        - user: 사용자 정보
        - is_new_user: 신규 가입 여부
    """
    # 1. 카카오 토큰으로 사용자 정보 조회
    kakao_user = await get_kakao_user_info(request.kakao_access_token)

    if kakao_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="카카오 토큰이 유효하지 않습니다."
        )

    # 2. 카카오 사용자 정보 파싱
    kakao_id = str(kakao_user.get("id"))
    kakao_account = kakao_user.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    nickname = profile.get("nickname")
    profile_image = profile.get("profile_image_url")

    # 3. 기존 사용자 조회
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    is_new_user = False

    if user:
        # 기존 사용자: 프로필 업데이트
        if nickname:
            user.nickname = nickname
        if profile_image:
            user.profile_image = profile_image
        db.commit()
        db.refresh(user)
    else:
        # 신규 사용자: 회원가입
        user = User(
            kakao_id=kakao_id,
            nickname=nickname,
            profile_image=profile_image,
            pet_name="복실이"  # 기본 강아지 이름
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new_user = True

    # 4. JWT 토큰 발급
    access_token = create_access_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            kakao_id=user.kakao_id,
            nickname=user.nickname,
            profile_image=user.profile_image,
            pet_name=user.pet_name,
            is_active=user.is_active
        ),
        is_new_user=is_new_user
    )


# ============================================================
# 현재 사용자 정보 조회
# ============================================================
@router.get("/me", response_model=UserResponse, summary="현재 사용자 정보")
async def get_me(
    user: User = Depends(get_current_user)
):
    """
    JWT 토큰으로 현재 로그인한 사용자 정보 조회

    Headers:
        Authorization: Bearer {access_token}
    """
    return UserResponse(
        id=str(user.id),
        kakao_id=user.kakao_id,
        nickname=user.nickname,
        profile_image=user.profile_image,
        pet_name=user.pet_name,
        is_active=user.is_active
    )


# ============================================================
# 로그아웃
# ============================================================
@router.post("/logout", summary="로그아웃")
async def logout():
    """
    로그아웃

    JWT는 stateless이므로 서버에서 할 작업 없음.
    클라이언트에서 토큰 삭제 처리.
    """
    return {"message": "로그아웃되었습니다."}


# ============================================================
# 토큰 갱신
# ============================================================
@router.post("/refresh", response_model=TokenResponse, summary="토큰 갱신")
async def refresh_token(
    user: User = Depends(get_current_user)
):
    """
    새 액세스 토큰 발급

    기존 토큰이 유효하면 새 토큰 발급
    """
    new_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=new_token)
