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
from common.image_utils import preprocess_image_for_ai, preprocess_image_file, ImageProcessingError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# Type Safety Layer: 응답 포맷 검증 헬퍼
# ============================================================
def format_response(required_keys: list, data: dict, schema_name: str = "UnknownSchema") -> dict:
    """
    Celery 태스크 반환값 검증 및 포맷팅
    
    Args:
        required_keys: 필수 필드 목록
        data: 반환할 데이터 딕셔너리
        schema_name: 스키마 이름 (디버깅용)
    
    Returns:
        dict: 검증된 응답 딕셔너리
    
    Raises:
        ValueError: 필수 키가 없는 경우
    """
    # 모든 UUID 필드를 문자열로 변환
    for key in ["session_id", "user_id", "video_id", "task_id"]:
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    
    # status는 소문자로 통일
    if "status" in data:
        data["status"] = str(data["status"]).lower()
    
    # 필수 키 검증
    missing_keys = [k for k in required_keys if k not in data]
    if missing_keys:
        logger.warning(f"[{schema_name}] 누락된 필드: {missing_keys}")
        # 누락된 필드에 기본값 설정
        for key in missing_keys:
            if key == "status":
                data[key] = "error"
            elif key == "message":
                data[key] = "Unknown error"
            else:
                data[key] = ""
    
    logger.debug(f"[{schema_name}] 검증 완료: {list(data.keys())}")
    return data

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
            
            # CUDA 시도 (cuDNN + libcublas 라이브러리 사전 체크)
            if device == "cuda":
                try:
                    # CUDA 필수 라이브러리 사전 체크
                    import ctypes
                    
                    # 1. cuDNN 체크
                    try:
                        ctypes.CDLL("libcudnn_ops_infer.so.8")
                        logger.info("✅ cuDNN 라이브러리 확인 완료")
                    except OSError as e:
                        raise Exception(f"cuDNN 라이브러리 누락: {e}")
                    
                    # 2. libcublas 체크 (CUDA 11.x 또는 12.x)
                    cublas_found = False
                    cublas_version = None
                    for cublas_ver in ["libcublas.so.12", "libcublas.so.11"]:
                        try:
                            ctypes.CDLL(cublas_ver)
                            logger.info(f"✅ {cublas_ver} 확인 완료")
                            cublas_found = True
                            cublas_version = cublas_ver
                            break
                        except OSError:
                            continue
                    
                    if not cublas_found:
                        raise Exception("libcublas 라이브러리 누락 (11 또는 12 버전 필요)")
                    
                    # libcublas.so.12가 필요한데 .11만 있는 경우 경고
                    if cublas_version == "libcublas.so.11":
                        logger.warning("⚠️ CTranslate2가 libcublas.so.12를 요구할 수 있습니다")
                        logger.warning("⚠️ 실패 시 심볼릭 링크 생성: ln -sf libcublas.so.11 libcublas.so.12")
                    
                    # 라이브러리 체크 통과 → Whisper 모델 로딩
                    whisper_model = WhisperModel(
                        model_size_or_path="medium",
                        device=device,
                        compute_type=compute_type,
                        download_root=whisper_root
                    )
                    logger.info(f"✅ Whisper 모델 로딩 완료 (model=medium, device={device}, path={whisper_root})")
                
                except Exception as cuda_error:
                    logger.warning(f"⚠️ CUDA 라이브러리 체크 실패: {cuda_error}")
                    logger.warning("⚠️ CPU 모드로 강제 전환")
                    whisper_model = WhisperModel(
                        model_size_or_path="medium",
                        device="cpu",
                        compute_type="int8",
                        download_root=whisper_root
                    )
                    logger.info(f"✅ Whisper 모델 로딩 완료 (model=medium, device=cpu, path={whisper_root})")
            
            else:
                # CPU 모드 직접 로딩
                whisper_model = WhisperModel(
                    model_size_or_path="medium",
                    device="cpu",
                    compute_type="int8",
                    download_root=whisper_root
                )
                logger.info(f"✅ Whisper 모델 로딩 완료 (model=medium, device=cpu, path={whisper_root})")
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
            # gemini-2.0-flash (최신 버전, quota 제한 주의)
            # gemini-2.0-flash-exp (실험 버전, quota 제한 심함)
            gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("✅ Gemini 2.0 Flash 초기화 완료")
        except Exception as e:
            logger.error(f"❌ Gemini 초기화 실패: {str(e)}")
            logger.error(traceback.format_exc())
            gemini_model = None


# ============================================================
# S3에서 음성 파일 다운로드
# ============================================================
def download_audio_from_s3(s3_url: str, user_id: str) -> str:
    """
    S3 URL에서 음성 파일 다운로드
    
    Args:
        s3_url: S3 URL (https://bucket.s3.region.amazonaws.com/key)
        user_id: 사용자 ID (임시 파일명용)
    
    Returns:
        str: 로컬 파일 경로
    """
    import tempfile
    import urllib.request
    import ssl
    
    # SSL 컨텍스트 (인증서 검증)
    ssl_context = ssl.create_default_context()
    
    # 임시 파일 경로 생성
    temp_dir = tempfile.gettempdir()
    local_path = os.path.join(temp_dir, f"audio_{user_id}_{os.getpid()}.m4a")
    
    try:
        logger.info(f"S3 다운로드: {s3_url} -> {local_path}")
        
        # URL로 직접 다운로드 (S3 public URL 가정)
        urllib.request.urlretrieve(s3_url, local_path)
        
        # 파일 존재 확인
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"다운로드 파일 없음: {local_path}")
        
        file_size = os.path.getsize(local_path)
        logger.info(f"S3 다운로드 완료: {file_size} bytes")
        
        return local_path
        
    except Exception as e:
        logger.error(f"S3 다운로드 실패: {str(e)}")
        raise RuntimeError(f"S3 음성 파일 다운로드 실패: {str(e)}")


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
# Celery 태스크: 음성 대화 처리 (STT + Brain + Summary-Buffer Memory)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.process_audio_and_reply")
def process_audio_and_reply(
    self: Task,
    audio_url: str,
    user_id: str,
    session_id: str = None,
    summary: str = "",
    recent_logs: list = None,
    turn_count: int = 0
):
    """
    음성 파일을 받아 AI 대화 처리 (Summary-Buffer Memory 적용)
    
    Flow:
    1. S3에서 음성 파일 다운로드
    2. STT: Faster-Whisper로 음성 → 텍스트
    3. Brain: 요약 + 최근 대화 컨텍스트로 Gemini 응답 생성
    4. 매 3턴마다 대화 요약 업데이트
    
    Args:
        audio_url: S3 URL (EC2에서 업로드됨)
        user_id: 사용자 ID
        session_id: 대화 세션 ID
        summary: 현재까지의 대화 요약 (Summary-Buffer Memory)
        recent_logs: 최근 대화 로그 [{"role": "user"|"assistant", "content": "..."}]
        turn_count: 현재 대화 턴 수
    
    Returns:
        dict: {
            "status": "success",
            "user_text": 사용자 음성 텍스트,
            "ai_reply": AI 답변 텍스트,
            "sentiment": 감정,
            "new_summary": 업데이트된 요약 (3턴마다),
            "session_id": 세션 ID
        }
    """
    if recent_logs is None:
        recent_logs = []
    
    try:
        # 모델 로딩 (첫 실행 시에만)
        load_models()
        
        # S3에서 음성 파일 다운로드
        logger.info(f"[S3] 음성 파일 다운로드 시작: {audio_url}")
        local_audio_path = download_audio_from_s3(audio_url, user_id)
        logger.info(f"[S3] 다운로드 완료: {local_audio_path}")
        
        # Step 1: STT (음성 → 텍스트)
        logger.info(f"[STT] 음성 인식 시작: {local_audio_path}")
        user_text = transcribe_audio(local_audio_path)
        logger.info(f"[STT] 인식 결과: {user_text}")
        
        # 다운로드한 임시 파일 삭제
        try:
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)
                logger.info(f"[S3] 임시 파일 삭제: {local_audio_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패 (무시): {e}")
        
        # Step 2: Brain (Summary-Buffer Memory 적용한 Gemini 응답 생성)
        logger.info(f"[Brain] AI 답변 생성 중... (턴 수: {turn_count})")
        reply_data = generate_reply_with_memory(
            user_text=user_text,
            summary=summary,
            recent_logs=recent_logs,
            turn_count=turn_count
        )
        ai_reply = reply_data["text"]
        sentiment = reply_data["sentiment"]
        new_summary = reply_data.get("new_summary")
        
        logger.info(f"[Brain] AI 답변: {ai_reply[:50]}... (sentiment={sentiment})")
        if new_summary:
            logger.info(f"[Memory] 요약 업데이트: {new_summary[:50]}...")
        
        # AudioChatResult 스키마에 맞게 반환
        result = {
            "status": "success",
            "user_text": user_text,
            "ai_reply": ai_reply,
            "sentiment": sentiment,
            "session_id": session_id
        }
        
        # 요약이 업데이트된 경우에만 추가
        if new_summary:
            result["new_summary"] = new_summary
        
        return format_response(
            required_keys=["status", "user_text", "ai_reply", "sentiment", "session_id"],
            data=result,
            schema_name="AudioChatResult"
        )
    
    except Exception as e:
        logger.error(f"❌ 음성 처리 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return format_response(
            required_keys=["status", "message"],
            data={
                "status": "error",
                "message": str(e)
            },
            schema_name="AudioChatResult"
        )



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
# Brain: Summary-Buffer Memory 적용 응답 생성
# ============================================================
def generate_reply_with_memory(
    user_text: str,
    summary: str = "",
    recent_logs: list = None,
    turn_count: int = 0
) -> dict:
    """
    Summary-Buffer Memory를 적용한 AI 답변 생성
    
    Args:
        user_text: 사용자 입력 텍스트
        summary: 현재까지의 대화 요약
        recent_logs: 최근 대화 로그 [{"role": "...", "content": "..."}]
        turn_count: 현재 대화 턴 수
    
    Returns:
        dict: {"text": "답변", "sentiment": "...", "new_summary": "..."(옵션)}
    """
    if recent_logs is None:
        recent_logs = []
    
    # Fallback 응답
    FALLBACK_RESPONSE = {
        "text": "할머니, 제가 잘 못 들었어요. 다시 말씀해 주시겠어요? 멍!",
        "sentiment": "curious"
    }
    
    if gemini_model is None:
        logger.error("Gemini 모델이 초기화되지 않았습니다.")
        return FALLBACK_RESPONSE
    
    try:
        # 최근 대화 컨텍스트 구성
        recent_context = ""
        if recent_logs:
            recent_context = "\n".join([
                f"{'사용자' if log['role'] == 'user' else 'AI'}: {log['content']}"
                for log in recent_logs
                if log.get('content')
            ])
        
        # 요약 업데이트 필요 여부 (매 3턴마다)
        should_update_summary = (turn_count > 0) and (turn_count % 3 == 0)
        
        # 프롬프트 구성
        if should_update_summary:
            # 응답 + 요약 업데이트 동시 요청 (기존 요약 MERGE)
            prompt = f"""
당신은 노인 회상 치료를 돕는 친근한 AI 상담사 '복실이'입니다.

[기존 대화 요약]
{summary if summary else "(첫 대화입니다)"}

[최근 대화 내용]
{recent_context if recent_context else "(이전 대화 없음)"}

[현재 사용자 말]
{user_text}

**AI 답변 지침:**
1. 따뜻하고 공감하는 어조로 대화하세요.
2. 과거 기억을 떠올릴 수 있는 질문을 포함하세요.
3. 2-3문장으로 간결하게 답변하세요.
4. 존댓말을 사용하세요.
5. 가끔 "멍!" 또는 "왈왈!"을 붙여주세요.

**요약 업데이트 지침 (중요!):**
- [기존 대화 요약]에 있는 핵심 정보(음식, 장소, 사람, 추억 등)를 절대 삭제하지 마세요.
- [최근 대화 내용]과 [현재 사용자 말]에서 새롭게 알게 된 사실을 기존 요약에 통합하세요.
- 3인칭 시점으로 서술하세요 (예: "사용자는 ...라고 말했다").
- 4-5문장으로 누적된 전체 대화 내용을 요약하세요.

**중요: 반드시 아래의 JSON 형식만 출력하세요. 다른 텍스트 없이 JSON만!**

{{
    "text": "AI 답변 (2-3문장)",
    "sentiment": "happy|sad|curious|excited|nostalgic|comforting",
    "new_summary": "[기존 요약]과 [새로운 정보]를 합친 누적 요약 (4-5문장, 정보 누락 금지)"
}}
"""
        else:
            # 일반 응답만
            prompt = f"""
당신은 노인 회상 치료를 돕는 친근한 AI 상담사 '복실이'입니다.

[이전 대화 요약]
{summary if summary else "(첫 대화입니다)"}

[최근 대화 내용]
{recent_context if recent_context else "(이전 대화 없음)"}

[현재 사용자 말]
{user_text}

아래 지침을 반드시 따르세요:
1. 따뜻하고 공감하는 어조로 대화하세요.
2. 과거 기억을 떠올릴 수 있는 질문을 포함하세요.
3. 2-3문장으로 간결하게 답변하세요.
4. 존댓말을 사용하세요.
5. 가끔 "멍!" 또는 "왈왈!"을 붙여주세요.

**중요: 반드시 아래의 JSON 형식만 출력하세요. 다른 텍스트 없이 JSON만!**

{{
    "text": "AI 답변 (2-3문장)",
    "sentiment": "happy|sad|curious|excited|nostalgic|comforting"
}}
"""
        
        # Gemini API 호출 (Retry 로직)
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = gemini_model.generate_content(prompt)
                break
            except Exception as api_error:
                error_str = str(api_error)
                if "429" in error_str or "quota" in error_str.lower():
                    retry_count += 1
                    import re
                    retry_match = re.search(r'retry in (\d+)', error_str)
                    retry_delay = int(retry_match.group(1)) if retry_match else 10
                    
                    if retry_count < max_retries:
                        logger.warning(f"⚠️ Gemini Quota 초과, {retry_delay}초 후 재시도 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        logger.error("❌ Gemini Quota 초과, 최대 재시도 횟수 도달")
                        return FALLBACK_RESPONSE
                else:
                    raise api_error
        
        # 응답 파싱
        if response and response.text:
            import json
            import re
            
            response_text = response.text.strip()
            
            # 코드블록 제거
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            
            # { ... } 패턴 추출
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            try:
                ai_reply = json.loads(response_text)
                
                if "text" in ai_reply and "sentiment" in ai_reply:
                    logger.info(f"[Memory] 답변 성공: {ai_reply['text'][:50]}...")
                    return ai_reply
                else:
                    logger.warning("Gemini 응답에 필수 필드 누락")
                    return FALLBACK_RESPONSE
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {e}")
                return {
                    "text": response.text.strip()[:200],
                    "sentiment": "comforting"
                }
        else:
            return FALLBACK_RESPONSE
    
    except Exception as e:
        logger.error(f"Summary-Buffer Memory 답변 생성 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return FALLBACK_RESPONSE


# ============================================================
# Brain: Gemini 1.5 Flash (Legacy - 기존 호환용)
# ============================================================
def generate_reply(user_text: str, user_id: str, session_id: str = None) -> dict:
    """
    사용자 입력에 대한 AI 답변 생성 (JSON 형식 반환)
    
    Args:
        user_text: 사용자 입력 텍스트
        user_id: 사용자 ID
        session_id: 대화 세션 ID
    
    Returns:
        dict: {"text": "답변내용", "sentiment": "happy|sad|curious|comforting"}
    """
    # Safety Fallback 응답
    FALLBACK_RESPONSE = {
        "text": "할머니, 제가 잘 못 들었어요. 다시 말씀해 주시겠어요? 멍!",
        "sentiment": "curious"
    }
    
    if gemini_model is None:
        logger.error("Gemini 모델이 초기화되지 않았습니다.")
        return FALLBACK_RESPONSE
    
    try:
        # 회상 치료 프롬프트 (JSON 강제)
        prompt = f"""
당신은 노인 회상 치료를 돕는 친근한 AI 상담사 '복실이'입니다.

사용자 말: {user_text}

아래 지침을 반드시 따르세요:
1. 따뜻하고 공감하는 어조로 대화하세요.
2. 과거 기억을 떠올릴 수 있는 질문을 포함하세요.
3. 2-3문장으로 간결하게 답변하세요.
4. 존댓말을 사용하세요.
5. 가끔 "멍!" 또는 "왈왈!"을 붙여주세요.

**중요: 반드시 아래의 JSON 형식만, 코드블록 없이, 다른 텍스트(설명, 인사, 안내 등) 없이, 예시 그대로, 한글로만 답변하세요.**
예시:
{{
    "text": "답변 내용",
    "sentiment": "happy|sad|curious|excited|nostalgic|comforting"
}}

오직 위 JSON만 출력하세요. 다른 텍스트, 마크다운, 설명, 인사, 안내, 코드블록, 공백 등은 절대 포함하지 마세요.
"""
        
        # Gemini API 호출 (Retry 로직 추가)
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = gemini_model.generate_content(prompt)
                break  # 성공 시 루프 탈출
            
            except Exception as api_error:
                error_str = str(api_error)
                
                # Quota 초과 에러 처리
                if "429" in error_str or "quota" in error_str.lower():
                    retry_count += 1
                    
                    # Retry delay 추출 (에러 메시지에서)
                    import re
                    retry_match = re.search(r'retry in (\d+)', error_str)
                    retry_delay = int(retry_match.group(1)) if retry_match else 10
                    
                    if retry_count < max_retries:
                        logger.warning(f"⚠️ Gemini Quota 초과, {retry_delay}초 후 재시도 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"❌ Gemini Quota 초과, 최대 재시도 횟수 도달")
                        return FALLBACK_RESPONSE
                else:
                    # 다른 에러는 즉시 Fallback
                    raise api_error
        
        # 응답 파싱
        if response and response.text:
            import json
            import re
            
            # JSON 추출 (마크다운 코드블록 처리)
            response_text = response.text.strip()
            
            # ```json ... ``` 또는 ``` ... ``` 패턴 제거
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            
            # { ... } 패턴 추출
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            try:
                ai_reply = json.loads(response_text)
                
                # 필수 필드 확인
                if "text" in ai_reply and "sentiment" in ai_reply:
                    logger.info(f"Gemini 답변 성공: {ai_reply['text'][:50]}...")
                    return ai_reply
                else:
                    logger.warning("Gemini 응답에 필수 필드 누락, Fallback 사용")
                    return FALLBACK_RESPONSE
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {e}, 원본: {response_text[:100]}")
                # JSON 파싱 실패 시 텍스트를 직접 사용
                return {
                    "text": response.text.strip()[:200],
                    "sentiment": "comforting"
                }
        else:
                logger.warning("Gemini 응답에 필수 필드 누락, Fallback 사용")
                return FALLBACK_RESPONSE
    
    except Exception as e:
        logger.error(f"Gemini 답변 생성 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return FALLBACK_RESPONSE


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
# Celery 태스크: 사진 기반 첫 인사 생성 (Gemini Vision)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.generate_greeting")
def generate_greeting(self: Task, image_url: str, pet_name: str = "복실이", session_id: str = None):
    """
    사진을 분석하여 맞춤형 첫 인사 생성
    
    Args:
        image_url: S3 URL 또는 로컬 이미지 경로
        pet_name: 반려견 이름 (기본: 복실이)
        session_id: 세션 ID
    
    Returns:
        GreetingTaskResult 스키마:
        {
            "status": "success",
            "ai_greeting": "인사 메시지",
            "analysis": "이미지 분석 요약",
            "session_id": "uuid-string"
        }
    """
    # 스키마 필수 필드
    REQUIRED_KEYS = ["status", "ai_greeting", "session_id"]
    
    # Fallback 응답
    def fallback_response(message: str = None):
        return format_response(
            required_keys=REQUIRED_KEYS,
            data={
                "status": "success",
                "ai_greeting": message or f"안녕하세요! 저는 {pet_name}예요. 사진이 참 좋아 보여요! 오늘 기분이 어떠세요? 멍!",
                "analysis": None,
                "session_id": session_id
            },
            schema_name="GreetingTaskResult"
        )
    
    try:
        load_models()
        
        if gemini_model is None:
            logger.error("Gemini 모델이 초기화되지 않았습니다.")
            return fallback_response()
        
        # 이미지 다운로드 (S3 URL인 경우)
        local_image_path = None
        image_analysis = None
        
        try:
            if image_url.startswith("http"):
                import tempfile
                import urllib.request
                
                temp_dir = tempfile.gettempdir()
                local_image_path = os.path.join(temp_dir, f"greeting_{session_id or 'temp'}_{os.getpid()}.jpg")
                
                logger.info(f"[Greeting] 이미지 다운로드: {image_url}")
                urllib.request.urlretrieve(image_url, local_image_path)
            else:
                local_image_path = image_url
            
            if not os.path.exists(local_image_path):
                raise FileNotFoundError(f"이미지 파일 없음: {local_image_path}")
            
            # 이미지 로딩
            from PIL import Image
            image = Image.open(local_image_path)
            logger.info(f"[Greeting] 이미지 로딩 완료: {image.size}")
            
        except Exception as img_error:
            logger.warning(f"[Greeting] 이미지 로딩 실패: {img_error}, Fallback 사용")
            return fallback_response()
        
        # Gemini Vision으로 사진 분석 및 인사 생성 (2단계)
        # Step 1: 이미지 분석
        analysis_prompt = "이 사진에서 보이는 장소, 인물, 상황을 간단히 설명해주세요. 50자 이내로 답변하세요."
        try:
            analysis_response = gemini_model.generate_content([analysis_prompt, image])
            if analysis_response and analysis_response.text:
                image_analysis = analysis_response.text.strip()[:100]
                logger.info(f"[Greeting] 이미지 분석: {image_analysis}")
        except Exception as e:
            logger.warning(f"[Greeting] 이미지 분석 실패: {e}")
            image_analysis = "사진 분석 실패"
        
        # Step 2: 인사 생성
        greeting_prompt = f"""
당신은 노인 회상 치료를 돕는 친근한 AI 반려견 '{pet_name}'입니다.
사용자가 보여준 사진을 보고, 따뜻하고 친근한 첫 인사를 해주세요.

규칙:
1. 사진에서 보이는 내용(장소, 인물, 상황 등)을 자연스럽게 언급하세요.
2. 호기심이 가득한 강아지처럼 질문을 포함하세요.
3. 2-3문장으로 간결하게 말하세요.
4. 존댓말을 사용하고, 가끔 "멍!" 또는 "왈왈!"을 붙여주세요.
5. 할머니/할아버지가 듣기 좋은 따뜻한 어조를 사용하세요.

**중요: JSON 없이 순수 인사 텍스트만 출력하세요.**
"""
        
        try:
            response = gemini_model.generate_content([greeting_prompt, image])
            
            if response and response.text:
                ai_greeting = response.text.strip()
                
                # JSON 형식이 포함된 경우 텍스트만 추출
                import json
                import re
                
                # JSON 패턴 제거 시도
                json_match = re.search(r'\{[^{}]*"text"\s*:\s*"([^"]+)"', ai_greeting)
                if json_match:
                    ai_greeting = json_match.group(1)
                else:
                    # 코드블록 제거
                    ai_greeting = re.sub(r'```.*?```', '', ai_greeting, flags=re.DOTALL)
                    ai_greeting = ai_greeting.strip()
                
                # 200자 제한
                ai_greeting = ai_greeting[:200]
                
                logger.info(f"[Greeting] 생성 완료: {ai_greeting[:50]}...")
                
                return format_response(
                    required_keys=REQUIRED_KEYS,
                    data={
                        "status": "success",
                        "ai_greeting": ai_greeting,
                        "analysis": image_analysis,
                        "session_id": session_id
                    },
                    schema_name="GreetingTaskResult"
                )
            
            return fallback_response()
            
        except Exception as api_error:
            logger.error(f"[Greeting] Gemini API 오류: {api_error}")
            return fallback_response()
        
        finally:
            # 임시 파일 정리
            if local_image_path and local_image_path != image_url:
                try:
                    if os.path.exists(local_image_path):
                        os.remove(local_image_path)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"[Greeting] 첫 인사 생성 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return format_response(
            required_keys=["status", "message", "session_id"],
            data={
                "status": "failure",
                "message": f"이미지를 분석할 수 없습니다: {str(e)}",
                "session_id": session_id
            },
            schema_name="GreetingTaskResult"
        )


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
        
        # Gemini로 답변 생성 (JSON 반환)
        reply_data = generate_reply(user_text, user_id, session_id)
        ai_reply = reply_data["text"]
        sentiment = reply_data["sentiment"]
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
# Celery 태스크: 기억 인사이트 추출 (Memory Insight Extraction)
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.extract_memory_insights")
def extract_memory_insights(self: Task, session_id: str, chat_logs: list):
    """
    대화 내용에서 의미 있는 기억을 추출
    
    Args:
        session_id: 대화 세션 ID (문자열)
        chat_logs: 대화 로그 리스트 [{"role": "user"|"assistant", "content": "..."}]
    
    Returns:
        InsightTaskResult 스키마:
        {
            "status": "success",
            "session_id": "...",
            "insights": [
                {"category": "family", "fact": "손주와 함께...", "importance": 4},
                ...
            ]
        }
    """
    # 스키마 필수 필드
    REQUIRED_KEYS = ["status", "session_id", "insights"]
    VALID_CATEGORIES = ["family", "travel", "food", "hobby", "emotion", "other"]
    
    try:
        load_models()
        
        if gemini_model is None:
            logger.error("[Insight] Gemini 모델이 초기화되지 않았습니다.")
            return format_response(
                required_keys=REQUIRED_KEYS,
                data={
                    "status": "failure",
                    "session_id": session_id,
                    "insights": [],
                    "error": "Gemini 모델 초기화 실패"
                },
                schema_name="InsightTaskResult"
            )
        
        # 빈 대화 로그 체크
        if not chat_logs or len(chat_logs) == 0:
            logger.warning(f"[Insight] 세션 {session_id}의 대화 로그가 비어있습니다.")
            return format_response(
                required_keys=REQUIRED_KEYS,
                data={
                    "status": "success",
                    "session_id": session_id,
                    "insights": []
                },
                schema_name="InsightTaskResult"
            )
        
        # 대화 로그를 텍스트로 변환
        conversation_text = "\n".join([
            f"{'사용자' if log['role'] == 'user' else 'AI'}: {log['content']}"
            for log in chat_logs
            if log.get('content')
        ])
        
        logger.info(f"[Insight] 대화 분석 시작 (세션: {session_id}, 로그 수: {len(chat_logs)})")
        
        # Gemini 프롬프트 (회상 요법 전문가 역할)
        insight_prompt = f"""
당신은 노인 회상 치료(Reminiscence Therapy) 전문가입니다.
아래 대화에서 사용자가 언급한 의미 있는 기억과 감정을 추출해주세요.

**규칙:**
1. 단순한 인사나 "네", "아니오" 같은 답변은 무시하세요.
2. 사용자가 언급한 장소, 인물, 음식, 취미, 감정 등 구체적인 내용만 추출하세요.
3. 각 기억에 대해 중요도(1-5)를 평가하세요:
   - 5: 매우 중요 (가족 이야기, 특별한 추억)
   - 4: 중요 (여행, 이벤트)
   - 3: 보통 (취미, 일상적 활동)
   - 2: 낮음 (일반적인 선호)
   - 1: 매우 낮음 (사소한 언급)
4. 추출된 사실(fact)은 한국어로 자연스러운 문장으로 작성하세요.
5. 카테고리: family, travel, food, hobby, emotion, other

**중요: 반드시 아래 JSON 배열 형식만 출력하세요. 다른 텍스트는 절대 포함하지 마세요.**

예시:
[
    {{"category": "family", "fact": "손주 민수와 함께 공원에서 놀았다", "importance": 5}},
    {{"category": "travel", "fact": "부산 해운대에서 바다를 봤다", "importance": 4}}
]

의미 있는 기억이 없으면 빈 배열 []을 반환하세요.

---
대화 내용:
{conversation_text}
"""
        
        try:
            response = gemini_model.generate_content(insight_prompt)
            
            if response and response.text:
                import json
                import re
                
                response_text = response.text.strip()
                logger.info(f"[Insight] Gemini 응답: {response_text[:200]}...")
                
                # JSON 배열 추출
                # 코드블록 제거
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                # 배열 패턴 매칭
                array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if array_match:
                    response_text = array_match.group(0)
                
                try:
                    insights_raw = json.loads(response_text)
                    
                    # 유효성 검증 및 정제
                    insights = []
                    for item in insights_raw:
                        if isinstance(item, dict) and "category" in item and "fact" in item:
                            # 카테고리 검증
                            category = item["category"].lower()
                            if category not in VALID_CATEGORIES:
                                category = "other"
                            
                            # 중요도 검증 (1-5 범위)
                            importance = int(item.get("importance", 3))
                            importance = max(1, min(5, importance))
                            
                            insights.append({
                                "category": category,
                                "fact": str(item["fact"]),
                                "importance": importance
                            })
                    
                    logger.info(f"[Insight] 추출 완료: {len(insights)}개 인사이트")
                    
                    return format_response(
                        required_keys=REQUIRED_KEYS,
                        data={
                            "status": "success",
                            "session_id": session_id,
                            "insights": insights
                        },
                        schema_name="InsightTaskResult"
                    )
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"[Insight] JSON 파싱 실패: {e}")
                    return format_response(
                        required_keys=REQUIRED_KEYS,
                        data={
                            "status": "failure",
                            "session_id": session_id,
                            "insights": [],
                            "error": f"JSON 파싱 실패: {str(e)}"
                        },
                        schema_name="InsightTaskResult"
                    )
            
            # 응답이 없는 경우
            return format_response(
                required_keys=REQUIRED_KEYS,
                data={
                    "status": "success",
                    "session_id": session_id,
                    "insights": []
                },
                schema_name="InsightTaskResult"
            )
            
        except Exception as api_error:
            logger.error(f"[Insight] Gemini API 오류: {api_error}")
            return format_response(
                required_keys=REQUIRED_KEYS,
                data={
                    "status": "failure",
                    "session_id": session_id,
                    "insights": [],
                    "error": str(api_error)
                },
                schema_name="InsightTaskResult"
            )
    
    except Exception as e:
        logger.error(f"[Insight] 기억 인사이트 추출 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return format_response(
            required_keys=["status", "session_id", "error"],
            data={
                "status": "failure",
                "session_id": session_id,
                "insights": [],
                "error": str(e)
            },
            schema_name="InsightTaskResult"
        )


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
    video = None
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
            # main_photo는 UserPhoto 객체이므로 s3_url 속성이 있음
            # 하지만 안전을 위해 dummy 객체도 s3_url로 통일
            photo_records = [type('obj', (object,), {'s3_url': session.main_photo.s3_url if hasattr(session.main_photo, 's3_url') else str(session.main_photo)})]
        else:
            photo_records = session_photos

        # 사진 다운로드 및 전처리
        local_photo_paths = []
        for i, photo in enumerate(photo_records):
            try:
                # S3에서 다운로드
                photo_url = photo.s3_url
                local_path = f"/tmp/photo_{video_id}_{i}.jpg"
                temp_files.append(local_path)
                
                download_image(photo_url, local_path)
                
                # 이미지 전처리 (리사이즈, 포맷 통일)
                processed_path = f"/tmp/photo_{video_id}_{i}_processed.jpg"
                temp_files.append(processed_path)

                # 파일 기반 전처리 함수 사용 (preprocess_image_file)
                preprocess_image_file(
                    local_path,
                    processed_path,
                    target_size=(1920, 1080),  # Full HD
                    jpeg_quality=95
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
        output_video_path = f"/tmp/video_{video_id}.mp4"
        temp_files.append(output_video_path)

        if video_type == "slideshow":
            # FFmpeg 슬라이드쇼 생성
            generate_slideshow(
                image_paths=local_photo_paths,
                audio_path=narration_audio_path,  # BGM 또는 None
                output_path=output_video_path,
                duration_per_slide=4.0  # 사진당 4초 (어르신 시청 고려)
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


# ============================================================
# Celery 태스크: 기억 인사이트 추출
# ============================================================
@celery_app.task(bind=True, name="worker.tasks.extract_memory_insights")
def extract_memory_insights(self: Task, session_id: str):
    """
    대화 종료 시 기억 인사이트 추출 (백그라운드)
    
    Args:
        session_id: 대화 세션 ID
    """
    from common.database import get_db_session
    from common.models import ChatSession, ChatLog, MemoryInsight
    
    db = None
    try:
        db = get_db_session()
        
        # 세션 조회
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            logger.warning(f"세션 없음: {session_id}")
            return
        
        # 모든 대화 로그 조회
        logs = db.query(ChatLog).filter(ChatLog.session_id == session_id).order_by(ChatLog.created_at).all()
        
        if not logs:
            logger.info(f"대화 로그 없음: {session_id}")
            return
        
        # 대화 내용 합치기
        conversation_text = "\n".join([f"{log.role}: {log.content}" for log in logs])
        
        # Gemini로 기억 인사이트 추출
        prompt = f"""
다음은 노인과 AI 강아지의 대화 내용입니다. 이 대화에서 추출할 수 있는 중요한 기억 정보를 찾아주세요.

대화 내용:
{conversation_text}

다음 형식으로 JSON으로 응답해주세요:
{{
  "insights": [
    {{
      "category": "family|travel|food|hobby|etc",
      "fact": "추출된 사실",
      "importance": 1-5
    }}
  ]
}}

주의:
- category는 family, travel, food, hobby 중 하나
- fact는 구체적인 사실만
- importance는 1(낮음)에서 5(높음)
"""
        
        # 모델 로딩
        load_models()
        if gemini_model is None:
            logger.error("Gemini 모델 로딩 실패")
            return
        
        response = gemini_model.generate_content(prompt)
        
        if response and response.text:
            import json
            import re
            
            # JSON 파싱
            response_text = response.text.strip()
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            
            try:
                data = json.loads(response_text)
                insights = data.get("insights", [])
                
                # DB 저장
                for insight in insights:
                    memory_insight = MemoryInsight(
                        user_id=session.user_id,
                        category=insight["category"],
                        fact=insight["fact"],
                        importance=insight["importance"],
                        source_log_id=logs[-1].id if logs else None  # 마지막 로그
                    )
                    db.add(memory_insight)
                
                db.commit()
                logger.info(f"기억 인사이트 추출 완료: {len(insights)}개")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
        
    except Exception as e:
        logger.error(f"기억 인사이트 추출 실패: {str(e)}")
        logger.error(traceback.format_exc())
    
    finally:
        if db:
            db.close()