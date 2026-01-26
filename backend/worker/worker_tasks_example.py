"""
RunPod Worker용 Celery Task 예시
- process_audio: 음성 파일 STT → LLM → TTS 전체 파이프라인
- S3 기반 파일 처리
"""
from celery import Task
from worker.celery_app import celery_app
from worker.s3_utils import download_from_s3, upload_to_s3, cleanup_temp_files
import logging
import uuid

logger = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.process_audio", bind=True)
def process_audio(
    self: Task,
    audio_s3_key: str,
    user_id: str,
    session_id: str,
    reference_voice_s3_key: str = None
) -> dict:
    """
    음성 처리 전체 파이프라인
    
    Flow:
    1. S3에서 사용자 음성 다운로드
    2. Whisper STT 실행
    3. Gemini LLM으로 응답 생성
    4. XTTS TTS로 음성 합성
    5. 결과를 S3에 업로드
    6. 임시 파일 정리
    
    Args:
        audio_s3_key: S3에 저장된 사용자 음성 파일 키
        user_id: 사용자 ID
        session_id: 대화 세션 ID
        reference_voice_s3_key: 참조 음성 파일 (XTTS 학습용, 선택)
    
    Returns:
        dict: {
            "transcription": str,  # STT 결과
            "response_text": str,  # LLM 응답 텍스트
            "response_audio_url": str,  # TTS 결과 S3 URL
            "task_id": str,  # Celery Task ID
            "status": "completed"
        }
    
    메모리 효율성 고려사항:
    - AI 모델은 worker 시작 시 한 번만 로드 (load_models() 함수)
    - 임시 파일은 처리 후 즉시 삭제
    - GPU 메모리는 Task 간 공유 (동시성=1 권장)
    """
    task_id = self.request.id
    logger.info(f"🎯 Task 시작: {task_id} - User: {user_id}, Session: {session_id}")
    
    # 임시 파일 경로
    input_audio_path = f"/tmp/{task_id}_input.wav"
    output_audio_path = f"/tmp/{task_id}_output.wav"
    reference_voice_path = f"/tmp/{task_id}_reference.wav" if reference_voice_s3_key else None
    
    try:
        # ========================================
        # 1. S3에서 파일 다운로드
        # ========================================
        logger.info("📥 Step 1: S3 파일 다운로드")
        download_from_s3(audio_s3_key, input_audio_path)
        
        if reference_voice_s3_key:
            download_from_s3(reference_voice_s3_key, reference_voice_path)
        
        # ========================================
        # 2. Whisper STT 실행
        # ========================================
        # TODO: worker.tasks.load_models()에서 로드된 whisper_model 사용
        # 예시 코드 (실제 구현은 기존 tasks.py 참고):
        #
        # from worker.tasks import whisper_model
        # segments, info = whisper_model.transcribe(
        #     input_audio_path,
        #     language="ko",
        #     beam_size=5
        # )
        # transcription = " ".join([seg.text for seg in segments])
        
        transcription = "[STT 결과 - 실제 구현 필요]"  # Stub
        logger.info(f"✅ Step 2: STT 완료 - '{transcription[:50]}...'")
        
        # ========================================
        # 3. Gemini LLM 응답 생성
        # ========================================
        # TODO: worker.tasks.load_models()에서 초기화된 gemini_model 사용
        # 예시 코드:
        #
        # from worker.tasks import gemini_model
        # prompt = f"사용자: {transcription}\n강아지 역할로 따뜻하게 응답:"
        # response = gemini_model.generate_content(prompt)
        # response_text = response.text
        
        response_text = "[LLM 응답 - 실제 구현 필요]"  # Stub
        logger.info(f"✅ Step 3: LLM 완료 - '{response_text[:50]}...'")
        
        # ========================================
        # 4. XTTS TTS 음성 합성
        # ========================================
        # TODO: worker.tasks.load_models()에서 로드된 tts_model 사용
        # 예시 코드:
        #
        # from worker.tasks import tts_model
        # tts_model.tts_to_file(
        #     text=response_text,
        #     file_path=output_audio_path,
        #     speaker_wav=reference_voice_path,  # 참조 음성 (선택)
        #     language="ko"
        # )
        
        # Stub: 빈 파일 생성
        with open(output_audio_path, "wb") as f:
            f.write(b"")  # 실제로는 TTS 결과 저장
        logger.info(f"✅ Step 4: TTS 완료 - {output_audio_path}")
        
        # ========================================
        # 5. 결과를 S3에 업로드
        # ========================================
        result_s3_key = f"audio/{user_id}/{session_id}/{task_id}_response.wav"
        response_audio_url = upload_to_s3(output_audio_path, result_s3_key)
        logger.info(f"✅ Step 5: S3 업로드 완료 - {response_audio_url}")
        
        # ========================================
        # 6. 임시 파일 정리
        # ========================================
        cleanup_temp_files(
            input_audio_path,
            output_audio_path,
            reference_voice_path
        )
        
        # 성공 결과 반환
        return {
            "transcription": transcription,
            "response_text": response_text,
            "response_audio_url": response_audio_url,
            "task_id": task_id,
            "status": "completed"
        }
    
    except Exception as e:
        logger.error(f"❌ Task 실패: {task_id} - {str(e)}")
        
        # 실패 시에도 임시 파일 정리
        cleanup_temp_files(
            input_audio_path,
            output_audio_path,
            reference_voice_path
        )
        
        # 에러 반환
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e)
        }


# ============================================================
# 모델 로딩 (Worker 시작 시 한 번만 실행)
# ============================================================
# 주의: 이 부분은 기존 worker/tasks.py의 load_models() 함수 참고
# Worker 시작 스크립트에서 호출:
#   celery -A worker.celery_app worker --loglevel=info -E
#
# load_models()는 다음을 수행:
# 1. whisper_model = WhisperModel(...)
# 2. tts_model = TTS(...).to(device)
# 3. gemini_model = genai.GenerativeModel(...)
#
# 메모리 효율성:
# - GPU 24GB 기준: Whisper 3GB + XTTS 1.8GB + 여유 공간
# - concurrency=2로 설정 가능 (동시 2개 Task)
# - concurrency=1 권장 (안정성 우선)
