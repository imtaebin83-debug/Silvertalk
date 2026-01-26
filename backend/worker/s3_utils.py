"""
RunPod Worker용 S3 유틸리티
- S3에서 오디오 파일 다운로드
- 처리 결과를 S3에 업로드
"""
import boto3
import os
import logging
from pathlib import Path
from common.config import settings

logger = logging.getLogger(__name__)

def get_s3_client():
    """
    S3 클라이언트 생성
    
    환경 변수에서 AWS 자격증명 자동 로드
    
    Returns:
        boto3.client: S3 클라이언트
    """
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )


def download_from_s3(s3_key: str, local_path: str) -> str:
    """
    S3에서 파일 다운로드
    
    Args:
        s3_key: S3 객체 키 (예: "audio/user123/recording.wav")
        local_path: 로컬 저장 경로 (예: "/tmp/recording.wav")
    
    Returns:
        str: 다운로드된 파일의 로컬 경로
    
    Raises:
        Exception: S3 다운로드 실패 시
    """
    try:
        s3_client = get_s3_client()
        bucket_name = settings.S3_BUCKET_NAME
        
        # 디렉토리 생성
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📥 S3 다운로드 시작: s3://{bucket_name}/{s3_key} → {local_path}")
        s3_client.download_file(bucket_name, s3_key, local_path)
        logger.info(f"✅ S3 다운로드 완료: {local_path}")
        
        return local_path
    
    except Exception as e:
        logger.error(f"❌ S3 다운로드 실패: {str(e)}")
        raise Exception(f"S3 download failed: {str(e)}")


def upload_to_s3(local_path: str, s3_key: str) -> str:
    """
    로컬 파일을 S3에 업로드
    
    Args:
        local_path: 업로드할 로컬 파일 경로
        s3_key: S3 객체 키 (예: "audio/user123/response.wav")
    
    Returns:
        str: S3 URL (https://bucket-name.s3.region.amazonaws.com/key)
    
    Raises:
        Exception: S3 업로드 실패 시
    """
    try:
        s3_client = get_s3_client()
        bucket_name = settings.S3_BUCKET_NAME
        
        logger.info(f"📤 S3 업로드 시작: {local_path} → s3://{bucket_name}/{s3_key}")
        s3_client.upload_file(local_path, bucket_name, s3_key)
        
        # S3 URL 생성
        s3_url = f"https://{bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"✅ S3 업로드 완료: {s3_url}")
        
        return s3_url
    
    except Exception as e:
        logger.error(f"❌ S3 업로드 실패: {str(e)}")
        raise Exception(f"S3 upload failed: {str(e)}")


def cleanup_temp_files(*file_paths: str):
    """
    임시 파일 삭제
    
    Args:
        *file_paths: 삭제할 파일 경로들
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ 임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ 파일 삭제 실패: {file_path} - {str(e)}")
