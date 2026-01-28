"""
이미지 전처리 유틸리티
- AI 모델(Replicate Flux 등)에 이미지를 전달하기 전 전처리
"""
from io import BytesIO
from typing import Tuple, Dict, Any, Union
from PIL import Image
import os


class ImageProcessingError(Exception):
    """이미지 처리 중 발생하는 에러"""
    pass


def preprocess_image_file(
    input_path: str,
    output_path: str,
    target_size: Tuple[int, int] = (1920, 1080),
    jpeg_quality: int = 95
) -> str:
    """
    파일 기반 이미지 전처리 (영상용)
    
    Args:
        input_path: 입력 파일 경로
        output_path: 출력 파일 경로
        target_size: (width, height)
        jpeg_quality: JPEG 품질
        
    Returns:
        output_path
    """
    try:
        with open(input_path, "rb") as f:
            image_bytes = f.read()
            
        processed_bytes = preprocess_image(image_bytes, target_size, jpeg_quality)
        
        with open(output_path, "wb") as f:
            f.write(processed_bytes)
            
        return output_path
    except Exception as e:
        raise ImageProcessingError(f"이미지 파일 처리 실패: {str(e)}")


def preprocess_image(
    image_bytes: bytes,
    target_size: Union[int, Tuple[int, int]] = 1024,
    jpeg_quality: int = 85
) -> bytes:
    """
    이미지 전처리 (공통 로직)
    """
    try:
        image = Image.open(BytesIO(image_bytes))
    except Exception as e:
        raise ImageProcessingError(f"이미지를 열 수 없습니다: {str(e)}")

    try:
        # 1. RGB 변환
        if image.mode != "RGB":
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            else:
                image = image.convert("RGB")

        # 타겟 크기 결정
        if isinstance(target_size, int):
            target_w, target_h = target_size, target_size
            is_square = True
        else:
            target_w, target_h = target_size
            is_square = False

        # 2. Resizing & Cropping
        if is_square:
            # 기존 로직: Center Crop 1:1 -> Resize
            width, height = image.size
            min_side = min(width, height)
            left = (width - min_side) // 2
            top = (height - min_side) // 2
            right = left + min_side
            bottom = top + min_side
            image = image.crop((left, top, right, bottom))
            image = image.resize((target_w, target_h), Image.LANCZOS)
        else:
            # 영상용: Aspect Ratio 유지하며 Resize 후 Center Crop? 
            # 아니면 Black Bar 추가? 
            # 여기서는 [Aspect Fill] 방식으로 구현 (화면을 꽉 채우되 넘치는 부분 잘림)
            
            src_w, src_h = image.size
            src_ratio = src_w / src_h
            target_ratio = target_w / target_h
            
            if src_ratio > target_ratio:
                # 원본이 더 와이드함 -> 높이 맞추고 가로 잘림
                new_h = target_h
                new_w = int(new_h * src_ratio)
            else:
                # 원본이 더 홀쭉함 -> 가로 맞추고 세로 잘림
                new_w = target_w
                new_h = int(new_w / src_ratio)
                
            # 1차 리사이즈 (LANCZOS)
            resize_img = image.resize((new_w, new_h), Image.LANCZOS)
            
            # 중앙 크롭
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            right = left + target_w
            bottom = top + target_h
            image = resize_img.crop((left, top, right, bottom))

        # 4. JPEG 압축
        output_buffer = BytesIO()
        image.save(
            output_buffer,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True
        )
        return output_buffer.getvalue()

    except Exception as e:
        raise ImageProcessingError(f"이미지 처리 중 오류 발생: {str(e)}")


# 기존 호환성 유지 (preprocess_image_for_ai -> preprocess_image alias)
preprocess_image_for_ai = preprocess_image

def get_image_info(image_bytes: bytes) -> Dict[str, Any]:
    """이미지 정보 조회"""
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

def validate_image(image_bytes: bytes, max_size_mb: float = 20.0) -> Tuple[bool, str]:
    """이미지 유효성 검사"""
    # ... 기존 코드 생략 ...
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"이미지 크기가 너무 큽니다. (최대 {max_size_mb}MB, 현재 {size_mb:.1f}MB)"

    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
    except Exception as e:
        return False, f"유효하지 않은 이미지 파일입니다: {str(e)}"

    image = Image.open(BytesIO(image_bytes))
    supported_formats = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}
    if image.format not in supported_formats:
        return False, f"지원하지 않는 이미지 포맷입니다. (지원: {', '.join(supported_formats)})"

    min_size = 64
    if image.size[0] < min_size or image.size[1] < min_size:
        return False, f"이미지가 너무 작습니다. (최소 {min_size}x{min_size})"

    return True, "유효한 이미지입니다."
