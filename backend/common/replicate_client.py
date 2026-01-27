"""
Replicate API 클라이언트
- 이미지 생성: black-forest-labs/flux-schnell
- 영상 생성: christophy/stable-video-diffusion (image-to-video)
"""
import asyncio
import httpx

from .config import settings


# Replicate API 설정
REPLICATE_BASE_URL = "https://api.replicate.com/v1"
REPLICATE_PREDICTIONS_URL = f"{REPLICATE_BASE_URL}/predictions"

# 모델별 엔드포인트 (model 필드 대신 URL에 모델 지정)
FLUX_SCHNELL_URL = f"{REPLICATE_BASE_URL}/models/black-forest-labs/flux-schnell/predictions"
# Stable Video Diffusion (SVD) - 저렴한 이미지→영상 모델
#SVD_URL = f"{REPLICATE_BASE_URL}/models/christophy/stable-video-diffusion/predictions"
SVD_VERSION = "92a0c9a9cb1fd93ea0361d15e499dc879b35095077b2feed47315ccab4524036"


class ReplicateError(Exception):
    """Replicate API 에러"""
    pass


class ReplicateTimeoutError(ReplicateError):
    """Replicate API 타임아웃 에러"""
    pass


def _get_headers() -> dict:
    """API 요청 헤더 반환"""
    if not settings.REPLICATE_API_TOKEN:
        raise ReplicateError("REPLICATE_API_TOKEN 환경변수가 설정되지 않았습니다.")

    return {
        "Authorization": f"Bearer {settings.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait"  # 동기 대기 옵션 (짧은 작업용)
    }


async def _poll_prediction(
    client: httpx.AsyncClient,
    prediction_id: str,
    timeout_seconds: int = 300,
    poll_interval: float = 2.0
) -> dict:
    """
    Prediction 상태를 polling하여 완료될 때까지 대기

    Args:
        client: httpx 클라이언트
        prediction_id: 예측 ID
        timeout_seconds: 최대 대기 시간 (초)
        poll_interval: polling 간격 (초)

    Returns:
        완료된 prediction 응답

    Raises:
        ReplicateTimeoutError: 타임아웃 발생
        ReplicateError: API 에러 또는 예측 실패
    """
    url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}"
    headers = _get_headers()
    elapsed = 0.0

    while elapsed < timeout_seconds:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise ReplicateError(f"상태 조회 실패: {response.status_code} - {response.text}")

        data = response.json()
        status = data.get("status")

        if status == "succeeded":
            return data
        elif status == "failed":
            error = data.get("error", "알 수 없는 에러")
            raise ReplicateError(f"예측 실패: {error}")
        elif status == "canceled":
            raise ReplicateError("예측이 취소되었습니다.")

        # starting, processing 상태면 계속 대기
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise ReplicateTimeoutError(f"타임아웃: {timeout_seconds}초 초과")


async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    num_outputs: int = 1,
    timeout_seconds: int = 120
) -> str:
    """
    Flux-Schnell 모델로 이미지 생성

    Args:
        prompt: 이미지 생성 프롬프트
        aspect_ratio: 이미지 비율 (기본 1:1)
        num_outputs: 생성할 이미지 수 (기본 1)
        timeout_seconds: 타임아웃 (초)

    Returns:
        생성된 이미지 URL

    Raises:
        ReplicateError: API 에러
        ReplicateTimeoutError: 타임아웃
    """
    headers = _get_headers()

    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_outputs": num_outputs,
            "output_format": "webp",
            "output_quality": 90
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Prediction 생성 요청 (모델별 엔드포인트 사용)
        response = await client.post(
            FLUX_SCHNELL_URL,
            headers=headers,
            json=payload
        )

        if response.status_code not in (200, 201):
            raise ReplicateError(f"이미지 생성 요청 실패: {response.status_code} - {response.text}")

        data = response.json()

        # 즉시 완료된 경우 (Prefer: wait 헤더 사용 시)
        if data.get("status") == "succeeded":
            output = data.get("output", [])
            if output:
                return output[0] if isinstance(output, list) else output
            raise ReplicateError("이미지 생성 결과가 없습니다.")

        # 2. Polling으로 완료 대기
        prediction_id = data.get("id")
        if not prediction_id:
            raise ReplicateError("예측 ID를 받지 못했습니다.")

        result = await _poll_prediction(client, prediction_id, timeout_seconds)
        output = result.get("output", [])

        if output:
            return output[0] if isinstance(output, list) else output

        raise ReplicateError("이미지 생성 결과가 없습니다.")


async def generate_video(
    image_url: str,
    prompt: str = "Animate this image with natural, gentle motion",
    aspect_ratio: str = "1:1",
    loop: bool = False,
    timeout_seconds: int = 600,
    # SVD 전용 파라미터
    video_length: str = "25_frames_with_svd_xt",
    frames_per_second: int = 6,
    motion_bucket_id: int = 127,
    cond_aug: float = 0.02
) -> str:
    """
    Stable Video Diffusion (SVD) 모델로 이미지에서 영상 생성

    Args:
        image_url: 입력 이미지 URL 또는 data URI (base64)
        prompt: (SVD에서는 사용되지 않음, 호환성 유지)
        aspect_ratio: (SVD에서는 sizing_strategy로 대체)
        loop: (SVD에서는 사용되지 않음)
        timeout_seconds: 타임아웃 (초, 영상 생성은 오래 걸림)
        video_length: "14_frames_with_svd" 또는 "25_frames_with_svd_xt"
        frames_per_second: 프레임 레이트 (기본 6)
        motion_bucket_id: 모션 강도 (1-255, 기본 127)
        cond_aug: 입력 이미지 노이즈 (기본 0.02)

    Returns:
        생성된 영상 URL

    Raises:
        ReplicateError: API 에러
        ReplicateTimeoutError: 타임아웃
    """
    headers = _get_headers()

    # aspect_ratio를 sizing_strategy로 변환
    sizing_strategy = "maintain_aspect_ratio"
    if aspect_ratio == "16:9":
        sizing_strategy = "crop_to_16_9"

    payload = {
        "version": SVD_VERSION,
        "input": {
            "input_image": image_url,
            "video_length": video_length,
            "frames_per_second": frames_per_second,
            "sizing_strategy": sizing_strategy,
            "motion_bucket_id": motion_bucket_id,
            "cond_aug": cond_aug
        }
    }

    # 타임아웃 설정: 연결 10초, 읽기/쓰기 120초 (base64 이미지 전송 고려)
    timeout_config = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout_config) as client:
        # 1. Prediction 생성 요청 (모델별 엔드포인트 사용)
        response = await client.post(
            #SVD_URL,
            REPLICATE_PREDICTIONS_URL,
            headers=headers,
            json=payload
        )

        if response.status_code not in (200, 201, 202):
            raise ReplicateError(f"영상 생성 요청 실패: {response.status_code} - {response.text}")

        data = response.json()

        # 즉시 완료된 경우 (거의 없음, 영상 생성은 시간 소요)
        if data.get("status") == "succeeded":
            output = data.get("output")
            if output:
                return output if isinstance(output, str) else output[0]
            raise ReplicateError("영상 생성 결과가 없습니다.")

        # 2. Polling으로 완료 대기 (영상은 시간이 오래 걸림)
        prediction_id = data.get("id")
        if not prediction_id:
            raise ReplicateError("예측 ID를 받지 못했습니다.")

        result = await _poll_prediction(
            client,
            prediction_id,
            timeout_seconds,
            poll_interval=5.0  # 영상은 polling 간격을 늘림
        )
        output = result.get("output")

        if output:
            return output if isinstance(output, str) else output[0]

        raise ReplicateError("영상 생성 결과가 없습니다.")


async def get_prediction_status(prediction_id: str) -> dict:
    """
    예측 상태 조회 (디버깅/모니터링용)

    Args:
        prediction_id: 예측 ID

    Returns:
        예측 상태 정보 dict
    """
    headers = _get_headers()
    url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise ReplicateError(f"상태 조회 실패: {response.status_code}")

        return response.json()


async def cancel_prediction(prediction_id: str) -> bool:
    """
    진행 중인 예측 취소

    Args:
        prediction_id: 예측 ID

    Returns:
        취소 성공 여부
    """
    headers = _get_headers()
    url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}/cancel"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers)
        return response.status_code == 200


# ============================================================
# 동기 래퍼 함수 (Celery Worker용)
# ============================================================

def generate_animated_video(
    image_path: str,
    prompt: str = "Animate this image with natural, gentle motion",
    timeout_seconds: int = 600
) -> str:
    """
    이미지를 영상으로 변환 (동기 버전)
    
    Celery Worker에서 사용하기 위한 동기 래퍼 함수.
    내부적으로 asyncio를 사용하여 generate_video()를 호출합니다.
    
    Args:
        image_path: 입력 이미지 파일 경로
        prompt: 영상 생성 프롬프트
        timeout_seconds: 타임아웃 (초)
    
    Returns:
        생성된 영상 URL
    
    Raises:
        ReplicateError: API 에러
        ReplicateTimeoutError: 타임아웃
    
    Example:
        >>> video_url = generate_animated_video("/path/to/image.jpg")
        >>> print(video_url)
        https://replicate.delivery/pbxt/...
    """
    import base64
    
    # 이미지 파일을 읽어서 URL 또는 base64로 변환
    if image_path.startswith("http://") or image_path.startswith("https://"):
        image_url = image_path
    else:
        # 로컬 파일을 base64로 인코딩
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
            # 이미지 형식 감지
            ext = image_path.lower().split(".")[-1]
            mime_type = f"image/{ext}" if ext in ["jpg", "jpeg", "png", "webp"] else "image/jpeg"
            image_url = f"data:{mime_type};base64,{image_data}"
    
    # asyncio 이벤트 루프 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        video_url = loop.run_until_complete(
            generate_video(
                image_url=image_url,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                # SVD 최적 설정
                video_length="25_frames_with_svd_xt",
                frames_per_second=6,
                motion_bucket_id=127,
                cond_aug=0.02
            )
        )
        return video_url
    finally:
        loop.close()
