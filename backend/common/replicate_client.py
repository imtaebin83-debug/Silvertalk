"""
Replicate API 클라이언트
- 이미지 생성: black-forest-labs/flux-schnell
- 영상 생성: luma/ray (image-to-video)
"""
import asyncio
import httpx

from .config import settings


# Replicate API 설정
REPLICATE_BASE_URL = "https://api.replicate.com/v1"
REPLICATE_PREDICTIONS_URL = f"{REPLICATE_BASE_URL}/predictions"

# 모델별 엔드포인트 (model 필드 대신 URL에 모델 지정)
FLUX_SCHNELL_URL = f"{REPLICATE_BASE_URL}/models/black-forest-labs/flux-schnell/predictions"
# luma/ray는 deprecated, ray-2-720p 사용
LUMA_RAY_URL = f"{REPLICATE_BASE_URL}/models/luma/ray-2-720p/predictions"


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
    timeout_seconds: int = 600
) -> str:
    """
    Luma Ray 모델로 이미지에서 영상 생성

    Args:
        image_url: 입력 이미지 URL 또는 data URI (base64)
        prompt: 영상 생성 프롬프트 (어떻게 움직일지 설명)
        aspect_ratio: 영상 비율 (1:1, 16:9, 9:16 등)
        loop: 루프 영상 여부
        timeout_seconds: 타임아웃 (초, 영상 생성은 오래 걸림)

    Returns:
        생성된 영상 URL

    Raises:
        ReplicateError: API 에러
        ReplicateTimeoutError: 타임아웃
    """
    headers = _get_headers()

    payload = {
        "input": {
            "prompt": prompt,
            "start_image": image_url,
            "aspect_ratio": aspect_ratio,
            "loop": loop
        }
    }

    # 타임아웃 설정: 연결 10초, 읽기/쓰기 120초 (base64 이미지 전송 고려)
    timeout_config = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout_config) as client:
        # 1. Prediction 생성 요청 (모델별 엔드포인트 사용)
        response = await client.post(
            LUMA_RAY_URL,
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
