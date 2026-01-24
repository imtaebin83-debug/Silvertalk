# 🚀 Git 저장소 설정 가이드

## 📋 체크리스트

### ✅ Push 전 확인사항

#### 1. 민감 정보 제거
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] API 키가 코드에 하드코딩되어 있지 않은지 확인
- [ ] 데이터베이스 비밀번호가 노출되지 않았는지 확인
- [ ] AWS 자격증명이 포함되지 않았는지 확인

#### 2. 불필요한 파일 제외
- [ ] `__pycache__/` 디렉토리
- [ ] `node_modules/` 디렉토리
- [ ] AI 모델 파일 (`backend/models/`)
- [ ] 개인 문서 (`personal-docs/`)
- [ ] 테스트 데이터 (`data/`)

#### 3. 문서 완성도
- [ ] `README.md` 업데이트
- [ ] `.env.example` 최신화
- [ ] `MAC_SETUP.md` 검토
- [ ] API 문서 (`docs/API_SPEC.md`) 확인

## 🔧 Git 초기화

### 기존 저장소가 없는 경우
```bash
# Git 초기화
git init

# 원격 저장소 추가
git remote add origin https://github.com/YOUR_USERNAME/silvertalk.git

# 현재 상태 확인
git status

# 모든 파일 추가 (.gitignore에 의해 제외된 파일은 자동 제외)
git add .

# 첫 커밋
git commit -m "feat: initial project setup with Docker and Poetry"

# Push
git branch -M main
git push -u origin main
```

### 기존 저장소가 있는 경우
```bash
# 원격 저장소 확인
git remote -v

# 최신 변경사항 Pull
git pull origin main

# 변경사항 추가
git add .
git commit -m "fix: resolve Docker build issues and add Poetry migration"
git push origin main
```

## 📂 저장소 구조

```
silvertalk/
├── .env.example          # ✅ 커밋 (환경 변수 템플릿)
├── .env                  # ❌ 제외 (.gitignore)
├── .gitignore            # ✅ 커밋
├── docker-compose.yml    # ✅ 커밋
├── README.md             # ✅ 커밋
│
├── backend/
│   ├── pyproject.toml        # ✅ 커밋 (Worker용 전체 의존성)
│   ├── pyproject.api.toml    # ✅ 커밋 (API용 간소화 의존성)
│   ├── poetry.lock           # ❌ 제외 (자동 생성)
│   ├── requirements.txt      # ✅ 커밋 (레거시 참고용)
│   ├── Dockerfile.api        # ✅ 커밋
│   ├── Dockerfile.worker     # ✅ 커밋
│   ├── models/               # ❌ 제외 (AI 모델 파일)
│   ├── data/                 # ❌ 제외 (업로드 파일)
│   │
│   ├── app/                  # ✅ 커밋 (FastAPI 애플리케이션)
│   ├── common/               # ✅ 커밋 (DB 모델, 유틸리티)
│   └── worker/               # ✅ 커밋 (Celery tasks)
│
├── mobile-app/
│   ├── package.json          # ✅ 커밋
│   ├── node_modules/         # ❌ 제외
│   ├── .expo/                # ❌ 제외
│   └── src/                  # ✅ 커밋
│
├── docs/                     # ✅ 커밋 (프로젝트 문서)
│   ├── API_SPEC.md
│   ├── DB_SCHEMA.md
│   ├── DOCKER_SETUP.md
│   ├── MAC_SETUP.md          # ✅ 새로 추가
│   └── SETUP.md
│
├── personal-docs/            # ❌ 제외 (개인 작업 문서)
│   ├── MVP_DECISIONS.md
│   └── NEXT_STEPS.md
│
└── data/                     # ❌ 제외 (런타임 데이터)
```

## 🔒 보안 주의사항

### 1. API 키 관리
```bash
# ❌ 절대 하지 말 것
GEMINI_API_KEY = "AIzaSyCwc1LihxUgkMBqJ9Gk1IqVl0Sw-muAd84"  # 코드에 직접 입력

# ✅ 올바른 방법
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # 환경 변수에서 로드
```

### 2. .env 파일 보호
```bash
# .env 파일이 실수로 추가되었는지 확인
git status

# 이미 커밋된 경우 히스토리에서 제거
git rm --cached .env
git commit -m "chore: remove .env from git history"

# .gitignore에 추가되어 있는지 재확인
cat .gitignore | grep ".env"
```

### 3. 민감한 파일 제거
```bash
# Git 히스토리에서 완전히 제거 (필요한 경우)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

## 🌿 브랜치 전략

### Main Branch
- 안정적인 프로덕션 코드
- 직접 Push 금지
- Pull Request를 통해서만 병합

### Feature Branch
```bash
# 새 기능 개발
git checkout -b feature/user-authentication
git checkout -b feature/voice-synthesis
git checkout -b feature/video-generation

# 작업 완료 후
git add .
git commit -m "feat: implement user authentication"
git push origin feature/user-authentication
```

### Fix Branch
```bash
# 버그 수정
git checkout -b fix/audio-upload-error
git checkout -b fix/database-connection

# 수정 완료 후
git add .
git commit -m "fix: resolve audio upload timeout issue"
git push origin fix/audio-upload-error
```

## 📝 Commit 메시지 컨벤션

### 형식
```
<type>: <subject>

<body> (optional)

<footer> (optional)
```

### Type
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅 (기능 변경 없음)
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 파일 수정

### 예시
```bash
feat: add voice synthesis with XTTS
fix: resolve Docker build PyAV compatibility issue
docs: update Mac setup guide
refactor: migrate from pip to Poetry for dependency management
chore: update .gitignore for Python and Docker
```

## 🔄 Pull Request 가이드

### PR 생성 전 체크리스트
- [ ] 로컬에서 테스트 완료
- [ ] Docker 빌드 성공
- [ ] 코드 리뷰 준비 완료
- [ ] 관련 문서 업데이트
- [ ] Conflict 해결 완료

### PR 템플릿
```markdown
## 변경 사항
- 주요 변경사항 요약

## 테스트
- 테스트 방법 설명

## 스크린샷 (UI 변경 시)
- Before/After 이미지

## 관련 이슈
- Closes #issue_number
```

## 🚨 긴급 대응

### 민감 정보 Push 시
```bash
# 1. 즉시 원격 저장소에서 삭제
git push --force origin HEAD^:main

# 2. API 키 등 즉시 재발급

# 3. Git 히스토리 정리
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <file>" \
  --prune-empty --tag-name-filter cat -- --all

# 4. 강제 Push
git push origin --force --all
```

## 📊 Git 상태 확인

```bash
# 현재 상태
git status

# 변경사항 확인
git diff

# 커밋 히스토리
git log --oneline --graph --all

# 원격 저장소 확인
git remote -v

# 브랜치 목록
git branch -a
```

## 🎯 팀원 초대 후 할 일

### 저장소 설정
1. GitHub Settings > Collaborators
2. 팀원 초대
3. 권한 설정 (Write 또는 Admin)

### Protected Branch 설정
1. Settings > Branches > Add rule
2. Branch name pattern: `main`
3. 설정:
   - ✅ Require pull request reviews
   - ✅ Require status checks to pass
   - ✅ Include administrators

### GitHub Actions (선택)
```yaml
# .github/workflows/docker-build.yml
name: Docker Build Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: docker-compose build
```

## 📞 지원

문제 발생 시:
1. `docs/MAC_SETUP.md` 확인
2. GitHub Issues 생성
3. 팀 채널에 문의

Happy Collaborating! 🤝