# RunPod 웹 터미널 문제 해결 가이드

## 🔍 진단 체크리스트

### 1. Pod 상태 확인
**RunPod Dashboard → Pods → territorial_amaranth_mastodon**

#### 확인 사항:
```
[ ] Status: Running (초록색)
[ ] GPU: RTX 3090 Allocated
[ ] Uptime: 표시됨
[ ] CPU/GPU 사용률: 표시됨
```

**문제별 해결:**
- **Stopped**: Start 버튼 클릭 → 2-3분 대기
- **Error**: Logs 탭에서 에러 확인 → Pod 재생성 필요할 수 있음
- **Exited**: Container 시작 실패 → Template 문제

---

### 2. 웹 터미널 활성화 재시도

#### Step 1: 브라우저 캐시 삭제
```
Ctrl+Shift+Delete → 캐시 삭제 → 새로고침
```

#### Step 2: Connect 탭 확인
```
Connect → Web terminal
→ "Enable web terminal" 토글 클릭
→ 5-10초 대기
```

**증상별 대응:**
- **바로 꺼짐**: Pod이 실제로 Running이 아님 → Status 재확인
- **로딩 무한**: 브라우저 문제 → 다른 브라우저 시도 (Chrome/Edge)
- **에러 메시지**: 메시지 내용 확인 → 로그 확인

---

### 3. SSH 접속 (PowerShell 대체 방법)

#### 방법 A: OpenSSH 명령어 (Windows 10/11)
```powershell
# RunPod 프록시 사용
ssh j9n3oy15dyy0xd-64411cc3@ssh.runpod.io -i $env:USERPROFILE\.ssh\id_ed25519

# 또는 비밀번호 방식 (RunPod Connect 탭에서 비밀번호 확인)
ssh j9n3oy15dyy0xd-64411cc3@ssh.runpod.io
```

#### 방법 B: PuTTY 사용 (GUI)
```
1. PuTTY 다운로드: https://www.putty.org/
2. Host Name: j9n3oy15dyy0xd-64411cc3@ssh.runpod.io
3. Port: 22
4. Connection Type: SSH
5. Auth → Private key file: C:\Users\imtae\.ssh\id_ed25519 (Convert to .ppk)
6. Open
```

#### 방법 C: VSCode Remote SSH
```
1. VSCode 설치
2. "Remote - SSH" Extension 설치
3. Ctrl+Shift+P → "Remote-SSH: Connect to Host"
4. j9n3oy15dyy0xd-64411cc3@ssh.runpod.io 입력
5. SSH Key 자동 인식
```

---

### 4. Pod 재시작 (최후의 수단)

#### Option 1: Soft Restart
```
RunPod Dashboard → Pod 우측 메뉴
→ Restart
→ 2-3분 대기
```

#### Option 2: Stop & Start
```
1. Stop 버튼 클릭
2. Status: Stopped 확인
3. Start 버튼 클릭
4. Status: Running 대기 (2-3분)
5. 웹 터미널 재시도
```

#### Option 3: Pod 재생성 (데이터 손실!)
```
⚠️ 주의: 저장된 데이터 모두 삭제됨

1. Terminate 버튼 클릭
2. Deploy 버튼 → 새 Pod 생성
3. Template: Runpod Pytorch 2.1
4. GPU: RTX 3090
5. Deploy
6. 코드 재설치 필요
```

---

## 🚀 추천 순서

### 즉시 시도:
1. **Pod Status 재확인** (Running인지)
2. **브라우저 새로고침** (Ctrl+Shift+R)
3. **다른 브라우저** (Chrome → Edge 또는 반대)

### 그래도 안 되면:
4. **Pod Restart** (Soft Restart)
5. **SSH 접속 시도** (PowerShell)

### 마지막 수단:
6. **VSCode Remote SSH** (가장 안정적)
7. **Pod 재생성** (데이터 손실 감수)

---

## 💡 SSH 접속 성공 시 할 일

```bash
# 1. GPU 확인
nvidia-smi

# 2. 코드 확인
cd /workspace
ls -la

# 3. 저장소 클론 (없으면)
git clone https://github.com/imtaebin83-debug/Silvertalk.git
cd Silvertalk/backend

# 4. 환경 변수 설정
nano .env
# (Ctrl+O 저장, Ctrl+X 종료)

# 5. 의존성 설치
apt-get update
apt-get install -y pkg-config libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev ffmpeg libsndfile1 screen
pip install -r requirements.txt

# 6. Celery Worker 시작
celery -A worker.celery_app worker --loglevel=info --concurrency=2 --queues=ai_tasks
```

---

## 📞 RunPod Support

문제가 계속되면:
```
RunPod Dashboard → 우측 하단 Help 아이콘
→ "Chat with Support"
→ "Web terminal not working" 문의
```

---

## 🎯 현재 상황별 대응

### Case 1: Pod이 Stopped 상태
```
→ Start 버튼 클릭
→ 2-3분 대기
→ Running 상태 확인
→ 웹 터미널 재시도
```

### Case 2: Pod은 Running인데 터미널만 안 됨
```
→ SSH 접속 시도 (PowerShell)
→ VSCode Remote SSH 사용 (추천!)
→ 또는 PuTTY
```

### Case 3: SSH도 안 되고 터미널도 안 됨
```
→ Pod Logs 탭 확인
→ 에러 메시지 확인
→ Pod Restart
→ 또는 Support 문의
```

---

**가장 빠른 해결책: VSCode Remote SSH 사용!** 🚀
