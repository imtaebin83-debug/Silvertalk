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

from sqlalchemy import func

from common.database import get_db
from common.models import User, UserPhoto, ChatSession, ChatLog, SessionStatus, SessionPhoto
from common.config import settings

# Worker의 Celery 앱 사용 (EC2와 RunPod 간 설정 일치)
from worker.celery_app import celery_app

def generate_first_greeting(photo, pet_name="복실이"):
    """
    사진 정보를 기반으로 첫 인사 생성
    """
    if not photo:
        return f"안녕하세요! 저는 {pet_name}예요. 오늘 기분이 어떠세요?"
    
    greeting_parts = [f"우와, {pet_name}가 사진을 봤어요!"]
    
    if photo.location_name:
        greeting_parts.append(f"{photo.location_name}에서 찍으셨네요!")
    
    if photo.taken_at:
        # 날짜를 친근하게 표현
        from datetime import datetime
        taken_date = photo.taken_at.date()
        today = datetime.now().date()
        days_diff = (today - taken_date).days
        
        if days_diff == 0:
            time_desc = "오늘"
        elif days_diff == 1:
            time_desc = "어제"
        elif days_diff < 7:
            time_desc = f"{days_diff}일 전"
        elif days_diff < 30:
            weeks = days_diff // 7
            time_desc = f"{weeks}주 전"
        else:
            time_desc = f"{photo.taken_at.strftime('%Y년 %m월 %d일')}"
        
        greeting_parts.append(f"{time_desc}에 찍으신 사진이네요!")
    
    greeting_parts.append("이 사진에 대해 이야기해주세요!")
    
    return " ".join(greeting_parts)

router = APIRouter(prefix="/chat", tags=["대화 서비스 (Chat & Memory)"])


# ============================================================
# 스키마
# ============================================================
class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    kakao_id: Optional[str] = None
    photo_id: Optional[str] = None  # UserPhoto UUID 또는 로컬 asset ID


class CreateSessionResponse(BaseModel):
    """세션 생성 응답 (첫 인사 포함)"""
    session_id: str
    greeting_task_id: Optional[str] = None  # 첫 인사 생성 태스크 ID (polling용)
    ai_reply: Optional[str] = None  # 즉시 반환용 fallback 인사
    turn_count: int
    related_photos: List[dict] = []  # 연관 사진 정보


class ChatSessionResponse(BaseModel):
    id: str
    main_photo_id: Optional[str] = None
    turn_count: int
    is_completed: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_session(cls, session):
        """ChatSession 모델을 응답 스키마로 변환"""
        return cls(
            id=str(session.id),
            main_photo_id=str(session.main_photo_id) if session.main_photo_id else None,
            turn_count=session.turn_count,
            is_completed=session.is_completed,
            status=session.status.value if hasattr(session.status, 'value') else str(session.status),
            created_at=session.created_at
        )


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
@router.post("/sessions", response_model=CreateSessionResponse, summary="대화 세션 시작")
async def start_chat_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db)
):
    """
    사용자가 사진 1장을 선택하면 대화 세션 시작 (첫 인사 포함)

    Flow:
    1. kakao_id로 사용자 확인 (필수)
    2. ChatSession 생성 (photo_id는 optional)
    3. Gemini Vision으로 첫 인사 생성 (비동기 - task_id 반환)
    4. 클라이언트에서 polling으로 결과 확인
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # kakao_id 필수 확인
    if not request.kakao_id:
        raise HTTPException(status_code=400, detail="kakao_id가 필요합니다.")

    # 사용자 조회
    user = db.query(User).filter(User.kakao_id == request.kakao_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # photo_id가 UUID 형식이면 UserPhoto 조회 (optional)
    photo = None
    if request.photo_id:
        try:
            photo_uuid = uuid.UUID(request.photo_id)
            photo = db.query(UserPhoto).filter(UserPhoto.id == photo_uuid).first()
        except ValueError:
            # UUID가 아니면 무시 (로컬 asset ID일 수 있음)
            pass

    # 새 세션 생성
    session = ChatSession(
        user_id=user.id,
        main_photo_id=photo.id if photo else None,
        status=SessionStatus.ACTIVE
    )
    db.add(session)
    db.flush()  # session.id 확보

    pet_name = user.pet_name or "복실이"
    greeting_task_id = None
    fallback_greeting = None
    
    # photo가 있고 s3_url이 있으면 Gemini Vision으로 첫 인사 생성
    if photo and photo.s3_url:
        # Celery 태스크로 첫 인사 생성 (비동기)
        task = celery_app.send_task(
            "worker.tasks.generate_greeting",
            args=[photo.s3_url, pet_name, str(session.id)],
            queue="ai_tasks"
        )
        greeting_task_id = task.id
        logger.info(f"🐕 첫 인사 생성 태스크 시작: task_id={task.id}")
        
        # SessionPhoto 추가 및 조회수 증가
        session_photo = SessionPhoto(
            session_id=session.id,
            photo_id=photo.id,
            s3_url=photo.s3_url,
            display_order=0
        )
        db.add(session_photo)
        photo.view_count += 1
        photo.last_chat_session_id = session.id
    else:
        # photo가 없거나 s3_url이 없으면 기본 인사 반환
        fallback_greeting = f"안녕하세요! 저는 {pet_name}예요. 오늘 기분이 어떠세요? 멍!"
        
        # 기본 인사를 ChatLog에 저장
        greeting_log = ChatLog(
            session_id=session.id,
            role="assistant",
            content=fallback_greeting
        )
        db.add(greeting_log)
        logger.info(f"🐕 기본 인사 사용 (사진 없음)")

    # 연관 사진 추천 (간단 버전)
    related_photos = []
    if photo and photo.taken_at:
        # 같은 날짜 사진 추천
        from datetime import timedelta
        date_from = photo.taken_at - timedelta(days=7)
        date_to = photo.taken_at + timedelta(days=7)
        
        related = (
            db.query(UserPhoto)
            .filter(
                UserPhoto.user_id == user.id,
                UserPhoto.id != photo.id,
                UserPhoto.taken_at.between(date_from, date_to)
            )
            .limit(3)
            .all()
        )
        related_photos = [{"id": str(p.id), "s3_url": p.s3_url} for p in related]

    db.commit()
    db.refresh(session)

    return CreateSessionResponse(
        session_id=str(session.id),
        greeting_task_id=greeting_task_id,
        ai_reply=fallback_greeting,
        turn_count=session.turn_count,
        related_photos=related_photos
    )


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
# 음성 메시지 처리 (STT + Brain)
# ============================================================
@router.post("/messages/voice", summary="음성 메시지 처리")
async def send_voice_message(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    음성 메시지 전송 및 처리 (TTS 제거됨)
    
    Flow:
    1. 음성 파일 저장
    2. Celery 태스크 큐잉 (STT + LLM)
    3. 클라이언트에서 Polling으로 결과 확인
    4. 클라이언트에서 expo-speech로 TTS 재생
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 음성 파일을 S3에 업로드 (RunPod에서 접근 가능하도록)
    import os
    from common.s3_client import S3Client, S3Error
    
    # 임시 로컬 저장 (S3 업로드 전)
    if os.path.exists("/app"):
        data_dir = "/app/data"
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
    
    os.makedirs(data_dir, exist_ok=True)
    audio_filename = f"{session.user_id}_{audio_file.filename}"
    local_audio_path = os.path.join(data_dir, audio_filename)
    
    # 로컬에 임시 저장
    content = await audio_file.read()
    with open(local_audio_path, "wb") as f:
        f.write(content)
    
    print(f"📁 음성 파일 임시 저장: {local_audio_path}")
    
    # S3에 업로드
    try:
        s3_client = S3Client()
        s3_key = f"audio/voice_messages/{session_id}/{audio_filename}"
        s3_url = s3_client.upload_file(
            local_path=local_audio_path,
            s3_key=s3_key,
            content_type="audio/m4a"
        )
        print(f"☁️ S3 업로드 완료: {s3_url}")
    except S3Error as e:
        print(f"❌ S3 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"음성 파일 업로드 실패: {str(e)}")
    finally:
        # 로컬 임시 파일 삭제 (선택적)
        if os.path.exists(local_audio_path):
            os.remove(local_audio_path)
            print(f"🗑️ 임시 파일 삭제: {local_audio_path}")
    
    # 사용자 음성 메시지 ChatLog 저장
    user_log = ChatLog(
        session_id=session.id,
        role="user",
        content="[음성 메시지]"  # STT 결과로 나중에 업데이트됨
    )
    db.add(user_log)
    
    # 턴 수 증가
    session.turn_count += 1
    db.commit()
    
    # Celery 태스크 실행 (S3 URL 전달)
    # 기본 queue 사용 (RunPod worker가 구독 중인 queue)
    task = celery_app.send_task(
        "worker.tasks.process_audio_and_reply",
        args=[s3_url, str(session.user_id), str(session.id)],
        queue="ai_tasks"
    )
    
    return {
        "task_id": task.id,
        "status": "processing",
        "message": "복실이가 듣고 있어요...",
        "turn_count": session.turn_count,
        "can_finish": session.turn_count >= 3
    }


# ============================================================
# AI 응답 저장 (Polling 성공 후 클라이언트에서 호출)
# ============================================================
class SaveAIResponseRequest(BaseModel):
    session_id: str
    user_text: Optional[str] = ""
    ai_reply: str

@router.post("/messages/save-ai-response", summary="AI 응답 저장")
async def save_ai_response(
    request: SaveAIResponseRequest,
    db: Session = Depends(get_db)
):
    """
    Polling 완료 후 AI 응답을 ChatLog에 저장
    
    클라이언트에서 task 결과를 받은 후 호출
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(request.session_id)).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 마지막 사용자 메시지 업데이트 (STT 결과)
    last_user_log = (
        db.query(ChatLog)
        .filter(
            ChatLog.session_id == session.id,
            ChatLog.role == "user"
        )
        .order_by(ChatLog.created_at.desc())
        .first()
    )
    
    if last_user_log and last_user_log.content == "[음성 메시지]":
        last_user_log.content = request.user_text
    
    # AI 응답 저장
    ai_log = ChatLog(
        session_id=session.id,
        role="assistant",
        content=request.ai_reply
    )
    db.add(ai_log)
    db.commit()
    
    return {
        "status": "success",
        "message": "대화가 저장되었습니다."
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
    - turn_count < 3이어도 사진이 있으면 영상 생성 허용 (Polling 실패 케이스 대응)
    """
    session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # turn_count 체크 완화: 사진이 있으면 영상 생성 허용
    session_photos = db.query(SessionPhoto).filter(SessionPhoto.session_id == session.id).count()
    if session.turn_count < 1 and session_photos == 0:
        raise HTTPException(
            status_code=400,
            detail="대화를 시작한 후에 종료할 수 있습니다."
        )
    
    # 세션 완료 처리
    session.is_completed = True
    session.status = SessionStatus.COMPLETED
    
    # 대화 요약 생성 (Gemini)
    # (추후 구현: 모든 ChatLog를 합쳐서 요약)
    logs = db.query(ChatLog).filter(ChatLog.session_id == session.id).all()
    session.summary = "할머니가 손주와 함께 바닷가에 갔던 추억을 이야기했습니다."
    
    db.commit()
    
    # 기억 인사이트 추출 (백그라운드)
    # ChatLog를 dict 형태로 직렬화하여 전달
    chat_logs_serialized = [
        {"role": log.role, "content": log.content}
        for log in logs
    ]
    celery_app.send_task(
        'worker.tasks.extract_memory_insights',
        args=[str(session.id), chat_logs_serialized],
        queue="ai_tasks"
    )
    
    # 영상 생성 요청
    if create_video:
        from common.models import GeneratedVideo, VideoStatus, VideoType

        new_video = GeneratedVideo(
            user_id=session.user_id, # 기존 로직 유지
            session_id=session.id,
            status=VideoStatus.PENDING,
            video_type=VideoType.SLIDESHOW
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        task = celery_app.send_task(
            'worker.tasks.generate_memory_video',
            args=[str(session.id), str(new_video.id), "slideshow"],
            queue="ai_tasks"
        )

        return {
            "success": True,  # 프론트엔드 if(result.success) 체크용 추가
            "message": "대화가 종료되었습니다. 영상을 만들고 있어요!",
            "session_id": str(session.id),
            "video_id": str(new_video.id),      # 프론트엔드가 이 값을 사용함
            "video_task_id": task.id
        }
    
    return {
        "success": True,
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
