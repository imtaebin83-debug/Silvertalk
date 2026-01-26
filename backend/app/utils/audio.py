import io
import ffmpeg
from fastapi import UploadFile, HTTPException

async def convert_audio_to_wav(file: UploadFile, target_sr: int = 16000) -> io.BytesIO:
    """
    업로드된 오디오 파일을 읽어 16kHz Mono WAV 포맷으로 변환합니다.
    Memory-to-Memory 처리를 위해 pipe를 사용합니다.
    """
    try:
        # 파일 내용을 메모리에 읽음
        file_content = await file.read()
        
        # ffmpeg 프로세스 실행 (Input Pipe -> Output Pipe)
        # -ac 1: Mono channel
        # -ar 16000: 16kHz Sampling rate
        out, _ = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav', ac=1, ar=target_sr)
            .run(input=file_content, capture_stdout=True, capture_stderr=True)
        )
        
        return io.BytesIO(out)
        
    except ffmpeg.Error as e:
        # 에러 발생 시 stderr 내용을 로그로 확인 가능
        print(f"FFmpeg Error: {e.stderr.decode()}")
        raise HTTPException(status_code=500, detail="Audio conversion failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.seek(0) # 커서 초기화 (필요 시)