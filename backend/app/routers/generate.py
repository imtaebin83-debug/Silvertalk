"""
AI 이미지/영상 생성 API 라우터
- Replicate API를 사용한 독립적인 생성 엔드포인트
- 다른 서비스(채팅, 갤러리 등)에서 재사용 가능
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import logging

from common.auth import get_current_user
from common.models import User
from common.replicate_client import (
    generate_image,
    generate_video,
    get_prediction_status,
    cancel_prediction,
    ReplicateError,
    ReplicateTimeoutError
)

router = APIRouter(prefix="/generate", tags=["Generate"])
logger = logging.getLogger(__name__)


# ============================================================
# 요청/응답 스키마
# ============================================================
class ImageGenerateRequest(BaseModel):
    """이미지 생성 요청"""
    prompt: str = Field(..., description="이미지 생성 프롬프트", min_length=1, max_length=2000)
    aspect_ratio: str = Field(default="1:1", description="이미지 비율 (1:1, 16:9, 9:16, 4:3, 3:4)")
    num_outputs: int = Field(default=1, ge=1, le=4, description="생성할 이미지 수 (1-4)")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A cute golden retriever playing in a sunny park",
                "aspect_ratio": "1:1",
                "num_outputs": 1
            }
        }


class ImageGenerateResponse(BaseModel):
    """이미지 생성 응답"""
    success: bool
    image_url: str
    prompt: str
    message: str = "이미지 생성 완료"


class VideoGenerateRequest(BaseModel):
    """영상 생성 요청"""
    image_url: str = Field(..., description="입력 이미지 URL")
    motion_bucket_id: int = Field(default=127, ge=1, le=255, description="모션 강도 (1-255)")
    fps: int = Field(default=7, ge=1, le=30, description="프레임 레이트")

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/image.png",
                "motion_bucket_id": 127,
                "fps": 7
            }
        }


class VideoGenerateResponse(BaseModel):
    """영상 생성 응답"""
    success: bool
    video_url: str
    source_image_url: str
    message: str = "영상 생성 완료"


class PredictionStatusResponse(BaseModel):
    """예측 상태 응답"""
    id: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    error: str
    detail: Optional[str] = None


# ============================================================
# 이미지 생성 API
# ============================================================
@router.post(
    "/image",
    response_model=ImageGenerateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        401: {"model": ErrorResponse, "description": "인증 필요"},
        500: {"model": ErrorResponse, "description": "서버 에러"},
        504: {"model": ErrorResponse, "description": "타임아웃"}
    },
    summary="AI 이미지 생성"
)
async def generate_image_endpoint(
    request: ImageGenerateRequest,
    user: User = Depends(get_current_user)
):
    """
    Flux-Schnell 모델을 사용해 프롬프트 기반 이미지 생성

    - **prompt**: 생성할 이미지 설명 (영어 권장)
    - **aspect_ratio**: 이미지 비율 (기본 1:1)
    - **num_outputs**: 생성할 이미지 수 (기본 1)

    Returns:
        생성된 이미지 URL
    """
    logger.info(f"이미지 생성 요청 - user: {user.id}, prompt: {request.prompt[:50]}...")

    try:
        image_url = await generate_image(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            num_outputs=request.num_outputs
        )

        logger.info(f"이미지 생성 완료 - user: {user.id}, url: {image_url}")

        return ImageGenerateResponse(
            success=True,
            image_url=image_url,
            prompt=request.prompt,
            message="이미지 생성이 완료되었습니다."
        )

    except ReplicateTimeoutError as e:
        logger.error(f"이미지 생성 타임아웃 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="이미지 생성 시간이 초과되었습니다. 다시 시도해주세요."
        )

    except ReplicateError as e:
        logger.error(f"이미지 생성 실패 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 생성 중 오류가 발생했습니다: {str(e)}"
        )

    except Exception as e:
        logger.error(f"이미지 생성 예외 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 오류가 발생했습니다."
        )


# ============================================================
# 영상 생성 API
# ============================================================
@router.post(
    "/video",
    response_model=VideoGenerateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        401: {"model": ErrorResponse, "description": "인증 필요"},
        500: {"model": ErrorResponse, "description": "서버 에러"},
        504: {"model": ErrorResponse, "description": "타임아웃"}
    },
    summary="AI 영상 생성"
)
async def generate_video_endpoint(
    request: VideoGenerateRequest,
    user: User = Depends(get_current_user)
):
    """
    Stable Video Diffusion 모델을 사용해 이미지에서 영상 생성

    - **image_url**: 입력 이미지 URL (공개 접근 가능해야 함)
    - **motion_bucket_id**: 모션 강도 (1-255, 높을수록 움직임 많음)
    - **fps**: 출력 프레임 레이트

    Returns:
        생성된 영상 URL

    Note:
        영상 생성은 이미지보다 시간이 오래 걸립니다 (약 2-5분).
    """
    logger.info(f"영상 생성 요청 - user: {user.id}, image: {request.image_url}")

    try:
        video_url = await generate_video(
            image_url=request.image_url,
            motion_bucket_id=request.motion_bucket_id,
            fps=request.fps
        )

        logger.info(f"영상 생성 완료 - user: {user.id}, url: {video_url}")

        return VideoGenerateResponse(
            success=True,
            video_url=video_url,
            source_image_url=request.image_url,
            message="영상 생성이 완료되었습니다."
        )

    except ReplicateTimeoutError as e:
        logger.error(f"영상 생성 타임아웃 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="영상 생성 시간이 초과되었습니다. 다시 시도해주세요."
        )

    except ReplicateError as e:
        logger.error(f"영상 생성 실패 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"영상 생성 중 오류가 발생했습니다: {str(e)}"
        )

    except Exception as e:
        logger.error(f"영상 생성 예외 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 오류가 발생했습니다."
        )


# ============================================================
# 이미지 + 영상 한번에 생성 (편의 API)
# ============================================================
class FullGenerateRequest(BaseModel):
    """이미지+영상 통합 생성 요청"""
    prompt: str = Field(..., description="이미지 생성 프롬프트")
    aspect_ratio: str = Field(default="1:1", description="이미지 비율")
    motion_bucket_id: int = Field(default=127, ge=1, le=255, description="영상 모션 강도")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A cute golden retriever playing in a sunny park",
                "aspect_ratio": "1:1",
                "motion_bucket_id": 127
            }
        }


class FullGenerateResponse(BaseModel):
    """이미지+영상 통합 생성 응답"""
    success: bool
    image_url: str
    video_url: str
    prompt: str
    message: str = "이미지와 영상 생성 완료"


@router.post(
    "/full",
    response_model=FullGenerateResponse,
    summary="이미지 + 영상 통합 생성"
)
async def generate_full_endpoint(
    request: FullGenerateRequest,
    user: User = Depends(get_current_user)
):
    """
    프롬프트로 이미지를 생성하고, 해당 이미지로 영상까지 자동 생성

    1. 프롬프트 → 이미지 생성 (Flux-Schnell)
    2. 이미지 → 영상 생성 (Stable Video Diffusion)

    Note:
        전체 과정에 약 3-7분 소요될 수 있습니다.
    """
    logger.info(f"통합 생성 요청 - user: {user.id}, prompt: {request.prompt[:50]}...")

    try:
        # 1. 이미지 생성
        image_url = await generate_image(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio
        )
        logger.info(f"이미지 생성 완료 - url: {image_url}")

        # 2. 영상 생성
        video_url = await generate_video(
            image_url=image_url,
            motion_bucket_id=request.motion_bucket_id
        )
        logger.info(f"영상 생성 완료 - url: {video_url}")

        return FullGenerateResponse(
            success=True,
            image_url=image_url,
            video_url=video_url,
            prompt=request.prompt,
            message="이미지와 영상 생성이 완료되었습니다."
        )

    except ReplicateTimeoutError as e:
        logger.error(f"통합 생성 타임아웃 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="생성 시간이 초과되었습니다."
        )

    except ReplicateError as e:
        logger.error(f"통합 생성 실패 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"생성 중 오류가 발생했습니다: {str(e)}"
        )


# ============================================================
# 유틸리티 API (상태 조회, 취소)
# ============================================================
@router.get(
    "/status/{prediction_id}",
    response_model=PredictionStatusResponse,
    summary="생성 작업 상태 조회"
)
async def get_status_endpoint(
    prediction_id: str,
    user: User = Depends(get_current_user)
):
    """
    Replicate 예측 작업의 상태 조회

    Status 값:
    - starting: 시작 중
    - processing: 처리 중
    - succeeded: 완료
    - failed: 실패
    - canceled: 취소됨
    """
    try:
        result = await get_prediction_status(prediction_id)

        return PredictionStatusResponse(
            id=result.get("id", prediction_id),
            status=result.get("status", "unknown"),
            output=result.get("output"),
            error=result.get("error")
        )

    except ReplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"예측 작업을 찾을 수 없습니다: {str(e)}"
        )


@router.post(
    "/cancel/{prediction_id}",
    summary="생성 작업 취소"
)
async def cancel_endpoint(
    prediction_id: str,
    user: User = Depends(get_current_user)
):
    """
    진행 중인 Replicate 예측 작업 취소
    """
    try:
        success = await cancel_prediction(prediction_id)

        if success:
            return {"success": True, "message": "작업이 취소되었습니다."}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="작업 취소에 실패했습니다."
            )

    except ReplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
