"""
이미지 전처리 유틸리티
- AI 모델(Replicate Flux 등)에 이미지를 전달하기 전 전처리
"""
from io import BytesIO
from PIL import Image


class ImageProcessingError(Exception):
    """이미지 처리 중 발생하는 에러"""
    pass


def preprocess_image_for_ai(
    image_bytes: bytes,
    target_size: int = 1024,
    jpeg_quality: int = 85
) -> bytes:
    """
    AI 모델 입력용 이미지 전처리

    전처리 단계:
    1. RGB 변환: PNG 투명도(RGBA) 등 오류 방지
    2. Center Crop: 정사각형(1:1) 비율로 중앙 크롭
    3. Resize: target_size x target_size로 리사이징 (LANCZOS 필터)
    4. Compression: JPEG 포맷, 지정된 품질로 압축

    Args:
        image_bytes: 원본 이미지 바이트 데이터
        target_size: 출력 이미지 크기 (기본 1024x1024)
        jpeg_quality: JPEG 압축 품질 1-100 (기본 85)

    Returns:
        전처리된 JPEG 이미지 바이트 데이터

    Raises:
        ImageProcessingError: 이미지 처리 실패 시

    Example:
        >>> with open("photo.png", "rb") as f:
        ...     original = f.read()
        >>> processed = preprocess_image_for_ai(original)
        >>> # processed는 1024x1024 JPEG 바이트
    """
    try:
        # 바이트 데이터에서 이미지 로드
        image = Image.open(BytesIO(image_bytes))
    except Exception as e:
        # 손상된 이미지 또는 지원하지 않는 포맷
        # - 파일이 실제 이미지가 아닌 경우
        # - 파일이 손상된 경우
        # - 지원하지 않는 이미지 포맷인 경우
        raise ImageProcessingError(f"이미지를 열 수 없습니다: {str(e)}")

    try:
        # 1. RGB 변환
        # - RGBA (PNG 투명도), P (팔레트), L (그레이스케일) 등을
        #   RGB로 변환하여 JPEG 저장 및 AI 모델 호환성 확보
        if image.mode != "RGB":
            # RGBA의 경우 흰색 배경 위에 합성
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # 알파 채널을 마스크로 사용
                image = background
            else:
                image = image.convert("RGB")

        # 2. Center Crop (1:1 정사각형)
        # - 가로/세로 중 짧은 쪽을 기준으로 정중앙 크롭
        width, height = image.size
        min_side = min(width, height)

        # 크롭 영역 계산 (정중앙)
        left = (width - min_side) // 2
        top = (height - min_side) // 2
        right = left + min_side
        bottom = top + min_side

        image = image.crop((left, top, right, bottom))

        # 3. Resize (LANCZOS 필터 - 고품질 다운샘플링)
        # - LANCZOS(Lanczos3): 고품질 리샘플링, 선명도 유지
        # - 다른 옵션: BILINEAR(빠름), BICUBIC(중간), BOX(빠름)
        image = image.resize((target_size, target_size), Image.LANCZOS)

        # 4. JPEG 압축 및 바이트 변환
        output_buffer = BytesIO()
        image.save(
            output_buffer,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True  # 파일 크기 최적화
        )

        return output_buffer.getvalue()

    except Exception as e:
        # 처리 중 예기치 않은 에러
        # - 메모리 부족
        # - 극단적으로 큰 이미지
        # - 내부 PIL 에러
        raise ImageProcessingError(f"이미지 처리 중 오류 발생: {str(e)}")


def get_image_info(image_bytes: bytes) -> dict:
    """
    이미지 정보 조회 (디버깅/로깅용)

    Args:
        image_bytes: 이미지 바이트 데이터

    Returns:
        {
            "format": "JPEG",
            "mode": "RGB",
            "width": 1920,
            "height": 1080,
            "size_kb": 245.5
        }
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        return {
            "format": image.format,
            "mode": image.mode,
            "width": image.size[0],
            "height": image.size[1],
            "size_kb": round(len(image_bytes) / 1024, 2)
        }
    except Exception:
        return {"error": "이미지 정보를 읽을 수 없습니다."}


def validate_image(image_bytes: bytes, max_size_mb: float = 20.0) -> tuple[bool, str]:
    """
    이미지 유효성 검사

    Args:
        image_bytes: 이미지 바이트 데이터
        max_size_mb: 최대 허용 크기 (MB)

    Returns:
        (is_valid: bool, message: str)

    Example:
        >>> is_valid, msg = validate_image(image_bytes)
        >>> if not is_valid:
        ...     raise ValueError(msg)
    """
    # 파일 크기 검사
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"이미지 크기가 너무 큽니다. (최대 {max_size_mb}MB, 현재 {size_mb:.1f}MB)"

    # 이미지 열기 검사
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()  # 이미지 무결성 검증
    except Exception as e:
        return False, f"유효하지 않은 이미지 파일입니다: {str(e)}"

    # 지원 포맷 검사
    # verify() 후에는 다시 열어야 함
    image = Image.open(BytesIO(image_bytes))
    supported_formats = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}
    if image.format not in supported_formats:
        return False, f"지원하지 않는 이미지 포맷입니다. (지원: {', '.join(supported_formats)})"

    # 최소 크기 검사
    min_size = 64
    if image.size[0] < min_size or image.size[1] < min_size:
        return False, f"이미지가 너무 작습니다. (최소 {min_size}x{min_size})"

    return True, "유효한 이미지입니다."
