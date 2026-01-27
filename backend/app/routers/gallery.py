"""
갤러리 관리 API 라우터
사진 메타데이터 동기화 및 큐레이션
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
from common.s3 import upload_file_to_s3 # 아까 만든 유틸리티
from common.models import SessionPhoto

from common.database import get_db
from common.models import User, UserPhoto

router = APIRouter(tags=["Gallery"])


# ============================================================
# 스키마
# ============================================================
class PhotoMetadata(BaseModel):
    """사진 메타데이터 (MVP: 로컬 경로 포함)"""
    local_uri: str  # 로컬 파일 경로 (필수)
    taken_at: Optional[datetime] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PhotoSyncRequest(BaseModel):
    """갤러리 동기화 요청"""
    photos: List[PhotoMetadata]


class PhotoResponse(BaseModel):
    id: str
    local_uri: Optional[str]  # 클라이언트가 로컬 파일 접근용
    s3_url: Optional[str]
    taken_at: Optional[datetime]
    location_name: Optional[str]
    ai_analysis: Optional[str]
    view_count: int
    
    class Config:
        from_attributes = True
        
        
        
@router.post("/batch-upload", summary="세션용 사진 묶음 업로드")
async def batch_upload_photos(
    session_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    선택된 사진과 앞뒤 5장(총 11장)을 S3에 업로드하고 세션에 연결
    """
    uploaded_photos = []
    
    for index, file in enumerate(files):
        # 1. S3 업로드용 파일명 생성
        file_ext = file.filename.split(".")[-1]
        s3_key = f"sessions/{session_id}/{index}_{uuid.uuid4()}.{file_ext}"
        
        # 2. S3 전송
        s3_url = upload_file_to_s3(file.file, s3_key)
        
        if s3_url:
            # 3. DB 저장 (순서는 -5부터 시작하도록 설정)
            new_session_photo = SessionPhoto(
                session_id=session_id,
                s3_url=s3_url,
                display_order=index - 5
            )
            db.add(new_session_photo)
            uploaded_photos.append({"url": s3_url, "order": index - 5})
            
    db.commit()
    return {"status": "success", "photos": uploaded_photos}

# 404 에러 해결을 위해 경로 수정
@router.get("/related", response_model=List[PhotoResponse])
async def get_related_photos(session_id: uuid.UUID, db: Session = Depends(get_db)):
    photos = db.query(SessionPhoto).filter(SessionPhoto.session_id == session_id).all()
    # UserPhoto와 형식을 맞추기 위해 변환하여 반환
    return [{"id": str(p.id), "url": p.s3_url, "order": p.display_order} for p in photos]


# ============================================================
# 사진 메타데이터 동기화 (초기 1회)
# ============================================================
@router.post("/sync-metadata", summary="사진 메타데이터 동기화")
async def sync_photos_metadata(
    kakao_id: str,
    request: PhotoSyncRequest,
    db: Session = Depends(get_db)
):
    """
    앱 설치 후 첫 실행 시 갤러리 메타데이터 동기화
    
    MVP 전략:
    1. 클라이언트가 expo-media-library로 EXIF 파싱
    2. 메타데이터만 서버로 전송 (사진 원본은 로컬 유지)
    3. 서버는 메타데이터만 DB 저장 (용량 작음)
    4. 이후 빠른 사진 선택 및 연관 추천 가능
    
    장점:
    - 초기 1회만 스캔 (백그라운드)
    - 이후 즉시 사진 선택 가능
    - 의미있는 연관 사진 추천 (날짜/장소 기반)
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 기존 사진 삭제 (재동기화)
    db.query(UserPhoto).filter(UserPhoto.user_id == user.id).delete()
    
    # 메타데이터만 저장
    for photo_meta in request.photos:
        new_photo = UserPhoto(
            user_id=user.id,
            local_uri=photo_meta.local_uri,  # 로컬 경로 (클라이언트가 접근용)
            taken_at=photo_meta.taken_at,
            location_name=photo_meta.location_name,
            latitude=photo_meta.latitude,
            longitude=photo_meta.longitude
        )
        db.add(new_photo)
    
    db.commit()
    
    return {
        "message": "갤러리 메타데이터가 동기화되었습니다.",
        "count": len(request.photos),
        "sync_time": datetime.utcnow()
    }


# ============================================================
# 사진 업로드 (Presign URL 발급)
# ============================================================
@router.post("/presign", summary="사진 업로드 URL 발급")
async def get_presign_url(
    kakao_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    S3 Presigned URL 발급 (클라이언트가 직접 업로드)
    
    - 대용량 사진 업로드를 위한 최적화
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # S3 Presigned URL 생성 로직 (boto3)
    # (추후 구현)
    
    presign_url = f"https://s3.amazonaws.com/silvertalk/{user.id}/{filename}"
    
    return {
        "presign_url": presign_url,
        "expires_in": 3600  # 1시간
    }


# ============================================================
# 랜덤 사진 큐레이션 (대화용)
# ============================================================
@router.get("/random", response_model=List[PhotoResponse], summary="초기 랜덤 사진 조회")
async def get_random_photos(
    kakao_id: str,
    limit: int = 4,
    db: Session = Depends(get_db)
):
    """
    대화 시작 전, 랜덤으로 4장의 사진 제공

    알고리즘:
    1. 오래된 사진 우선 (taken_at DESC)
    2. 사용 빈도가 낮은 사진 우선 (view_count ASC)
    3. 위 두 조건을 혼합하여 랜덤 선택
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 오래된 + 덜 본 사진 우선
    photos = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == user.id)
        .order_by(
            UserPhoto.view_count.asc(),
            func.random()  # PostgreSQL random()
        )
        .limit(limit)
        .all()
    )
    
    return photos


# ============================================================
# 사진 리스트 갱신 (다른 사진 보기)
# ============================================================
@router.get("/refresh", response_model=List[PhotoResponse], summary="사진 리스트 갱신")
async def refresh_photos(
    kakao_id: str,
    limit: int = 4,
    db: Session = Depends(get_db)
):
    """
    사용자가 '다른 사진 보기' 클릭 시 새로운 4장 제공
    """
    return await get_random_photos(kakao_id, limit, db)


