"""
Celery 작업 전송 및 결과 확인 테스트
EC2 → Redis → RunPod Worker 전체 파이프라인 검증
"""
from app.celery_config import celery_producer
import time

print("=" * 60)
print("Celery Task 전송 테스트")
print("=" * 60)

# 테스트 작업 전송
task = celery_producer.send_task(
    'worker.tasks.process_audio',
    args=["test-session-123", "s3://silvertalkbucket/test.wav"],
    kwargs={"user_prompt": "안녕하세요"},
    queue='ai_tasks'
)

print(f"\n✅ Task 전송 완료!")
print(f"   Task ID: {task.id}")
print(f"   Queue: ai_tasks")
print(f"   Initial State: {task.state}")

# 작업 완료 대기 (최대 60초)
print(f"\n⏳ Worker 응답 대기 중... (최대 60초)")
try:
    result = task.get(timeout=60)
    print(f"\n✅ Task 완료!")
    print(f"   Status: {result.get('status')}")
    print(f"   Transcription: {result.get('transcription', 'N/A')[:100]}")
    print(f"   Response Audio: {result.get('response_audio_url', 'N/A')}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"   Task State: {task.state}")
    print("\n💡 RunPod Worker가 실행 중인지 확인하세요!")

print("\n" + "=" * 60)
