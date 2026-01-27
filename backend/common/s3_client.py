"""
AWS S3 스토리지 클라이언트
- 파일 업로드/다운로드
- Presigned URL 생성
- 로컬 개발용 mock 클라이언트
"""
import os
import shutil
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class S3Error(Exception):
    """S3 작업 에러"""
    pass


class S3Client:
    """AWS S3 클라이언트"""

    def __init__(self):
        from .config import settings

        # boto3 동적 import (의존성 없을 때 에러 방지)
        try:
            import boto3
            from botocore.exceptions import ClientError
            self.ClientError = ClientError
        except ImportError:
            raise S3Error("boto3가 설치되지 않았습니다. pip install boto3")

        if not settings.AWS_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
            raise S3Error("AWS 설정이 없습니다 (AWS_ACCESS_KEY_ID, S3_BUCKET_NAME)")

        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        파일을 S3에 업로드

        Args:
            local_path: 로컬 파일 경로
            s3_key: S3 객체 키 (버킷 내 경로)
            content_type: MIME 타입

        Returns:
            S3 URL
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs=extra_args if extra_args else None
            )

            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
            logger.info(f"S3 업로드 완료: {url}")
            return url

        except self.ClientError as e:
            logger.error(f"S3 업로드 실패: {e}")
            raise S3Error(f"업로드 실패: {str(e)}")

    def download_file(self, s3_url_or_key: str, local_path: str) -> str:
        """
        S3에서 파일 다운로드

        Args:
            s3_url_or_key: S3 URL 또는 키
            local_path: 저장할 로컬 경로

        Returns:
            로컬 파일 경로
        """
        try:
            # URL에서 키 추출
            if s3_url_or_key.startswith("https://"):
                # https://bucket.s3.region.amazonaws.com/key
                s3_key = s3_url_or_key.split('.amazonaws.com/')[-1]
            else:
                s3_key = s3_url_or_key

            self.client.download_file(self.bucket, s3_key, local_path)
            logger.info(f"S3 다운로드 완료: {s3_key} -> {local_path}")
            return local_path

        except self.ClientError as e:
            logger.error(f"S3 다운로드 실패: {e}")
            raise S3Error(f"다운로드 실패: {str(e)}")

    def generate_presigned_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
        operation: str = "get_object"
    ) -> str:
        """
        Presigned URL 생성

        Args:
            s3_key: S3 객체 키
            expires_in: 만료 시간 (초)
            operation: "get_object" 또는 "put_object"

        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except self.ClientError as e:
            raise S3Error(f"Presigned URL 생성 실패: {str(e)}")

    def delete_file(self, s3_key: str) -> bool:
        """S3 파일 삭제"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"S3 삭제 완료: {s3_key}")
            return True
        except self.ClientError as e:
            logger.error(f"S3 삭제 실패: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """S3 파일 존재 여부 확인"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except self.ClientError:
            return False


class LocalStorageClient:
    """
    로컬 개발용 mock 스토리지 클라이언트
    S3 대신 로컬 파일 시스템 사용
    """

    def __init__(self, base_path: str = "/app/data/storage"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """파일을 로컬 스토리지에 복사"""
        # 키의 디렉토리 구조 생성
        dest_path = os.path.join(self.base_path, s3_key)
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)

        shutil.copy(local_path, dest_path)
        url = f"file://{dest_path}"
        logger.info(f"로컬 스토리지 저장: {url}")
        return url

    def download_file(self, s3_url_or_key: str, local_path: str) -> str:
        """로컬 스토리지에서 파일 복사"""
        if s3_url_or_key.startswith("file://"):
            src = s3_url_or_key[7:]
        else:
            src = os.path.join(self.base_path, s3_url_or_key)

        if not os.path.exists(src):
            raise S3Error(f"파일을 찾을 수 없습니다: {src}")

        shutil.copy(src, local_path)
        logger.info(f"로컬 스토리지 다운로드: {src} -> {local_path}")
        return local_path

    def generate_presigned_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
        operation: str = "get_object"
    ) -> str:
        """로컬 파일 경로 반환"""
        return f"file://{os.path.join(self.base_path, s3_key)}"

    def delete_file(self, s3_key: str) -> bool:
        """로컬 파일 삭제"""
        path = os.path.join(self.base_path, s3_key)
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False

    def file_exists(self, s3_key: str) -> bool:
        """파일 존재 여부"""
        return os.path.exists(os.path.join(self.base_path, s3_key))


def get_storage_client():
    """
    환경에 따라 적절한 스토리지 클라이언트 반환

    - development: LocalStorageClient (S3 설정 없어도 동작)
    - production: S3Client
    """
    from .config import settings

    # 개발 환경이거나 AWS 설정이 없으면 로컬 스토리지 사용
    if settings.ENVIRONMENT == "development":
        if not settings.AWS_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
            logger.info("로컬 스토리지 사용 (개발 환경)")
            return LocalStorageClient()

    try:
        return S3Client()
    except S3Error as e:
        logger.warning(f"S3 초기화 실패, 로컬 스토리지로 fallback: {e}")
        return LocalStorageClient()


def upload_video(local_path: str, user_id: str, video_id: str) -> tuple:
    """
    영상 업로드 편의 함수

    Args:
        local_path: 로컬 영상 파일 경로
        user_id: 사용자 ID
        video_id: 영상 ID

    Returns:
        (video_url, thumbnail_url)
    """
    from .ffmpeg_client import generate_thumbnail

    client = get_storage_client()

    # 영상 업로드
    video_key = f"videos/{user_id}/{video_id}.mp4"
    video_url = client.upload_file(local_path, video_key, content_type="video/mp4")

    # 썸네일 생성 및 업로드
    thumbnail_path = local_path.replace('.mp4', '_thumb.jpg')
    try:
        generate_thumbnail(local_path, thumbnail_path)
        thumb_key = f"videos/{user_id}/{video_id}_thumb.jpg"
        thumb_url = client.upload_file(thumbnail_path, thumb_key, content_type="image/jpeg")

        # 로컬 썸네일 정리
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
    except Exception as e:
        logger.warning(f"썸네일 생성/업로드 실패: {e}")
        thumb_url = None

    return video_url, thumb_url


def download_image(image_url: str, local_path: str) -> str:
    """
    이미지 다운로드 편의 함수

    S3 URL 또는 HTTP URL 모두 지원

    Args:
        image_url: 이미지 URL (S3, HTTP, file://)
        local_path: 저장할 로컬 경로

    Returns:
        로컬 파일 경로
    """
    # 로컬 파일
    if image_url.startswith("file://"):
        src = image_url[7:]
        if os.path.exists(src):
            shutil.copy(src, local_path)
            return local_path
        raise S3Error(f"로컬 파일 없음: {src}")

    # 이미 로컬 경로인 경우
    if os.path.exists(image_url):
        shutil.copy(image_url, local_path)
        return local_path

    # S3 URL
    if "s3." in image_url and "amazonaws.com" in image_url:
        client = get_storage_client()
        return client.download_file(image_url, local_path)

    # HTTP URL (외부 이미지)
    if image_url.startswith("http"):
        import httpx
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.get(image_url)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
        return local_path

    raise S3Error(f"알 수 없는 URL 형식: {image_url}")
