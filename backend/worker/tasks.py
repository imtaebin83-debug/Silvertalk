"""
Celery AI 처리 태스크
- 동적 디바이스 감지 (CUDA/CPU 자동 전환)
- AI 모델: Faster-Whisper (STT), Gemini (LLM/Vision), Coqui XTTS (TTS)
"""
import os
import logging
from celery import Task
from worker.celery_app import celery_app
from common.config import settings
import torch

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 동적 디바이스 감지
# ============================================================
def detect_device():
    """
    실행 환경에 따라 자동으로 디바이스 선택
    
    Returns:
        device (str): "cuda" 또는 "cpu"
        compute_type (str): "float16" (GPU) 또는 "int8" (CPU)
    """
    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"🚀 GPU 감지: {gpu_name} - CUDA 모드 활성화")
    else:
        device = "cpu"
        compute_type = "int8"
        logger.info("💻 GPU 미감지 - CPU 모드로 실행 (로컬 개발 환경)")
    
    return device, compute_type


# 전역 디바이스 설정
DEVICE, COMPUTE_TYPE = detect_device()

# ============================================================
# AI 모델 전역 변수 (워커 시작 시 한 번만 로드)
# ============================================================

whisper_model = None
tts_model = None
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
    
    # STT: Faster-Whisper 로딩
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            
            # 환경별 모델 경로 자동 설정
            whisper_root = os.path.join(settings.models_root, "whisper")
            os.makedirs(whisper_root, exist_ok=True)
            
            whisper_model = WhisperModel(
                model_size_or_path="large-v3",  # 한국어 성능 최상
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
                download_root=whisper_root
            )
            logger.info(f"✅ Whisper 모델 로딩 완료 (device={DEVICE}, path={whisper_root})")
        except Exception as e:
            logger.error(f"❌ Whisper 로딩 실패: {str(e)}")
            whisper_model = None
    
    # TTS: Coqui XTTS v2 로딩
    if tts_model is None:
        try:
            from TTS.api import TTS
            
            tts_model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False
            ).to(DEVICE)
            logger.info(f"✅ XTTS 모델 로딩 완료 (device={DEVICE})")
        except Exception as e:
            logger.error(f"❌ XTTS 로딩 실패: {str(e)}")
            tts_model = None
    
    # LLM: Gemini 1.5 Flash 초기화
    if gemini_model is None:
        try:
            import google.generativeai as genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("✅ Gemini 1.5 Flash 초기화 완료")
        except Exception as e:
            logger.error(f"❌ Gemini 초기화 실패: {str(e)}")
            gemini_model = None


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
    3. TTS: XTTS로 텍스트 → 음성
    
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
        
        # Step 3: TTS (텍스트 → 음성)
        logger.info(f"[TTS] 음성 합성 시작...")
        output_audio_path = f"/app/data/{user_id}_reply_{self.request.id}.wav"
        synthesize_speech(ai_reply, output_audio_path)
        logger.info(f"[TTS] 음성 합성 완료: {output_audio_path}")
        
        return {
            "status": "success",
            "user_text": user_text,
            "ai_reply": ai_reply,
            "audio_url": output_audio_path
        }
    
    except Exception as e:
        logger.error(f"❌ 음성 처리 실패: {str(e)}")
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
# TTS: Coqui XTTS v2
# ============================================================
def synthesize_speech(text: str, output_path: str, speaker_wav: str = None):
    """
    텍스트를 음성으로 변환
    
    Args:
        text: 합성할 텍스트
        output_path: 출력 음성 파일 경로
        speaker_wav: 목소리 복제용 샘플 (옵션)
    """
    if tts_model is None:
        raise RuntimeError("XTTS 모델이 로딩되지 않았습니다.")
    
    try:
        # 기본 목소리로 생성 (또는 커스텀 목소리 사용 가능)
        tts_model.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav,  # None이면 기본 목소리
            language="ko"
        )
        logger.info(f"TTS 완료: {output_path}")
    
    except Exception as e:
        logger.error(f"TTS 실패: {str(e)}")
        raise


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
    텍스트 입력만으로 AI 답변 생성 (STT/TTS 없이)
    """
    try:
        load_models()
        
        ai_reply = generate_reply(user_text, user_id, session_id)
        
        return {
            "status": "success",
            "user_text": user_text,
            "ai_reply": ai_reply
        }
    
    except Exception as e:
        logger.error(f"텍스트 대화 실패: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# Celery 태스크: 추억 영상 생성
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.generate_memory_video")
def generate_memory_video(self: Task, session_id: str, video_id: str):
    """
    대화 세션을 기반으로 추억 영상 생성
    
    Flow:
    1. ChatSession에서 대화 요약 조회
    2. 삽화 생성 (Replicate/Flux API 또는 원본 사진 활용)
    3. 내레이션 생성 (Coqui XTTS v2)
    4. FFmpeg로 영상 렌더링
    5. S3 업로드
    
    Args:
        session_id: 대화 세션 ID
        video_id: 생성할 영상 ID
    
    Returns:
        dict: 영상 URL 및 상태
    """
    try:
        from common.database import SessionLocal
        from common.models import ChatSession, GeneratedVideo, ChatLog, VideoStatus
        
        db = SessionLocal()
        
        # 세션 조회
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError("세션을 찾을 수 없습니다.")
        
        # 영상 레코드 조회
        video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
        if not video:
            raise ValueError("영상 레코드를 찾을 수 없습니다.")
        
        # 상태 업데이트: PROCESSING
        video.status = VideoStatus.PROCESSING
        db.commit()
        
        # Step 1: 대화 로그 수집
        logger.info(f"[영상 생성] Step 1: 대화 로그 수집 (session_id={session_id})")
        logs = db.query(ChatLog).filter(ChatLog.session_id == session_id).all()
        
        conversation_text = "\n".join([
            f"{'사용자' if log.role == 'user' else '강아지'}: {log.content}"
            for log in logs
        ])
        
        # Step 2: 내레이션 스크립트 생성 (Gemini)
        logger.info(f"[영상 생성] Step 2: 내레이션 스크립트 생성")
        if gemini_model is None:
            load_models()
        
        narration_prompt = f"""다음은 할머니와 반려견 AI의 대화 내용입니다.

{conversation_text}

이 대화를 바탕으로 **손주가 할머니에게 들려주는 따뜻한 내레이션**을 작성해주세요.
2-3문장으로 짧고 감동적으로 작성해주세요.

내레이션:"""
        
        response = gemini_model.generate_content(narration_prompt)
        narration_text = response.text.strip()
        logger.info(f"[영상 생성] 내레이션: {narration_text}")
        
        # Step 3: TTS 내레이션 생성
        logger.info(f"[영상 생성] Step 3: TTS 음성 생성")
        narration_audio_path = f"/app/data/video_{video_id}_narration.wav"
        synthesize_speech(narration_text, narration_audio_path)
        
        # Step 4: FFmpeg로 영상 렌더링 (간단한 버전)
        logger.info(f"[영상 생성] Step 4: 영상 렌더링")
        output_video_path = f"/app/data/video_{video_id}.mp4"
        
        # 원본 사진 경로
        main_photo = session.main_photo
        photo_path = main_photo.s3_url if main_photo else None
        
        if photo_path and photo_path.startswith("http"):
            # S3 URL -> 로컬 다운로드 (추후 구현)
            photo_path = "/app/data/placeholder.jpg"
        
        # FFmpeg 명령어 (사진 + 오디오)
        # (추후 구현: ffmpeg-python 사용)
        # 현재는 placeholder
        
        # Step 5: S3 업로드 (추후 구현)
        logger.info(f"[영상 생성] Step 5: S3 업로드")
        video_url = f"https://s3.amazonaws.com/silvertalk/videos/{video_id}.mp4"
        thumbnail_url = f"https://s3.amazonaws.com/silvertalk/videos/{video_id}_thumb.jpg"
        
        # 영상 레코드 업데이트
        video.video_url = video_url
        video.thumbnail_url = thumbnail_url
        video.status = VideoStatus.COMPLETED
        db.commit()
        
        db.close()
        
        logger.info(f"[영상 생성] ✅ 완료: {video_url}")
        
        return {
            "status": "success",
            "video_id": str(video_id),
            "video_url": video_url,
            "thumbnail_url": thumbnail_url
        }
    
    except Exception as e:
        logger.error(f"[영상 생성] ❌ 실패: {str(e)}")
        
        # 상태 업데이트: FAILED
        try:
            db = SessionLocal()
            video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                db.commit()
            db.close()
        except:
            pass
        
        return {
            "status": "error",
            "message": str(e)
        }
