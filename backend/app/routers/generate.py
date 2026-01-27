"""
AI 이미지/영상 생성 API 라우터
- Replicate API를 사용한 독립적인 생성 엔드포인트
- 다른 서비스(채팅, 갤러리 등)에서 재사용 가능
"""
import base64
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
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
from common.image_utils import (
    preprocess_image_for_ai,
    validate_image,
    ImageProcessingError
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
    prompt: str = Field(default="Animate this image with natural, gentle motion", description="영상 생성 프롬프트")
    aspect_ratio: str = Field(default="1:1", description="영상 비율 (1:1, 16:9, 9:16)")
    loop: bool = Field(default=False, description="루프 영상 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/image.png",
                "prompt": "A dog running happily in slow motion",
                "aspect_ratio": "1:1",
                "loop": False
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
    Stable Video Diffusion (SVD) 모델을 사용해 이미지에서 영상 생성

    - **image_url**: 입력 이미지 URL (공개 접근 가능해야 함)
    - **prompt**: (현재 SVD에서는 사용되지 않음)
    - **aspect_ratio**: 영상 비율
    - **loop**: (현재 SVD에서는 사용되지 않음)

    Returns:
        생성된 영상 URL

    Note:
        영상 생성은 이미지보다 시간이 오래 걸립니다 (약 1-3분).
    """
    logger.info(f"영상 생성 요청 - user: {user.id}, image: {request.image_url}")

    try:
        video_url = await generate_video(
            image_url=request.image_url,
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            loop=request.loop
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
# 이미지 업로드 → 영상 생성 API
# ============================================================
class VideoFromUploadResponse(BaseModel):
    """이미지 업로드 → 영상 생성 응답"""
    success: bool
    video_url: str
    message: str = "영상 생성 완료"


@router.post(
    "/video/upload",
    response_model=VideoFromUploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 이미지"},
        401: {"model": ErrorResponse, "description": "인증 필요"},
        500: {"model": ErrorResponse, "description": "서버 에러"},
        504: {"model": ErrorResponse, "description": "타임아웃"}
    },
    summary="이미지 업로드 → 영상 생성"
)
async def generate_video_from_upload(
    file: UploadFile = File(..., description="이미지 파일 (JPEG, PNG, WEBP)"),
    prompt: str = Form(default="Animate this image with natural, gentle motion", description="영상 생성 프롬프트"),
    aspect_ratio: str = Form(default="1:1", description="영상 비율 (1:1, 16:9, 9:16)"),
    loop: bool = Form(default=False, description="루프 영상 여부"),
    user: User = Depends(get_current_user)
):
    """
    이미지 파일을 업로드하여 영상 생성

    1. 이미지 유효성 검사
    2. 전처리 (RGB 변환, 1:1 크롭, 1024x1024 리사이즈)
    3. Stable Video Diffusion (SVD)으로 영상 생성

    - **file**: 이미지 파일 (최대 20MB)
    - **prompt**: (현재 SVD에서는 사용되지 않음)
    - **aspect_ratio**: 영상 비율
    - **loop**: (현재 SVD에서는 사용되지 않음)
    """
    logger.info(f"이미지 업로드 영상 생성 요청 - user: {user.id}, filename: {file.filename}")

    try:
        # 1. 파일 읽기
        image_bytes = await file.read()

        # 2. 유효성 검사
        is_valid, error_msg = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # 3. 이미지 전처리 (RGB, 1:1 크롭, 1024x1024, JPEG)
        processed_bytes = preprocess_image_for_ai(image_bytes)
        logger.info(f"이미지 전처리 완료 - 원본: {len(image_bytes)}bytes → 처리: {len(processed_bytes)}bytes")

        # 4. Base64 인코딩 (Replicate data URI 형식)
        base64_image = base64.b64encode(processed_bytes).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{base64_image}"

        # 5. 영상 생성
        video_url = await generate_video(
            image_url=data_uri,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            loop=loop
        )

        logger.info(f"영상 생성 완료 - user: {user.id}, url: {video_url}")

        return VideoFromUploadResponse(
            success=True,
            video_url=video_url,
            message="영상 생성이 완료되었습니다."
        )

    except ImageProcessingError as e:
        logger.error(f"이미지 전처리 실패 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미지 처리 실패: {str(e)}"
        )

    except ReplicateTimeoutError as e:
        logger.error(f"영상 생성 타임아웃 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="영상 생성 시간이 초과되었습니다."
        )

    except ReplicateError as e:
        logger.error(f"영상 생성 실패 - user: {user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"영상 생성 중 오류가 발생했습니다: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        logger.error(f"영상 생성 예외 - user: {user.id}, error: {str(e)}, traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )


# ============================================================
# 이미지 전처리만 (테스트/디버깅용)
# ============================================================
class PreprocessResponse(BaseModel):
    """이미지 전처리 응답"""
    success: bool
    original_size_kb: float
    processed_size_kb: float
    data_uri: str
    message: str = "이미지 전처리 완료"


@router.post(
    "/preprocess",
    response_model=PreprocessResponse,
    summary="이미지 전처리 (테스트용)"
)
async def preprocess_image_endpoint(
    file: UploadFile = File(..., description="이미지 파일"),
    user: User = Depends(get_current_user)
):
    """
    이미지 전처리만 수행 (영상 생성 없이)

    - RGB 변환
    - 1:1 중앙 크롭
    - 1024x1024 리사이즈
    - JPEG 압축 (품질 85)

    테스트/디버깅 용도로 사용
    """
    try:
        image_bytes = await file.read()

        is_valid, error_msg = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        processed_bytes = preprocess_image_for_ai(image_bytes)

        base64_image = base64.b64encode(processed_bytes).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{base64_image}"

        return PreprocessResponse(
            success=True,
            original_size_kb=round(len(image_bytes) / 1024, 2),
            processed_size_kb=round(len(processed_bytes) / 1024, 2),
            data_uri=data_uri,
            message="이미지 전처리가 완료되었습니다."
        )

    except ImageProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 이미지 + 영상 한번에 생성 (편의 API)
# ============================================================
class FullGenerateRequest(BaseModel):
    """이미지+영상 통합 생성 요청"""
    image_prompt: str = Field(..., description="이미지 생성 프롬프트")
    video_prompt: str = Field(default="Animate this image with natural, gentle motion", description="영상 생성 프롬프트")
    aspect_ratio: str = Field(default="1:1", description="비율")
    loop: bool = Field(default=False, description="루프 영상 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "image_prompt": "A cute golden retriever playing in a sunny park",
                "video_prompt": "The dog runs happily towards the camera",
                "aspect_ratio": "1:1",
                "loop": False
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
        전체 과정에 약 2-5분 소요될 수 있습니다.
    """
    logger.info(f"통합 생성 요청 - user: {user.id}, prompt: {request.image_prompt[:50]}...")

    try:
        # 1. 이미지 생성
        image_url = await generate_image(
            prompt=request.image_prompt,
            aspect_ratio=request.aspect_ratio
        )
        logger.info(f"이미지 생성 완료 - url: {image_url}")

        # 2. 영상 생성
        video_url = await generate_video(
            image_url=image_url,
            prompt=request.video_prompt,
            aspect_ratio=request.aspect_ratio,
            loop=request.loop
        )
        logger.info(f"영상 생성 완료 - url: {video_url}")

        return FullGenerateResponse(
            success=True,
            image_url=image_url,
            video_url=video_url,
            prompt=request.image_prompt,
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
