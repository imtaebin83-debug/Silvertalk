"""
AWS S3 업로드 유틸리티
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import logging

from .config import settings

logger = logging.getLogger(__name__)

# S3 클라이언트 초기화
def get_s3_client():
    """S3 클라이언트 반환"""
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )


def upload_file_to_s3(
    file_obj: BinaryIO,
    s3_key: str,
    content_type: str = "image/jpeg"
) -> Optional[str]:
    """
    파일을 S3에 업로드하고 URL 반환

    Args:
        file_obj: 파일 객체 (바이너리 모드)
        s3_key: S3 내 저장 경로 (예: "sessions/uuid/photo_0.jpg")
        content_type: 파일 MIME 타입

    Returns:
        성공 시 S3 URL, 실패 시 None
    """
    if not settings.S3_BUCKET_NAME:
        logger.error("S3_BUCKET_NAME이 설정되지 않았습니다.")
        return None

    try:
        s3_client = get_s3_client()

        # 파일 업로드
        s3_client.upload_fileobj(
            file_obj,
            settings.S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
            }
        )

        # S3 URL 생성
        url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"S3 업로드 성공: {url}")
        return url

    except ClientError as e:
        logger.error(f"S3 업로드 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"S3 업로드 중 오류: {e}")
        return None


def delete_file_from_s3(s3_key: str) -> bool:
    """
    S3에서 파일 삭제

    Args:
        s3_key: S3 내 파일 경로

    Returns:
        성공 여부
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key
        )
        logger.info(f"S3 파일 삭제 성공: {s3_key}")
        return True
    except Exception as e:
        logger.error(f"S3 파일 삭제 실패: {e}")
        return False


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    S3 Presigned URL 생성 (업로드용)

    Args:
        s3_key: S3 내 저장 경로
        expiration: URL 유효 시간 (초)

    Returns:
        Presigned URL 또는 None
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.S3_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Presigned URL 생성 실패: {e}")
        return None
