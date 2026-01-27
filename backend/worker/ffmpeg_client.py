"""
FFmpeg 슬라이드쇼 영상 생성
- Ken Burns 효과 (줌인/아웃)
- 사진 간 페이드 트랜지션
- 오디오 (나레이션) 합성
- 썸네일 추출
"""
import os
import subprocess
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SlideConfig:
    """개별 슬라이드 설정"""
    image_path: str
    duration: float = 5.0  # 슬라이드당 초


@dataclass
class SlideshowConfig:
    """슬라이드쇼 전체 설정"""
    slides: List[SlideConfig]
    audio_path: Optional[str] = None
    output_path: str = "output.mp4"
    resolution: Tuple[int, int] = (1080, 1920)  # 세로 모바일 (width, height)
    fps: int = 30
    transition_duration: float = 1.0  # 크로스페이드 시간
    ken_burns_zoom: float = 1.1  # 10% 줌


class FFmpegError(Exception):
    """FFmpeg 처리 에러"""
    pass


class FFmpegSlideshowGenerator:
    """
    Ken Burns 효과와 트랜지션이 적용된 슬라이드쇼 생성기
    """

    def __init__(self, config: SlideshowConfig):
        self.config = config

    def generate(self) -> str:
        """
        슬라이드쇼 영상 생성

        Returns:
            생성된 영상 파일 경로
        """
        try:
            # 단일 이미지인 경우 간단한 방식 사용
            if len(self.config.slides) == 1:
                return self._generate_single_image()

            # 여러 이미지인 경우 Ken Burns + 크로스페이드
            return self._generate_multi_image()

        except subprocess.TimeoutExpired:
            raise FFmpegError("FFmpeg 타임아웃 (5분 초과)")
        except Exception as e:
            raise FFmpegError(f"영상 생성 실패: {str(e)}")

    def _generate_single_image(self) -> str:
        """단일 이미지 슬라이드쇼 생성"""
        slide = self.config.slides[0]
        width, height = self.config.resolution
        duration = slide.duration

        if self.config.audio_path:
            # 오디오 길이에 맞춤
            duration = self.get_audio_duration(self.config.audio_path)

        # Ken Burns 효과: 천천히 줌인
        zoom_increment = (self.config.ken_burns_zoom - 1.0) / (duration * self.config.fps)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", slide.image_path,
        ]

        # 오디오 추가
        if self.config.audio_path:
            cmd.extend(["-i", self.config.audio_path])

        # 필터: 스케일 + Ken Burns 줌 + 크롭
        filter_complex = (
            f"[0:v]scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
            f"crop={width*2}:{height*2},"
            f"zoompan=z='min(zoom+{zoom_increment},{self.config.ken_burns_zoom})':"
            f"d={int(duration * self.config.fps)}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={width}x{height}:fps={self.config.fps},"
            f"format=yuv420p[outv]"
        )

        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[outv]"])

        if self.config.audio_path:
            cmd.extend(["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-movflags", "+faststart",
            "-t", str(duration),
            self.config.output_path
        ])

        logger.info(f"FFmpeg 명령어: {' '.join(cmd[:15])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(f"FFmpeg 에러: {result.stderr}")
            raise FFmpegError(f"FFmpeg 실패: {result.stderr[:500]}")

        return self.config.output_path

    def _generate_multi_image(self) -> str:
        """여러 이미지 슬라이드쇼 생성 (크로스페이드 포함)"""
        width, height = self.config.resolution
        slides = self.config.slides
        fps = self.config.fps
        trans_dur = self.config.transition_duration

        # 오디오가 있으면 슬라이드 시간 자동 조정
        if self.config.audio_path:
            audio_duration = self.get_audio_duration(self.config.audio_path)
            # 트랜지션 시간을 고려한 슬라이드당 시간 계산
            total_trans_time = trans_dur * (len(slides) - 1)
            slide_duration = (audio_duration + total_trans_time) / len(slides)
            slide_duration = max(slide_duration, 2.0)  # 최소 2초

            for slide in slides:
                slide.duration = slide_duration

        # FFmpeg 명령어 구성
        cmd = ["ffmpeg", "-y"]

        # 입력 이미지들
        for slide in slides:
            cmd.extend(["-loop", "1", "-t", str(slide.duration), "-i", slide.image_path])

        # 오디오 입력
        if self.config.audio_path:
            cmd.extend(["-i", self.config.audio_path])

        # 필터 구성
        filter_parts = []

        # 각 이미지에 Ken Burns 효과 적용
        for i, slide in enumerate(slides):
            duration_frames = int(slide.duration * fps)
            zoom_increment = (self.config.ken_burns_zoom - 1.0) / duration_frames

            # 번갈아 줌인/줌아웃 효과
            if i % 2 == 0:
                # 줌인
                zoom_expr = f"min(zoom+{zoom_increment},{self.config.ken_burns_zoom})"
            else:
                # 줌아웃
                zoom_expr = f"max(zoom-{zoom_increment},1.0)"
                # 초기 줌 설정 필요

            ken_burns = (
                f"[{i}:v]scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
                f"crop={width*2}:{height*2},"
                f"zoompan=z='{zoom_expr}':"
                f"d={duration_frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={width}x{height}:fps={fps}[v{i}]"
            )
            filter_parts.append(ken_burns)

        # 크로스페이드로 연결
        if len(slides) > 1:
            prev = "v0"
            for i in range(1, len(slides)):
                # 이전 슬라이드 끝에서 페이드 시작
                offset = sum(s.duration for s in slides[:i]) - trans_dur * i
                offset = max(0, offset)

                xfade = (
                    f"[{prev}][v{i}]xfade=transition=fade:"
                    f"duration={trans_dur}:offset={offset}[xf{i}]"
                )
                filter_parts.append(xfade)
                prev = f"xf{i}"

            filter_parts.append(f"[{prev}]format=yuv420p[outv]")
        else:
            filter_parts.append("[v0]format=yuv420p[outv]")

        filter_complex = ";".join(filter_parts)

        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[outv]"])

        # 오디오 매핑
        if self.config.audio_path:
            audio_idx = len(slides)
            cmd.extend(["-map", f"{audio_idx}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-movflags", "+faststart",
            self.config.output_path
        ])

        logger.info(f"FFmpeg 다중 이미지 슬라이드쇼 생성: {len(slides)}장")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(f"FFmpeg 에러: {result.stderr}")
            raise FFmpegError(f"FFmpeg 실패: {result.stderr[:500]}")

        return self.config.output_path

    @staticmethod
    def get_audio_duration(audio_path: str) -> float:
        """오디오 파일 길이 (초) 반환"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"오디오 길이 조회 실패, 기본값 사용")
            return 10.0

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 10.0


def generate_slideshow(
    image_paths: List[str],
    audio_path: Optional[str],
    output_path: str,
    duration_per_slide: float = 5.0,
    resolution: Tuple[int, int] = (1080, 1920)
) -> str:
    """
    슬라이드쇼 생성 편의 함수

    Args:
        image_paths: 이미지 파일 경로 목록
        audio_path: 나레이션 오디오 경로 (선택)
        output_path: 출력 영상 경로
        duration_per_slide: 슬라이드당 기본 시간 (오디오 있으면 자동 조정)
        resolution: (width, height) 해상도

    Returns:
        생성된 영상 파일 경로
    """
    if not image_paths:
        raise FFmpegError("이미지가 없습니다")

    # 존재하는 이미지만 필터링
    valid_paths = [p for p in image_paths if os.path.exists(p)]
    if not valid_paths:
        raise FFmpegError("유효한 이미지가 없습니다")

    slides = [SlideConfig(image_path=p, duration=duration_per_slide) for p in valid_paths]

    config = SlideshowConfig(
        slides=slides,
        audio_path=audio_path,
        output_path=output_path,
        resolution=resolution
    )

    generator = FFmpegSlideshowGenerator(config)
    return generator.generate()


def generate_thumbnail(video_path: str, output_path: str, time: str = "00:00:01") -> str:
    """
    영상에서 썸네일 추출

    Args:
        video_path: 입력 영상 경로
        output_path: 썸네일 저장 경로
        time: 추출 시점 (HH:MM:SS)

    Returns:
        썸네일 파일 경로
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", time,
        "-vframes", "1",
        "-vf", "scale=640:-1",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        logger.error(f"썸네일 생성 실패: {result.stderr}")
        raise FFmpegError(f"썸네일 생성 실패: {result.stderr[:200]}")

    return output_path


def get_video_duration(video_path: str) -> float:
    """영상 길이 (초) 반환"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return 0.0

    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def merge_videos_with_audio(
    video_paths: List[str],
    audio_path: str,
    output_path: str,
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 30
) -> str:
    """
    여러 영상을 병합하고 오디오를 추가
    
    Args:
        video_paths: 병합할 영상 파일 경로 목록 (또는 URL)
        audio_path: 추가할 오디오 파일 경로
        output_path: 출력 영상 경로
        resolution: (width, height) 해상도
        fps: 프레임 레이트
    
    Returns:
        생성된 영상 파일 경로
    
    Raises:
        FFmpegError: 영상 병합 실패
    
    Example:
        >>> merge_videos_with_audio(
        ...     video_paths=["video1.mp4", "video2.mp4"],
        ...     audio_path="narration.wav",
        ...     output_path="final.mp4"
        ... )
    """
    if not video_paths:
        raise FFmpegError("병합할 영상이 없습니다")
    
    if not os.path.exists(audio_path):
        raise FFmpegError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")
    
    # URL인 경우 다운로드 필요 (임시 처리)
    local_video_paths = []
    for i, video_path in enumerate(video_paths):
        if video_path.startswith("http://") or video_path.startswith("https://"):
            # URL에서 다운로드
            import httpx
            temp_path = f"/tmp/video_temp_{i}.mp4"
            
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.get(video_path)
                    response.raise_for_status()
                    
                    with open(temp_path, "wb") as f:
                        f.write(response.content)
                    
                    local_video_paths.append(temp_path)
                    logger.info(f"영상 다운로드 완료: {video_path[:50]}...")
            except Exception as e:
                logger.error(f"영상 다운로드 실패: {str(e)}")
                raise FFmpegError(f"영상 다운로드 실패: {str(e)}")
        else:
            if not os.path.exists(video_path):
                raise FFmpegError(f"영상 파일을 찾을 수 없습니다: {video_path}")
            local_video_paths.append(video_path)
    
    try:
        width, height = resolution
        
        # 단일 영상인 경우
        if len(local_video_paths) == 1:
            cmd = [
                "ffmpeg", "-y",
                "-i", local_video_paths[0],
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                "-movflags", "+faststart",
                "-shortest",
                output_path
            ]
        else:
            # 여러 영상 병합
            # concat demuxer를 위한 파일 목록 생성
            concat_file = "/tmp/concat_list.txt"
            with open(concat_file, "w") as f:
                for video_path in local_video_paths:
                    # 특수문자 이스케이프
                    escaped_path = video_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # 1단계: 영상들을 병합
            merged_video = "/tmp/merged_video.mp4"
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                merged_video
            ]
            
            logger.info(f"영상 병합 중: {len(local_video_paths)}개")
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"영상 병합 실패: {result.stderr}")
                raise FFmpegError(f"영상 병합 실패: {result.stderr[:500]}")
            
            # 2단계: 오디오 추가
            cmd = [
                "ffmpeg", "-y",
                "-i", merged_video,
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-shortest",
                output_path
            ]
        
        logger.info(f"오디오 추가 중: {audio_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            logger.error(f"오디오 추가 실패: {result.stderr}")
            raise FFmpegError(f"오디오 추가 실패: {result.stderr[:500]}")
        
        logger.info(f"영상 병합 완료: {output_path}")
        return output_path
    
    finally:
        # 임시 파일 정리
        for temp_path in local_video_paths:
            if temp_path.startswith("/tmp/") and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        # concat 파일 정리
        if os.path.exists("/tmp/concat_list.txt"):
            try:
                os.remove("/tmp/concat_list.txt")
            except:
                pass
        
        if os.path.exists("/tmp/merged_video.mp4"):
            try:
                os.remove("/tmp/merged_video.mp4")
            except:
                pass
