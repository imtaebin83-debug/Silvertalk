"""
Celery AI 처리 태스크 (TTS 제거 버전)
- 동적 디바이스 감지 (CUDA/CPU 자동 전환)
- AI 모델: Faster-Whisper (STT), Gemini (LLM)
- TTS는 클라이언트 expo-speech로 대체
- CUDA 충돌 방지: Lazy 초기화 + 명시적 .env 로드
"""

# ============================================================
# 최우선: .env 로드 (GEMINI_API_KEY 등)
# ============================================================
from dotenv import load_dotenv
load_dotenv()

import os
import logging
import traceback
import soundfile as sf
from celery import Task
from worker.celery_app import celery_app
from common.config import settings
from common.image_utils import preprocess_image_for_ai, ImageProcessingError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 동적 디바이스 감지 (Lazy 초기화)
# ============================================================
_device_cache = None
DEVICE = None
COMPUTE_TYPE = None

def detect_device():
    """
    실행 환경에 따라 자동으로 디바이스 선택
    Worker fork 이후에 호출되어야 CUDA 충돌 방지
    
    Returns:
        tuple: (device, compute_type)
    """
    global _device_cache, DEVICE, COMPUTE_TYPE
    
    if _device_cache is not None:
        return _device_cache
    
    # torch는 함수 내부에서 import (Worker fork 이후)
    try:
        import torch
        
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"  # Whisper용
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"🚀 GPU 감지: {gpu_name} - CUDA 모드 활성화")
        else:
            device = "cpu"
            compute_type = "int8"
            logger.info("💻 GPU 미감지 - CPU 모드로 실행")
        
        _device_cache = (device, compute_type)
        DEVICE = device
        COMPUTE_TYPE = compute_type
        return _device_cache
    
    except Exception as e:
        logger.error(f"❌ 디바이스 감지 실패: {str(e)}, CPU로 fallback")
        _device_cache = ("cpu", "int8")
        DEVICE = "cpu"
        COMPUTE_TYPE = "int8"
        return _device_cache


# ============================================================
# AI 모델 전역 변수 (워커 시작 시 한 번만 로드)
# ============================================================
whisper_model = None
# tts_model = None  # TTS 제거 (시간 절약)
gemini_model = None


# ============================================================
# 모델 로딩 함수
# ============================================================
def load_models():
    """
    AI 모델 초기화 (워커 시작 시 한 번만 실행)
    
    에러 처리:
    - 모델 로딩 실패 시에도 워커가 죽지 않도록 try-except 사용
    """
    global whisper_model, tts_model, gemini_model
    
    # 디바이스 감지 (첫 실행)
    device, compute_type = detect_device()
    logger.info(f"🔧 디바이스 설정: device={device}, compute_type={compute_type}")
    
    # STT: Faster-Whisper 로딩
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            
            # RunPod Volume 경로 사용 (영구 저장)
            whisper_root = os.path.join(settings.models_root, "whisper")
            os.makedirs(whisper_root, exist_ok=True)
            
            logger.info(f"[Whisper] 모델 로딩 시작... (경로: {whisper_root})")
            # medium: 1.5GB, 한국어 정확도 95%+ (large-v3 대비 약간 하락하지만 충분)
            whisper_model = WhisperModel(
                model_size_or_path="medium",
                device=device,
                compute_type=compute_type,
                download_root=whisper_root
            )
            logger.info(f"✅ Whisper 모델 로딩 완료 (model=medium, device={device}, path={whisper_root})")
        except Exception as e:
            logger.error(f"❌ Whisper 로딩 실패: {str(e)}")
            logger.error(traceback.format_exc())
            whisper_model = None
    
    # TTS: 제거 (시간 절약, API로 대체 예정)
    # logger.info("⚠️ TTS 비활성화 - 텍스트 응답만 제공")
    
    # LLM: Gemini 1.5 Flash 초기화
    if gemini_model is None:
        try:
            import google.generativeai as genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            genai.configure(api_key=api_key)
            # 최신 안정 버전 사용 (API 키 재발급 후 gemini-1.5-flash로 변경 가능)
            gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")
            logger.info("✅ Gemini 1.5 Flash 초기화 완료")
        except Exception as e:
            logger.error(f"❌ Gemini 초기화 실패: {str(e)}")
            logger.error(traceback.format_exc())
            gemini_model = None


# ============================================================
# Celery 태스크: AI 모델 사전 로드
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.preload_models")
def preload_models(self: Task):
    """
    AI 모델 사전 로드 (Whisper, Qwen3-TTS, Gemini)
    
    첫 태스크 실행 전에 이 task를 실행하면 모델을 미리 다운로드할 수 있습니다.
    
    Returns:
        dict: 각 모델의 로딩 상태
    """
    try:
        logger.info("🚀 AI 모델 사전 로드 시작...")
        
        load_models()
        
        # 각 모델 로딩 상태 확인
        status = {
            "whisper": "loaded" if whisper_model is not None else "failed",
            "gemini": "loaded" if gemini_model is not None else "failed",
        }
        
        # 모델 저장 경로 확인
        import subprocess
        models_info = subprocess.run(
            ['du', '-sh', f'{settings.models_root}/*'],
            capture_output=True,
            text=True
        )
        
        logger.info("✅ AI 모델 사전 로드 완료!")
        logger.info(f"   모델 상태: {status}")
        logger.info(f"   저장 경로: {settings.models_root}")
        
        return {
            "status": "success",
            "models": status,
            "storage_info": models_info.stdout,
            "message": "모든 모델 로드 완료"
        }
    
    except Exception as e:
        logger.error(f"❌ 모델 사전 로드 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# Celery 태스크: 음성 대화 처리 (STT + Brain + TTS)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.process_audio_and_reply")
def process_audio_and_reply(self: Task, audio_path: str, user_id: str, session_id: str = None):
    """
    음성 파일을 받아 AI 대화 처리
    
    Flow:
    1. STT: Faster-Whisper로 음성 → 텍스트
    2. Brain: Gemini로 대화 생성
    3. TTS: Qwen3-TTS로 텍스트 → 음성
    
    Args:
        audio_path: 업로드된 음성 파일 경로
        user_id: 사용자 ID
        session_id: 대화 세션 ID (옵션)
    
    Returns:
        dict: {
            "user_text": 사용자 음성 텍스트,
            "ai_reply": AI 답변 텍스트,
            "audio_url": TTS 생성 음성 파일 경로
        }
    """
    try:
        # 모델 로딩 (첫 실행 시에만)
        load_models()
        
        # Step 1: STT (음성 → 텍스트)
        logger.info(f"[STT] 음성 인식 시작: {audio_path}")
        user_text = transcribe_audio(audio_path)
        logger.info(f"[STT] 인식 결과: {user_text}")
        
        # Step 2: Brain (Gemini로 대화 생성)
        logger.info(f"[Brain] AI 답변 생성 중...")
        ai_reply = generate_reply(user_text, user_id, session_id)
        logger.info(f"[Brain] AI 답변: {ai_reply}")
        
        # Step 3: 감정 분석 (클라이언트 애니메이션 연동)
        sentiment = analyze_sentiment(ai_reply)
        logger.info(f"[완료] 텍스트 응답 생성 완료 (sentiment={sentiment})")
        
        return {
            "status": "success",
            "user_text": user_text,
            "ai_reply": ai_reply,
            "sentiment": sentiment,
            "session_id": session_id  # 클라이언트에서 DB 저장용
        }
    
    except Exception as e:
        logger.error(f"❌ 음성 처리 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# STT: Faster-Whisper
# ============================================================
def transcribe_audio(audio_path: str) -> str:
    """
    음성 파일을 텍스트로 변환
    
    Args:
        audio_path: 오디오 파일 경로
    
    Returns:
        str: 인식된 텍스트
    """
    if whisper_model is None:
        raise RuntimeError("Whisper 모델이 로딩되지 않았습니다.")
    
    try:
        segments, info = whisper_model.transcribe(
            audio_path,
            language="ko",  # 한국어
            beam_size=5,
            vad_filter=True  # Voice Activity Detection
        )
        
        # 세그먼트 결합
        text = " ".join([segment.text for segment in segments])
        return text.strip()
    
    except Exception as e:
        logger.error(f"STT 실패: {str(e)}")
        return ""


# ============================================================
# Brain: Gemini 1.5 Flash
# ============================================================
def generate_reply(user_text: str, user_id: str, session_id: str = None) -> str:
    """
    사용자 입력에 대한 AI 답변 생성
    
    Args:
        user_text: 사용자 입력 텍스트
        user_id: 사용자 ID
        session_id: 대화 세션 ID
    
    Returns:
        str: AI 답변
    """
    if gemini_model is None:
        raise RuntimeError("Gemini 모델이 초기화되지 않았습니다.")
    
    try:
        # 회상 치료 프롬프트
        prompt = f"""당신은 노인 회상 치료를 돕는 친근한 AI 상담사입니다.

사용자 말: {user_text}

다음 가이드라인을 따라 답변하세요:
1. 따뜻하고 공감하는 어조로 대화하세요.
2. 과거 기억을 떠올릴 수 있는 질문을 포함하세요.
3. 2-3문장으로 간결하게 답변하세요.
4. 존댓말을 사용하세요.

답변:"""
        
        response = gemini_model.generate_content(prompt)
        ai_reply = response.text.strip()
        
        return ai_reply
    
    except Exception as e:
        logger.error(f"Gemini 답변 생성 실패: {str(e)}")
        return "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다."


# ============================================================
# 감정 분석 (애니메이션 연동용)
# ============================================================
def analyze_sentiment(text: str) -> str:
    """
    AI 답변의 감정을 분석하여 강아지 애니메이션 결정
    
    Args:
        text: AI 답변 텍스트
    
    Returns:
        str: "happy" | "curious" | "nostalgic" | "excited" | "comforting"
    """
    # 키워드 기반 감정 분석
    happy_keywords = ["좋", "기뻐", "행복", "웃", "재밌", "신나", "멋지"]
    curious_keywords = ["뭐", "어디", "누구", "언제", "왜", "어떻게", "?"]
    nostalgic_keywords = ["추억", "옛날", "그때", "기억", "예전", "어릴", "오래"]
    excited_keywords = ["와", "우와", "대박", "정말", "진짜", "!"]
    
    text_lower = text.lower()
    
    # 우선순위: curious > nostalgic > excited > happy > comforting
    for kw in curious_keywords:
        if kw in text_lower:
            return "curious"
    for kw in nostalgic_keywords:
        if kw in text_lower:
            return "nostalgic"
    for kw in excited_keywords:
        if kw in text_lower:
            return "excited"
    for kw in happy_keywords:
        if kw in text_lower:
            return "happy"
    
    return "comforting"  # 기본값: 따뜻한 위로


# ============================================================
# Celery 태스크: 이미지 분석 (Gemini Vision)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.analyze_image")
def analyze_image(self: Task, image_path: str, prompt: str):
    """
    이미지를 Gemini Vision으로 분석
    
    Args:
        image_path: 이미지 파일 경로
        prompt: 분석 요청 프롬프트
    
    Returns:
        dict: 분석 결과
    """
    try:
        load_models()
        
        if gemini_model is None:
            raise RuntimeError("Gemini 모델이 초기화되지 않았습니다.")
        
        # 이미지 로딩
        from PIL import Image
        image = Image.open(image_path)
        
        # Gemini Vision 분석
        response = gemini_model.generate_content([prompt, image])
        
        return {
            "status": "success",
            "analysis": response.text.strip()
        }
    
    except Exception as e:
        logger.error(f"이미지 분석 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# Celery 태스크: 텍스트 전용 대화 (테스트용)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.generate_reply_from_text")
def generate_reply_from_text(self: Task, user_text: str, user_id: str, session_id: str = None):
    """
    텍스트 입력으로 AI 답변 생성 + TTS 음성 합성
    """
    try:
        load_models()
        
        # Gemini로 답변 생성
        ai_reply = generate_reply(user_text, user_id, session_id)
        
        # 감정 분석
        sentiment = analyze_sentiment(ai_reply)
        logger.info(f"✅ AI 답변 생성 완료: {ai_reply[:50]}... (sentiment={sentiment})")
        
        return {
            "status": "success",
            "user_text": user_text,
            "ai_reply": ai_reply,
            "sentiment": sentiment,
            "session_id": session_id,
            "gemini_response": ai_reply  # 테스트 스크립트 호환
        }
    
    except Exception as e:
        logger.error(f"텍스트 대화 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# Celery 태스크: 추억 영상 생성
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.generate_memory_video")
def generate_memory_video(
    self: Task,
    session_id: str,
    video_id: str,
    video_type: str = "slideshow"
):
    """
    대화 세션을 기반으로 추억 영상 생성

    Flow:
    1. SessionPhoto에서 사진 목록 조회
    2. 내레이션 스크립트 생성 (Gemini)
    3. TTS 내레이션 생성 (Qwen3-TTS)
    4. 영상 생성 (slideshow: FFmpeg / ai_animated: Replicate SVD)
    5. S3 업로드

    Args:
        session_id: 대화 세션 ID
        video_id: 생성할 영상 ID
        video_type: "slideshow" (FFmpeg) 또는 "ai_animated" (Replicate SVD)

    Returns:
        dict: 영상 URL 및 상태
    """
    db = None
    temp_files = []  # 정리할 임시 파일들

    try:
        from common.database import SessionLocal
        from common.models import (
            ChatSession, GeneratedVideo, ChatLog, VideoStatus,
            SessionPhoto, VideoType
        )
        from worker.ffmpeg_client import generate_slideshow, get_video_duration
        from common.s3_client import upload_video, download_image

        db = SessionLocal()

        # 세션 조회
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        # 영상 레코드 조회
        video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
        if not video:
            raise ValueError(f"영상 레코드를 찾을 수 없습니다: {video_id}")

        # 상태 업데이트: PROCESSING
        video.status = VideoStatus.PROCESSING
        db.commit()

        # ============================================================
        # Step 1: 사진 수집
        # ============================================================
        logger.info(f"[영상 생성] Step 1: 사진 수집 (session_id={session_id})")

        # SessionPhoto 테이블에서 순서대로 조회
        session_photos = (
            db.query(SessionPhoto)
            .filter(SessionPhoto.session_id == session_id)
            .order_by(SessionPhoto.display_order)
            .all()
        )

        # SessionPhoto가 없으면 main_photo로 fallback
        if not session_photos:
            if not session.main_photo:
                raise ValueError("세션에 사진이 없습니다.")
            photo_records = [type('obj', (object,), {'photo_url': session.main_photo})]
        else:
            photo_records = session_photos

        # 사진 다운로드 및 전처리
        local_photo_paths = []
        for i, photo in enumerate(photo_records):
            try:
                # S3에서 다운로드
                photo_url = photo.photo_url
                local_path = f"/app/data/photo_{video_id}_{i}.jpg"
                temp_files.append(local_path)
                
                download_image(photo_url, local_path)
                
                # 이미지 전처리 (리사이즈, 포맷 통일)
                processed_path = f"/app/data/photo_{video_id}_{i}_processed.jpg"
                temp_files.append(processed_path)
                
                preprocess_image_for_ai(
                    local_path,
                    processed_path,
                    target_size=(1920, 1080),  # Full HD
                    quality=95
                )
                
                local_photo_paths.append(processed_path)
                logger.info(f"   사진 {i+1}/{len(photo_records)} 준비 완료")
                
            except Exception as e:
                logger.error(f"   사진 {i+1} 처리 실패: {str(e)}")
                continue

        if not local_photo_paths:
            raise ValueError("처리 가능한 사진이 없습니다.")

        logger.info(f"[영상 생성] {len(local_photo_paths)}장 사진 다운로드 완료")

        # ============================================================
        # Step 2: 대화 로그 수집 및 내레이션 생성
        # ============================================================
        logger.info(f"[영상 생성] Step 2: 내레이션 스크립트 생성")

        logs = db.query(ChatLog).filter(ChatLog.session_id == session_id).all()
        conversation_text = "\n".join([
            f"{'사용자' if log.role == 'user' else '강아지'}: {log.content}"
            for log in logs
        ])

        if gemini_model is None:
            load_models()

        photo_count = len(local_photo_paths)
        narration_prompt = f"""다음은 할머니와 반려견 AI의 대화 내용입니다.

{conversation_text}

이 대화를 바탕으로 **손주가 할머니에게 들려주는 따뜻한 내레이션**을 작성해주세요.
{photo_count}장의 사진이 슬라이드쇼로 보여질 예정입니다.
전체 3-5문장으로 따뜻하고 감동적으로 작성해주세요.

내레이션:"""

        response = gemini_model.generate_content(narration_prompt)
        narration_text = response.text.strip()
        logger.info(f"[영상 생성] 내레이션: {narration_text[:100]}...")

        # ============================================================
        # Step 3: 배경음악 설정 (TTS 제거됨)
        # ============================================================
        logger.info(f"[영상 생성] Step 3: 배경음악 설정 (TTS 제거)")
        # BGM 파일이 없으면 무음으로 처리
        bgm_path = os.path.join(settings.models_root, "bgm", "emotional_bgm.mp3")
        if os.path.exists(bgm_path):
            narration_audio_path = bgm_path
            logger.info(f"[영상 생성] BGM 사용: {bgm_path}")
        else:
            narration_audio_path = None
            logger.warning(f"[영상 생성] BGM 파일 없음, 무음으로 생성")

        # ============================================================
        # Step 4: 영상 생성
        # ============================================================
        logger.info(f"[영상 생성] Step 4: 영상 렌더링 (type={video_type})")
        output_video_path = f"/app/data/video_{video_id}.mp4"
        temp_files.append(output_video_path)

        if video_type == "slideshow":
            # FFmpeg 슬라이드쇼 생성
            generate_slideshow(
                image_paths=local_photo_paths,
                audio_path=narration_audio_path,  # BGM 또는 None
                output_path=output_video_path,
                duration_per_image=4.0  # 사진당 4초 (어르신 시청 고려)
            )
        else:
            # Replicate SVD 애니메이션 (기존 로직)
            from common.replicate_client import generate_animated_video
            
            svd_outputs = []
            for img_path in local_photo_paths:
                video_url = generate_animated_video(img_path)
                svd_outputs.append(video_url)
            
            # 영상 병합 + 오디오 추가
            from worker.ffmpeg_client import merge_videos_with_audio
            merge_videos_with_audio(
                video_paths=svd_outputs,
                audio_path=narration_audio_path,
                output_path=output_video_path
            )

        # ============================================================
        # Step 5: S3 업로드
        # ============================================================
        logger.info(f"[영상 생성] Step 5: S3 업로드")

        video_url, thumbnail_url = upload_video(
            output_video_path,
            str(session.user_id),
            str(video_id)
        )

        # 영상 길이 조회
        duration = get_video_duration(output_video_path)

        # ============================================================
        # Step 6: DB 업데이트
        # ============================================================
        video.video_url = video_url
        video.thumbnail_url = thumbnail_url
        video.status = VideoStatus.COMPLETED
        video.video_type = VideoType(video_type)
        video.duration_seconds = duration
        db.commit()

        logger.info(f"[영상 생성] ✅ 완료: {video_url} ({duration:.1f}초)")

        return {
            "status": "success",
            "video_id": str(video_id),
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "duration_seconds": duration
        }

    except Exception as e:
        logger.error(f"[영상 생성] ❌ 실패: {str(e)}")
        logger.error(traceback.format_exc())

        # 상태 업데이트: FAILED
        if db and video:
            try:
                video.status = VideoStatus.FAILED
                db.commit()
            except:
                pass

        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        # 임시 파일 정리
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        if db:
            db.close()