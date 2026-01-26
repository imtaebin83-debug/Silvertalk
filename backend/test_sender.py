# test_sender.py
from celery import Celery
import os

# 아까 설정한 Upstash 주소 (RunPod .env에 넣은 것과 똑같아야 함!)
# ?ssl_cert_reqs=CERT_NONE 꼭 포함하세요.
UPSTASH_URL = "rediss://default:ARzRAAImcDI4ZDE2ZTZmZWJkOGY0OTVjOGM1NzE4N2ViN2FlNWM3OHAyNzM3Nw@new-grizzly-7377.upstash.io:6379?ssl_cert_reqs=CERT_NONE"

celery_app = Celery(
    'silvertalk_worker', # RunPod 코드의 Celery 앱 이름과 같아야 함 (보통 tasks 파일 안의 이름)
    broker=UPSTASH_URL,
    backend=UPSTASH_URL
)

print("📨 메시지 보내는 중...")
# 'tasks.process_audio' 부분은 RunPod에 작성된 함수 이름과 정확히 같아야 합니다.
# 만약 함수 이름을 모르면 tasks.py 파일을 확인하거나 임의로 보내보세요.
task = celery_app.send_task('worker.tasks.process_audio_and_reply', args=["Test connection!"]) 
print(f"✅ 전송 완료! Task ID: {task.id}")