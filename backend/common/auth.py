"""
JWT 토큰 및 인증 유틸리티
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx

from .config import settings
from .database import get_db
from .models import User


# Bearer 토큰 스키마
security = HTTPBearer()


# ============================================================
# JWT 토큰 생성/검증
# ============================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰 검증 및 페이로드 반환"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ============================================================
# 카카오 API 호출
# ============================================================
async def get_kakao_user_info(kakao_access_token: str) -> Optional[dict]:
    """
    카카오 액세스 토큰으로 사용자 정보 조회

    카카오 API: GET https://kapi.kakao.com/v2/user/me

    Returns:
        {
            "id": 12345678,  # 카카오 고유 ID
            "kakao_account": {
                "profile": {
                    "nickname": "홍길동",
                    "profile_image_url": "http://..."
                }
            }
        }
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={
                    "Authorization": f"Bearer {kakao_access_token}",
                    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception:
            return None


# ============================================================
# FastAPI 의존성: 현재 사용자 조회
# ============================================================
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    JWT 토큰에서 현재 사용자 조회

    사용법:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": str(user.id)}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # DB에서 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다."
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """선택적 인증 (토큰 없어도 OK)"""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        return None

    user_id: str = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == user_id).first()
