"""
추억 영상 생성 및 관리 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from common.database import get_db
from common.models import User, ChatSession, GeneratedVideo, VideoStatus, VideoType

router = APIRouter(prefix="/videos", tags=["추억 영상 (Video)"])


# ============================================================
# 스키마
# ============================================================
class VideoResponse(BaseModel):
    id: str
    session_id: str
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    video_type: Optional[str] = "slideshow"
    duration_seconds: Optional[float] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VideoGenerateRequest(BaseModel):
    session_id: str
    video_type: str = "slideshow"  # "slideshow" (FFmpeg) 또는 "ai_animated" (Replicate SVD)
    voice_id: Optional[str] = None  # 손주 목소리 ID (추후 확장)


# ============================================================
# 애니메이션 제작 요청
# ============================================================
@router.post("/generate", summary="추억 영상 제작 요청")
async def generate_video(
    request: VideoGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    대화 세션을 기반으로 추억 영상 생성

    **video_type 옵션:**
    - `slideshow`: FFmpeg Ken Burns 슬라이드쇼 (모든 사진 사용, 무료)
    - `ai_animated`: Replicate SVD AI 애니메이션 (첫 사진만 사용, 유료)

    Flow:
    1. SessionPhoto에서 사진 목록 수집
    2. Gemini로 내레이션 스크립트 생성
    3. Coqui XTTS v2로 TTS 나레이션 생성
    4. video_type에 따라 FFmpeg 또는 Replicate SVD로 영상 생성
    5. S3 업로드
    """
    # video_type 검증
    if request.video_type not in ["slideshow", "ai_animated"]:
        raise HTTPException(
            status_code=400,
            detail="video_type은 'slideshow' 또는 'ai_animated'만 가능합니다."
        )

    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(request.session_id)
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if not session.is_completed:
        raise HTTPException(status_code=400, detail="대화가 아직 완료되지 않았습니다.")

    # 같은 타입의 영상이 이미 생성 중인지 확인
    existing_video = db.query(GeneratedVideo).filter(
        GeneratedVideo.session_id == session.id,
        GeneratedVideo.video_type == VideoType(request.video_type),
        GeneratedVideo.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
    ).first()

    if existing_video:
        return {
            "message": "이미 영상이 생성 중입니다.",
            "video_id": str(existing_video.id),
            "video_type": request.video_type,
            "status": existing_video.status.value
        }

    # 새 영상 레코드 생성
    new_video = GeneratedVideo(
        user_id=session.user_id,
        session_id=session.id,
        status=VideoStatus.PENDING,
        video_type=VideoType(request.video_type)
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    # Celery 태스크 실행 (백그라운드)
    from worker.tasks import generate_memory_video
    task = generate_memory_video.apply_async(
        args=[str(session.id), str(new_video.id), request.video_type],
        queue="ai_tasks"
    )

    return {
        "message": "영상 생성이 시작되었습니다.",
        "video_id": str(new_video.id),
        "video_type": request.video_type,
        "task_id": task.id,
        "status": "pending"
    }


# ============================================================
# 제작 상태 조회
# ============================================================
@router.get("/{video_id}/status", summary="제작 상태 조회")
async def get_video_status(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    영상 생성 상태 확인
    
    - PENDING: 대기 중
    - PROCESSING: 생성 중
    - COMPLETED: 완료
    - FAILED: 실패
    """
    video = db.query(GeneratedVideo).filter(
        GeneratedVideo.id == uuid.UUID(video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
    
    return {
        "video_id": str(video.id),
        "status": video.status,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
        "created_at": video.created_at
    }


# ============================================================
# 나레이션 보이스 목록
# ============================================================
@router.get("/voices", summary="나레이션 보이스 목록")
async def get_voice_list():
    """
    TTS 목소리 옵션 목록 (MVP)
    
    Coqui XTTS v2 기본 제공 목소리 사용
    - 따뜻한 여성 목소리 (손녀 느낌)
    - 부드러운 남성 목소리 (손자 느낌)
    - 밝은 여성 목소리
    """
    return {
        "voices": [
            {
                "id": "warm_female",
                "name": "따뜻한 여성",
                "description": "손녀같은 목소리",
                "sample_url": None,  # 추후 샘플 음성 추가
                "is_default": True
            },
            {
                "id": "soft_male",
                "name": "부드러운 남성",
                "description": "손자같은 목소리",
                "sample_url": None,
                "is_default": False
            },
            {
                "id": "bright_female",
                "name": "밝은 여성",
                "description": "활기찬 목소리",
                "sample_url": None,
                "is_default": False
            },
        ]
    }


# ============================================================
# 카카오톡 공유 데이터
# ============================================================
@router.post("/{video_id}/share", summary="카카오톡 공유 데이터")
async def share_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    카카오톡 공유용 메타데이터 생성
    
    - 썸네일 URL
    - 제목
    - 설명
    """
    video = db.query(GeneratedVideo).filter(
        GeneratedVideo.id == uuid.UUID(video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
    
    if video.status != VideoStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="영상이 아직 완료되지 않았습니다.")
    
    session = video.session
    user = video.user
    
    return {
        "title": f"{user.nickname or '할머니'}의 추억",
        "description": session.summary or "소중한 추억을 영상으로 만들었어요",
        "thumbnail_url": video.thumbnail_url,
        "video_url": video.video_url,
        "share_url": f"https://silvertalk.app/videos/{video_id}"
    }


# ============================================================
# 추억 영상 목록 조회
# ============================================================
@router.get("/", response_model=List[VideoResponse], summary="추억 영상 목록 조회")
async def get_videos(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    사용자의 모든 추억 영상 목록 (추억 극장)
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    videos = (
        db.query(GeneratedVideo)
        .filter(GeneratedVideo.user_id == user.id)
        .order_by(GeneratedVideo.created_at.desc())
        .all()
    )
    
    return videos


# ============================================================
# 영상 삭제
# ============================================================
@router.delete("/{video_id}", summary="영상 삭제")
async def delete_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    추억 영상 삭제
    """
    video = db.query(GeneratedVideo).filter(
        GeneratedVideo.id == uuid.UUID(video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")
    
    # S3에서 파일 삭제 (추후 구현)
    
    db.delete(video)
    db.commit()
    
    return {"message": "영상이 삭제되었습니다."}
