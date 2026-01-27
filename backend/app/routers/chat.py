"""
대화 서비스 API 라우터
사진 기반 회상 대화
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
from celery import Celery

from sqlalchemy import func

from common.database import get_db
from common.models import User, UserPhoto, ChatSession, ChatLog, SessionStatus, SessionPhoto
from common.config import settings

# Celery 앱 초기화 (Producer용 - Worker tasks 참조만)
# settings.redis_url은 DEPLOYMENT_MODE에 따라 Upstash/Local 자동 선택
celery_app = Celery(
    "silvertalk_worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

router = APIRouter(prefix="/chat", tags=["대화 서비스 (Chat & Memory)"])


# ============================================================
# 스키마
# ============================================================
class ChatSessionResponse(BaseModel):
    id: str
    main_photo_id: Optional[str]
    turn_count: int
    is_completed: bool
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatLogResponse(BaseModel):
    id: int
    role: str
    content: str
    voice_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnimationResponse(BaseModel):
    """강아지 애니메이션"""
    type: str  # "tail_wag", "tilt_head", "roll", "sit"
    message: str


# ============================================================
# 대화 세션 시작
# ============================================================
@router.post("/sessions", response_model=ChatSessionResponse, summary="대화 세션 시작")
async def start_chat_session(
    kakao_id: str,
    photo_id: str,
    db: Session = Depends(get_db)
):
    """
    사용자가 사진 1장을 선택하면 대화 세션 시작
    
    Flow:
    1. ChatSession 생성
    2. UserPhoto의 view_count 증가
    3. Vision AI로 사진 분석 (백그라운드)
    4. 강아지의 첫 질문 생성
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    photo = db.query(UserPhoto).filter(UserPhoto.id == uuid.UUID(photo_id)).first()
    
    if not photo or photo.user_id != user.id:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")
    
    # 새 세션 생성
    session = ChatSession(
        user_id=user.id,
        main_photo_id=photo.id,
        status=SessionStatus.ACTIVE
    )
    db.add(session)
    db.flush()  # session.id 확보

    # SessionPhoto에 메인 사진 추가 (display_order=1)
    session_photo = SessionPhoto(
        session_id=session.id,
        photo_id=photo.id,
        display_order=1
    )
    db.add(session_photo)

    # 사진 조회수 증가
    photo.view_count += 1
    photo.last_chat_session_id = session.id

    db.commit()
    db.refresh(session)
    
    # Vision AI 분석 (비동기)
    if not photo.ai_analysis:
        # Celery 태스크 실행 (이름으로 호출)
        celery_app.send_task(
            "worker.tasks.analyze_image",
            args=[photo.s3_url or "", "이 사진에 대해 간단히 설명해주세요."],
            queue="ai_tasks"
        )
    
    return session


# ============================================================
# 연관 사진 추천 (날짜/장소 기반)
# ============================================================
@router.get("/sessions/next-photos", summary="연관 사진 추천")
async def get_next_photos(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    현재 대화 세션과 연관된 사진 추천 (회상 치료 효과 증대)
    
    추천 알고리즘:
    1. 같은 날짜 범위 (±7일)
    2. 같은 장소
    3. 비슷한 시간대
    
    MVP에서는 날짜 기반 추천만 구현
    """
    from datetime import timedelta
    
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    main_photo = session.main_photo
    
    if not main_photo or not main_photo.taken_at:
        # 날짜 정보 없으면 랜덤 추천
        return (
            db.query(UserPhoto)
            .filter(
                UserPhoto.user_id == session.user_id,
                UserPhoto.id != main_photo.id if main_photo else True
            )
            .order_by(func.random())
            .limit(4)
            .all()
        )
    
    # 같은 날짜 범위 (±7일) 사진 추천
    date_from = main_photo.taken_at - timedelta(days=7)
    date_to = main_photo.taken_at + timedelta(days=7)
    
    related_photos = (
        db.query(UserPhoto)
        .filter(
            UserPhoto.user_id == session.user_id,
            UserPhoto.id != main_photo.id,
            UserPhoto.taken_at.between(date_from, date_to)
        )
        .order_by(
            # 날짜가 가까운 순
            func.abs(
                func.extract('epoch', UserPhoto.taken_at) - 
                func.extract('epoch', main_photo.taken_at)
            )
        )
        .limit(4)
        .all()
    )
    
    # 연관 사진이 부족하면 랜덤 추가
    if len(related_photos) < 4:
        remaining = 4 - len(related_photos)
        random_photos = (
            db.query(UserPhoto)
            .filter(
                UserPhoto.user_id == session.user_id,
                UserPhoto.id != main_photo.id,
                UserPhoto.id.notin_([p.id for p in related_photos])
            )
            .order_by(func.random())
            .limit(remaining)
            .all()
        )
        related_photos.extend(random_photos)
    
    return related_photos


# ============================================================
# 메시지 보내기 (대화)
# ============================================================
@router.post("/messages", summary="메시지 보내기 (대화)")
async def send_message(
    session_id: str,
    audio_file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    사용자가 음성 또는 텍스트 메시지 전송
    
    - 음성: STT → LLM → TTS
    - 텍스트: LLM → TTS
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 사용자 메시지 저장
    user_message = ChatLog(
        session_id=session.id,
        role="user",
        content=text or "[음성 메시지]"
    )
    db.add(user_message)
    
    # 턴 수 증가
    session.turn_count += 1
    db.commit()
    
    # AI 응답 생성 (Celery)
    if audio_file:
        # 음성 파일 저장
        audio_path = f"/app/data/{session.user_id}_{audio_file.filename}"
        with open(audio_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Celery 태스크 실행 (이름으로 호출)
        task = celery_app.send_task(
            "worker.tasks.process_audio_and_reply",
            args=[audio_path, str(session.user_id), str(session.id)],
            queue="ai_tasks"
        )
        
        return {
            "task_id": task.id,
            "status": "processing",
            "message": "AI가 답변을 생성 중입니다...",
            "turn_count": session.turn_count
        }
    
    else:
        # 텍스트 메시지 처리
        # (LLM 응답 생성)
        return {
            "status": "success",
            "message": "텍스트 메시지가 전송되었습니다.",
            "turn_count": session.turn_count
        }


# ============================================================
# 음성 메시지 처리 (STT + Brain + TTS)
# ============================================================
@router.post("/messages/voice", summary="음성 메시지 처리")
async def send_voice_message(
    session_id: str,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    음성 메시지 전송 및 처리
    
    Flow:
    1. STT: 음성 → 텍스트
    2. Brain: Gemini로 대화 생성
    3. TTS: 텍스트 → 음성
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 음성 파일 저장
    audio_path = f"/app/data/{session.user_id}_{audio_file.filename}"
    with open(audio_path, "wb") as f:
        content = await audio_file.read()
        f.write(content)
    
    # Celery 태스크 실행 (이름으로 호출)
    task = celery_app.send_task(
        "worker.tasks.process_audio_and_reply",
        args=[audio_path, str(session.user_id), str(session.id)],
        queue="ai_tasks"
    )
    
    # 턴 수 증가
    session.turn_count += 1
    db.commit()
    
    return {
        "task_id": task.id,
        "status": "processing",
        "message": "AI가 듣고 있어요...",
        "turn_count": session.turn_count
    }


# ============================================================
# 대기 애니메이션 조회
# ============================================================
@router.get("/animations", response_model=AnimationResponse, summary="대기 애니메이션 조회")
async def get_animation():
    """
    STT/LLM 처리 중 보여줄 강아지 애니메이션
    
    - 꼬리 흔들기
    - 갸웃거리기
    - 뒹굴기
    - 앉기
    """
    import random
    
    animations = [
        {"type": "tail_wag", "message": "꼬리 흔들흔들~"},
        {"type": "tilt_head", "message": "음? 뭐라고요?"},
        {"type": "roll", "message": "데굴데굴~"},
        {"type": "sit", "message": "잘 듣고 있어요!"}
    ]
    
    return random.choice(animations)


# ============================================================
# 대화 턴 수 확인
# ============================================================
@router.get("/sessions/{session_id}/turns", summary="대화 턴 수 확인")
async def get_turn_count(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    현재 대화 턴 수 확인
    
    - turn_count < 3: [종료] 버튼 비활성화
    - turn_count >= 3: [종료] 버튼 활성화
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    return {
        "session_id": str(session.id),
        "turn_count": session.turn_count,
        "can_finish": session.turn_count >= 3
    }


# ============================================================
# 대화 종료 및 요약
# ============================================================
@router.patch("/sessions/{session_id}/finish", summary="대화 종료 및 요약")
async def finish_session(
    session_id: str,
    create_video: bool = True,
    db: Session = Depends(get_db)
):
    """
    대화 세션 종료
    
    - 대화 요약 생성 (LLM)
    - create_video=True: 영상 생성 시작
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    if session.turn_count < 3:
        raise HTTPException(
            status_code=400,
            detail="최소 3턴 이상 대화해야 종료할 수 있습니다."
        )
    
    # 세션 완료 처리
    session.is_completed = True
    session.status = SessionStatus.COMPLETED
    
    # 대화 요약 생성 (Gemini)
    # (추후 구현: 모든 ChatLog를 합쳐서 요약)
    logs = db.query(ChatLog).filter(ChatLog.session_id == session.id).all()
    session.summary = "할머니가 손주와 함께 바닷가에 갔던 추억을 이야기했습니다."
    
    db.commit()
    
    # 영상 생성 요청
    if create_video:
        # ✅ EC2에서는 send_task()로 태스크 이름만 전달
        from worker.celery_app import celery_app
        task = celery_app.send_task(
            'worker.tasks.generate_memory_video',
            args=[str(session.id)]
        )
        
        return {
            "message": "대화가 종료되었습니다. 영상을 만들고 있어요!",
            "session_id": str(session.id),
            "video_task_id": task.id
        }
    
    return {
        "message": "대화가 종료되었습니다.",
        "session_id": str(session.id)
    }


# ============================================================
# 전체 대화 목록 조회 (History)
# ============================================================
@router.get("/sessions", response_model=List[ChatSessionResponse], summary="전체 대화 목록 조회")
async def get_chat_sessions(
    kakao_id: str,
    db: Session = Depends(get_db)
):
    """
    사용자의 모든 대화 세션 조회 (마이 페이지용)
    """
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    
    return sessions


# ============================================================
# 대화 상세 기록 조회
# ============================================================
@router.get("/sessions/{session_id}", response_model=List[ChatLogResponse], summary="대화 상세 기록 조회")
async def get_chat_logs(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 세션의 모든 대화 로그 조회
    """
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id == uuid.UUID(session_id))
        .order_by(ChatLog.created_at.asc())
        .all()
    )
    
    return logs


# ============================================================
# 대화 기록 삭제
# ============================================================
@router.delete("/sessions/{session_id}", summary="대화 기록 삭제")
async def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    대화 세션 및 관련 로그 삭제
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    db.delete(session)
    db.commit()
    
    return {"message": "대화 기록이 삭제되었습니다."}


# ============================================================
# 세션에 사진 추가
# ============================================================
@router.post("/sessions/{session_id}/photos", summary="세션에 사진 추가")
async def add_photo_to_session(
    session_id: str,
    photo_id: str,
    db: Session = Depends(get_db)
):
    """
    대화 중 관련 사진을 세션에 추가

    - 사용자가 연관 사진 추천에서 사진을 선택하면 호출
    - 슬라이드쇼 영상 생성 시 이 사진들이 순서대로 사용됨
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id)
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    photo = db.query(UserPhoto).filter(
        UserPhoto.id == uuid.UUID(photo_id)
    ).first()

    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")

    if photo.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 이미 추가된 사진인지 확인
    existing = db.query(SessionPhoto).filter(
        SessionPhoto.session_id == session.id,
        SessionPhoto.photo_id == photo.id
    ).first()

    if existing:
        return {
            "message": "이미 추가된 사진입니다.",
            "session_id": session_id,
            "photo_id": photo_id,
            "display_order": existing.display_order
        }

    # 다음 순서 번호 조회
    max_order = db.query(func.max(SessionPhoto.display_order)).filter(
        SessionPhoto.session_id == session.id
    ).scalar() or 0

    # 사진 추가
    session_photo = SessionPhoto(
        session_id=session.id,
        photo_id=photo.id,
        display_order=max_order + 1
    )
    db.add(session_photo)

    # 사진 조회수 증가
    photo.view_count += 1

    db.commit()

    return {
        "message": "사진이 추가되었습니다.",
        "session_id": session_id,
        "photo_id": photo_id,
        "display_order": session_photo.display_order
    }


# ============================================================
# 세션 사진 목록 조회
# ============================================================
@router.get("/sessions/{session_id}/photos", summary="세션 사진 목록 조회")
async def get_session_photos(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    세션에 사용된 모든 사진 목록 (순서대로)

    - 영상 생성 미리보기에 사용
    - display_order 순서로 슬라이드쇼 생성됨
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id)
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session_photos = (
        db.query(SessionPhoto)
        .filter(SessionPhoto.session_id == session.id)
        .order_by(SessionPhoto.display_order)
        .all()
    )

    return {
        "session_id": session_id,
        "photo_count": len(session_photos),
        "photos": [
            {
                "id": str(sp.photo_id),
                "display_order": sp.display_order,
                "local_uri": sp.photo.local_uri,
                "s3_url": sp.photo.s3_url,
                "taken_at": sp.photo.taken_at.isoformat() if sp.photo.taken_at else None,
                "added_at": sp.added_at.isoformat() if sp.added_at else None
            }
            for sp in session_photos
        ]
    }
