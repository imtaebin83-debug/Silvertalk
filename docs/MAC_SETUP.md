# 🍎 Mac 환경 세팅 가이드

## 📋 사전 요구사항

### 필수 설치 항목
```bash
# 1. Homebrew 설치 (Mac 패키지 매니저)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Docker Desktop for Mac 설치
# https://www.docker.com/products/docker-desktop 에서 다운로드
# 또는 Homebrew로 설치:
brew install --cask docker

# 3. Git 설치 (보통 기본 설치되어 있음)
brew install git

# 4. Node.js & npm 설치 (모바일 앱 개발용)
brew install node

# 5. Watchman 설치 (React Native 필수)
brew install watchman
```

## 🚀 프로젝트 초기 세팅

### 1. 저장소 클론
```bash
git clone https://github.com/YOUR_USERNAME/silvertalk.git
cd silvertalk
```

### 2. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (nano, vim, VS Code 등 사용)
nano .env
```

**필수 설정:**
- `GEMINI_API_KEY`: Google AI Studio에서 발급 (https://makersuite.google.com/app/apikey)

### 3. Docker 실행 확인
```bash
# Docker Desktop이 실행 중인지 확인
docker --version
docker-compose --version

# Docker Desktop 앱을 실행하세요
```

### 4. 프로젝트 빌드 및 실행
```bash
# 모든 서비스 빌드 및 시작
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build
```

### 5. 서비스 확인
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📱 모바일 앱 개발 환경

### React Native 개발 도구 설치
```bash
cd mobile-app

# 의존성 설치
npm install

# 또는 yarn 사용
yarn install

# Expo CLI 전역 설치
npm install -g expo-cli

# 개발 서버 시작
npm start
# 또는
expo start
```

### iOS 시뮬레이터 (Mac 전용)
```bash
# Xcode 설치 (App Store에서)
# Command Line Tools 설치
xcode-select --install

# iOS 시뮬레이터에서 실행
expo start --ios
```

### Android 에뮬레이터
```bash
# Android Studio 설치 필요
# https://developer.android.com/studio

# Android 에뮬레이터에서 실행
expo start --android
```

## 🔧 Mac 특정 이슈 해결

### Docker Desktop 메모리 설정
```bash
# Docker Desktop > Preferences > Resources
# 권장 설정:
# - CPUs: 4개 이상
# - Memory: 8GB 이상 (AI Worker용)
# - Swap: 2GB
# - Disk image size: 60GB 이상
```

### M1/M2/M3 Mac (Apple Silicon) 사용자
```bash
# Docker 이미지 빌드 시 --platform 옵션 필요할 수 있음
# docker-compose.yml에 이미 설정되어 있으나, 문제 발생 시:
docker-compose build --platform linux/amd64

# Rosetta 2 활성화
softwareupdate --install-rosetta
```

### Permission 에러 해결
```bash
# data 디렉토리 권한 설정
chmod -R 755 data/

# Docker 볼륨 마운트 권한 문제 시
sudo chown -R $(whoami) backend/data
```

### 포트 충돌 해결
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8000  # API 서버
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 프로세스 종료
kill -9 <PID>
```

## 🐳 Docker 명령어 모음

### 기본 명령어
```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f web
docker-compose logs -f worker

# 컨테이너 재시작
docker-compose restart web

# 완전히 정리하고 재빌드
docker-compose down -v
docker-compose up --build
```

### 디버깅
```bash
# 컨테이너 접속
docker exec -it silvertalk-web bash
docker exec -it silvertalk-worker bash

# 데이터베이스 접속
docker exec -it silvertalk-postgres psql -U silvertalk

# Python 패키지 확인
docker exec silvertalk-web pip list
docker exec silvertalk-worker pip list
```

## 📝 개발 워크플로우

### 1. 브랜치 전략
```bash
# 새 기능 개발
git checkout -b feature/your-feature-name

# 작업 후 커밋
git add .
git commit -m "feat: add new feature"

# Push
git push origin feature/your-feature-name
```

### 2. 코드 변경 시
```bash
# 백엔드 코드 변경 시 (자동 리로드)
# - docker-compose.yml에 볼륨 마운트 설정되어 있음
# - 파일 저장하면 자동으로 반영됨

# Docker 이미지 재빌드 필요한 경우:
# - requirements.txt 변경
# - pyproject.toml 변경
# - Dockerfile 변경
docker-compose build web worker
docker-compose up -d
```

### 3. 데이터베이스 마이그레이션
```bash
# Alembic 마이그레이션 생성
docker exec silvertalk-web alembic revision --autogenerate -m "description"

# 마이그레이션 적용
docker exec silvertalk-web alembic upgrade head
```

## ⚠️ 주의사항

### 1. .env 파일 관리
- ❌ `.env` 파일은 절대 Git에 커밋하지 마세요
- ✅ `.env.example`만 커밋하세요
- ✅ 팀원마다 자신의 `.env` 파일을 생성하세요

### 2. AI 모델 파일
- `backend/models/` 디렉토리는 Git에서 제외됨
- 첫 실행 시 Worker가 자동으로 모델을 다운로드합니다
- 인터넷 연결 필요 (Faster-Whisper, XTTS 모델 다운로드)

### 3. GPU 설정
- Mac 로컬 개발: CPU 모드로 자동 실행
- 프로덕션 배포: AWS EC2 GPU 인스턴스 사용
- `docker-compose.yml`의 `CUDA_VISIBLE_DEVICES` 환경 변수로 제어

### 4. 볼륨 데이터
- `data/` 디렉토리: 업로드된 파일, 생성된 오디오 저장
- 개발 중 데이터 초기화 필요 시: `rm -rf data/*`

## 🆘 문제 해결

### Q: Docker 빌드가 너무 느려요
```bash
# Docker BuildKit 활성화
export DOCKER_BUILDKIT=1

# 캐시 사용하여 빌드
docker-compose build

# 캐시 없이 완전히 새로 빌드 (문제 발생 시)
docker-compose build --no-cache
```

### Q: Worker에서 "No module named 'torch'" 에러
```bash
# Worker 컨테이너 재빌드
docker-compose build --no-cache worker
docker-compose up -d worker

# 로그 확인
docker logs silvertalk-worker
```

### Q: API가 응답하지 않아요
```bash
# 로그 확인
docker logs silvertalk-web

# 컨테이너 상태 확인
docker-compose ps

# 재시작
docker-compose restart web
```

### Q: PostgreSQL 연결 에러
```bash
# PostgreSQL 헬스체크 확인
docker-compose ps

# 데이터베이스 재시작
docker-compose restart postgres

# 데이터 초기화 (주의: 모든 데이터 삭제)
docker-compose down -v
docker-compose up -d
```

## 📚 추가 리소스

- **FastAPI 문서**: https://fastapi.tiangolo.com
- **React Native 문서**: https://reactnative.dev
- **Docker 문서**: https://docs.docker.com
- **Celery 문서**: https://docs.celeryq.dev
- **Google Gemini API**: https://ai.google.dev/gemini-api/docs

## 💬 팀 커뮤니케이션

문제가 발생하면:
1. 로그 확인 (`docker-compose logs`)
2. GitHub Issues에 등록
3. 팀 채널에 공유

Happy Coding! 🚀