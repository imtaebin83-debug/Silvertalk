# ============================================================
# FastAPI 프로덕션 실행 가이드
# ============================================================

## 🚀 실행 방식 비교

### 1️⃣ 간단한 방식 (개발/테스트)
```bash
# screen 사용 (터미널 종료해도 실행 유지)
screen -S fastapi
cd ~/Silvertalk/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 세션 나가기: Ctrl+A, D
# 다시 들어가기: screen -r fastapi
```

### 2️⃣ nohup 방식 (백그라운드 실행)
```bash
cd ~/Silvertalk/backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &

# 로그 확인
tail -f /tmp/fastapi.log

# 프로세스 종료
ps aux | grep uvicorn
kill <PID>
```

### 3️⃣ systemd 서비스 (권장, 프로덕션)
```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/silvertalk-api.service
```

**서비스 파일 내용:**
```ini
[Unit]
Description=SilverTalk FastAPI Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Silvertalk/backend
Environment="PATH=/home/ubuntu/Silvertalk/backend/venv/bin"
ExecStart=/home/ubuntu/Silvertalk/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

# 로그 설정
StandardOutput=append:/var/log/silvertalk-api.log
StandardError=append:/var/log/silvertalk-api.error.log

[Install]
WantedBy=multi-user.target
```

**서비스 활성화:**
```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable silvertalk-api

# 서비스 시작
sudo systemctl start silvertalk-api

# 상태 확인
sudo systemctl status silvertalk-api

# 로그 확인
sudo journalctl -u silvertalk-api -f

# 재시작
sudo systemctl restart silvertalk-api

# 중지
sudo systemctl stop silvertalk-api
```

## 🎯 현재 아키텍처에 맞는 추천

**개발 단계**: screen 방식
**프로덕션**: systemd 서비스

### 현재 작업 흐름

```python
# FastAPI 엔드포인트 예시
@app.post("/api/chat/audio")
async def process_audio(file: UploadFile, user_id: str):
    # 1. 파일 저장 (S3 또는 로컬)
    audio_path = await save_audio(file)
    
    # 2. Celery 태스크 큐잉 (RunPod로 전달)
    task = process_audio_and_reply.delay(audio_path, user_id)
    
    # 3. 태스크 ID 반환 (클라이언트가 polling)
    return {"task_id": task.id, "status": "processing"}

@app.get("/api/tasks/{task_id}")
async def get_task_result(task_id: str):
    # 4. 태스크 결과 조회 (Redis에서)
    task = AsyncResult(task_id)
    
    if task.ready():
        return {"status": "completed", "result": task.result}
    else:
        return {"status": "processing"}
```

### Nginx 리버스 프록시 (선택 사항)

프로덕션에서는 Nginx를 앞단에 두는 것이 좋습니다:

```bash
sudo apt-get install nginx

# /etc/nginx/sites-available/silvertalk
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 📊 모니터링

### 서버 상태 확인
```bash
# CPU/메모리 사용률
htop

# 포트 확인
sudo netstat -tulpn | grep 8000

# FastAPI 로그 (systemd)
sudo journalctl -u silvertalk-api --since "1 hour ago"
```

### 헬스체크 엔드포인트

```python
# app/main.py
@app.get("/health")
async def health_check():
    # Redis 연결 확인
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        redis_status = "ok"
    except:
        redis_status = "error"
    
    return {
        "status": "ok",
        "redis": redis_status,
        "version": "0.1.0"
    }
```

## 🔧 자동 배포 (GitHub Actions)

```yaml
# .github/workflows/deploy-ec2.yml
name: Deploy to EC2

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to EC2
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd ~/Silvertalk
            git pull
            source backend/venv/bin/activate
            pip install -r backend/requirements.ec2.txt
            sudo systemctl restart silvertalk-api
```
