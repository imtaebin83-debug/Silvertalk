# 🐳 Docker 초기 설정 가이드

## 📋 현재 상황
- ✅ Docker 설치 완료
- ✅ GEMINI_API_KEY 설정 완료 (`.env.example` 확인됨)
- ⏳ 컨테이너 미생성 상태
- ⏳ AWS EC2 미연결 (로컬 개발 환경)

## 🚀 단계별 Docker 설정

### 1단계: 환경 변수 파일 생성

```powershell
# PowerShell에서 실행
cd "c:\Users\imtae\OneDrive\바탕 화면\2026madcamp\silvertalk"

# .env 파일이 이미 있는지 확인
if (Test-Path .env) {
    Write-Host "✅ .env 파일이 이미 존재합니다."
} else {
    Copy-Item .env.example .env
    Write-Host "✅ .env 파일이 생성되었습니다."
}
```

**중요:** `.env` 파일에 GEMINI_API_KEY가 올바르게 설정되어 있는지 다시 확인하세요!

### 2단계: Docker Desktop 실행 확인

```powershell
# Docker 데몬이 실행 중인지 확인
docker ps
```

**오류 발생 시:**
- Docker Desktop이 실행되지 않았다면: Windows 시작 메뉴에서 "Docker Desktop" 실행
- WSL 2 오류 발생 시: [WSL 2 설치 가이드](https://docs.microsoft.com/ko-kr/windows/wsl/install) 참조

### 3단계: Docker 이미지 빌드

```powershell
# 프로젝트 디렉토리로 이동
cd "c:\Users\imtae\OneDrive\바탕 화면\2026madcamp\silvertalk"

# 컨테이너 빌드 (첫 실행 시 10-15분 소요)
docker-compose build
```

**빌드 중 발생 가능한 이슈:**

#### ❌ 이슈 1: "no configuration file provided"
```powershell
# 해결: docker-compose.yml 파일 위치 확인
ls docker-compose.yml
```

#### ❌ 이슈 2: PyTorch 다운로드 타임아웃
```yaml
# backend/Dockerfile.worker 수정 (타임아웃 늘리기)
ENV PIP_DEFAULT_TIMEOUT=100
```

#### ❌ 이슈 3: 디스크 공간 부족
```powershell
# Docker 이미지/컨테이너 정리
docker system prune -a
```

### 4단계: 컨테이너 실행

```powershell
# 백그라운드 실행 (권장)
docker-compose up -d

# 또는 로그를 보면서 실행 (디버깅용)
docker-compose up
```

**실행 중 확인사항:**
- ✅ Redis 컨테이너: 5초 내 시작
- ✅ PostgreSQL 컨테이너: 10초 내 시작
- ✅ Web 컨테이너: 30초 내 시작
- ⚠️ Worker 컨테이너: **3-5분 소요** (AI 모델 다운로드)

### 5단계: 컨테이너 상태 확인

```powershell
# 실행 중인 컨테이너 확인
docker-compose ps

# 예상 출력:
# NAME                   STATUS              PORTS
# silvertalk-web         Up 2 minutes        0.0.0.0:8000->8000/tcp
# silvertalk-worker      Up 2 minutes
# silvertalk-redis       Up 2 minutes        0.0.0.0:6379->6379/tcp
# silvertalk-postgres    Up 2 minutes        0.0.0.0:5432->5432/tcp
# silvertalk-flower      Up 2 minutes        0.0.0.0:5555->5555/tcp
```

### 6단계: 로그 확인

```powershell
# 전체 로그 확인
docker-compose logs

# Worker 로그만 확인 (AI 모델 로딩 상태)
docker-compose logs -f worker

# 예상 로그:
# ✅ "💻 GPU 미감지 - CPU 모드로 실행"
# ✅ "✅ Whisper 모델 로딩 완료"
# ✅ "✅ XTTS 모델 로딩 완료"
# ✅ "✅ Gemini 1.5 Flash 초기화 완료"
```

### 7단계: 서비스 접속 테스트

#### 7.1. API 서버 테스트
```powershell
# PowerShell에서 실행
Invoke-WebRequest -Uri http://localhost:8000/health -Method GET

# 또는 브라우저에서 접속
# http://localhost:8000
# http://localhost:8000/docs (Swagger UI)
```

#### 7.2. Flower 대시보드 접속
브라우저에서: http://localhost:5555

#### 7.3. 데이터베이스 연결 테스트
```powershell
# PostgreSQL 컨테이너 접속
docker exec -it silvertalk-postgres psql -U silvertalk -d silvertalk

# SQL 쿼리 실행
\dt  # 테이블 목록 확인
SELECT version();  # PostgreSQL 버전 확인
\q  # 종료
```

## 🐛 트러블슈팅

### 문제 1: Worker 컨테이너가 계속 재시작됨
```powershell
# Worker 로그 확인
docker-compose logs worker

# 일반적인 원인:
# 1. GEMINI_API_KEY 누락 -> .env 파일 확인
# 2. Redis 연결 실패 -> redis 컨테이너 상태 확인
# 3. 모델 다운로드 실패 -> 네트워크 확인
```

**해결책:**
```powershell
# 컨테이너 재시작
docker-compose restart worker

# 완전 재빌드 (캐시 무시)
docker-compose build --no-cache worker
docker-compose up -d
```

### 문제 2: "Port already in use" 오류
```powershell
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# 해결: docker-compose.yml에서 포트 변경
# 예: 8000 -> 8001
```

### 문제 3: Windows Defender 방화벽 경고
- "액세스 허용" 클릭 (Docker 컨테이너 네트워크 통신 필요)

### 문제 4: WSL 2 메모리 과다 사용
**`.wslconfig` 파일 생성** (`C:\Users\imtae\.wslconfig`):
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

그 후:
```powershell
wsl --shutdown
# Docker Desktop 재시작
```

## 📊 리소스 사용량 모니터링

```powershell
# 컨테이너별 리소스 사용량
docker stats

# 예상 리소스:
# - redis: ~10MB
# - postgres: ~50MB
# - web: ~200MB
# - worker: ~2-4GB (AI 모델 로딩 후)
# - flower: ~100MB
```

## 🔄 일상적인 Docker 명령어

### 컨테이너 시작/종료
```powershell
# 시작
docker-compose up -d

# 종료
docker-compose down

# 종료 + 볼륨 삭제 (데이터베이스 초기화)
docker-compose down -v
```

### 로그 확인
```powershell
# 실시간 로그 추적
docker-compose logs -f

# 특정 서비스만
docker-compose logs -f worker
docker-compose logs -f web

# 최근 100줄만
docker-compose logs --tail=100
```

### 컨테이너 내부 접속
```powershell
# Worker 컨테이너 Bash 접속
docker exec -it silvertalk-worker bash

# 내부에서 Python 실행 가능
python -c "import torch; print(torch.cuda.is_available())"
exit
```

### 데이터베이스 백업
```powershell
# PostgreSQL 백업
docker exec -t silvertalk-postgres pg_dumpall -c -U silvertalk > backup.sql

# 복원
cat backup.sql | docker exec -i silvertalk-postgres psql -U silvertalk
```

## ⚡ 성능 최적화 팁

### 1. Docker 이미지 레이어 캐싱
- `requirements.txt` 변경 없이 코드만 수정한 경우: 빌드 시간 단축
- 의존성 추가 시: `docker-compose build` 재실행 필요

### 2. AI 모델 영구 저장
```yaml
# docker-compose.yml에 이미 설정됨
volumes:
  - ./backend/models:/app/models  # 모델 재다운로드 방지
```

### 3. 개발 시 Hot Reload
```yaml
# docker-compose.yml에 이미 설정됨
volumes:
  - ./backend:/app  # 코드 변경 시 자동 반영
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📝 다음 단계

1. ✅ Docker 컨테이너 실행 확인
2. ⏭️ API 테스트 (Swagger UI 또는 cURL)
3. ⏭️ React Native 앱 개발 시작
4. ⏭️ GitHub에 코드 푸시
5. ⏭️ AWS EC2 배포 준비

## 🆘 도움이 필요한 경우

### 로그 수집 방법
```powershell
# 전체 로그를 파일로 저장
docker-compose logs > docker_logs.txt

# 시스템 정보 수집
docker version > system_info.txt
docker-compose version >> system_info.txt
wsl --version >> system_info.txt
```

### 완전 초기화 (문제 발생 시)
```powershell
# 모든 컨테이너/이미지/볼륨 삭제
docker-compose down -v
docker system prune -a

# 재시작
docker-compose build
docker-compose up -d
```

---

**이제 Docker가 실행되면 다음 명령어로 API를 테스트해보세요:**

```powershell
# 헬스체크
curl http://localhost:8000/health

# 또는 브라우저에서
# http://localhost:8000/docs
```

**축하합니다! 🎉 Docker 설정이 완료되었습니다!**
