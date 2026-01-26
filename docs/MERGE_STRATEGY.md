# 팀원 S3+RDS Push 전 Merge 전략

## 🔥 현재 상황
- **나 (imtae)**: RunPod + Upstash 설정 완료, config.py 수정
- **팀원**: S3 + RDS 설정 완료, 곧 push 예정

## ⚠️ 충돌 예상 파일

### 1. `backend/common/config.py` (HIGH 충돌 가능성)
**내 변경사항:**
```python
DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "LOCAL")
STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "LOCAL")

@property
def redis_url(self):
    if self.DEPLOYMENT_MODE == "CLOUD":
        return os.getenv("UPSTASH_REDIS_URL", "")
    else:
        return os.getenv("LOCAL_REDIS_URL", "redis://localhost:6379/0")

@property
def database_url(self):
    if self.DEPLOYMENT_MODE == "CLOUD":
        return os.getenv("PROD_DATABASE_URL", "")
    else:
        return os.getenv("LOCAL_DATABASE_URL", "")
```

**팀원이 추가했을 가능성:**
```python
# S3 설정
AWS_ACCESS_KEY_ID: str
AWS_SECRET_ACCESS_KEY: str
S3_BUCKET_NAME: str

# RDS 설정
DATABASE_URL: str = "postgresql://rds-endpoint..."
```

### 2. `backend/requirements.txt` (MEDIUM 충돌)
**팀원이 추가했을 것:**
```
boto3==1.34.34
```

**내 파일:** boto3 주석 처리됨

### 3. `.env` 파일들 (LOW 충돌, 하지만 중요)
- 팀원이 `.env` 또는 `.env.example` 수정했을 가능성
- 내가 `.env.ec2`, `.env.runpod` 추가

## ✅ Merge 전략 (3단계)

### Phase 1: 팀원 Push 전 소통 (지금 당장!)

**팀원에게 메시지:**
```
"S3 + RDS push 전에 잠깐!
나도 config.py 수정했어서 충돌날 수 있어.

네가 push하기 전에:
1. 어떤 파일 수정했는지 리스트 좀 보내줘
2. config.py에 뭐 추가했는지 확인하고 싶어
3. DATABASE_URL을 직접 설정했는지 환경 변수로 했는지

내가 먼저 커밋 안 하고 기다릴게!"
```

### Phase 2: 파일별 Merge 계획

#### A. 팀원이 먼저 Push하는 경우 (추천)

```bash
# 1. 내 현재 변경사항 백업
git stash save "runpod-upstash-changes"

# 2. 팀원 변경사항 Pull
git pull origin main

# 3. 충돌 파일 확인
git status

# 4. config.py 수동 병합
# - 팀원의 S3/RDS 설정 유지
# - 내 DEPLOYMENT_MODE, redis_url/database_url @property 추가
# - 중복 제거

# 5. requirements.txt 병합
# - boto3 주석 해제

# 6. 내 변경사항 복원
git stash pop

# 7. 충돌 해결 후 커밋
git add .
git commit -m "merge: integrate RunPod setup with S3+RDS config"
git push origin main
```

#### B. 내가 먼저 Push하는 경우

```bash
# 1. 내 변경사항 커밋 (지금)
git add .
git commit -m "feat: add RunPod + Upstash configuration"
git push origin main

# 2. 팀원에게 알림
"push 했어! config.py 수정했으니 충돌 날 거야.
내가 추가한 부분:
- DEPLOYMENT_MODE
- @property redis_url, database_url
네 S3/RDS 설정이랑 합쳐줘!"

# 3. 팀원이 pull 시 충돌 해결
# (팀원이 수동 병합)
```

### Phase 3: 병합 후 최종 config.py 형태

```python
class Settings(BaseSettings):
    # 환경 구분
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "LOCAL")  # 내가 추가
    
    # Redis (동적 선택)
    @property
    def redis_url(self) -> str:  # 내가 추가
        if self.DEPLOYMENT_MODE == "CLOUD":
            return os.getenv("UPSTASH_REDIS_URL", "")
        else:
            return os.getenv("LOCAL_REDIS_URL", "redis://localhost:6379/0")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # AWS & S3 (팀원이 추가)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-1")  # Tokyo
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "LOCAL")  # 내가 추가
    
    # Database (동적 선택)
    @property
    def database_url(self) -> str:  # 내가 추가
        if self.DEPLOYMENT_MODE == "CLOUD":
            return os.getenv("PROD_DATABASE_URL", "")
        else:
            return os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/silvertalk")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # 팀원이 RDS로 설정했을 수도
    
    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # RunPod (내가 추가)
    RUNPOD_POD_ID: str = os.getenv("RUNPOD_POD_ID", "")
    RUNPOD_API_KEY: str = os.getenv("RUNPOD_API_KEY", "")
```

## 🎯 최종 환경 변수 통합

### `.env.ec2` (EC2 FastAPI 서버)
```bash
# 배포 모드
DEPLOYMENT_MODE=CLOUD

# Redis (Upstash)
UPSTASH_REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379

# Database (RDS - 팀원 제공)
PROD_DATABASE_URL=postgresql://admin:password@silvertalk-rds.xxxxx.ap-northeast-1.rds.amazonaws.com:5432/silvertalk

# S3 (팀원 제공)
STORAGE_BACKEND=S3
AWS_ACCESS_KEY_ID=AKIAxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxx
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=silvertalk-prod

# Gemini API
GEMINI_API_KEY=your_key
```

### `.env.runpod` (RunPod Worker)
```bash
# 위와 동일 + GPU 설정
DEPLOYMENT_MODE=CLOUD
CUDA_VISIBLE_DEVICES=0

UPSTASH_REDIS_URL=rediss://...
PROD_DATABASE_URL=postgresql://...
STORAGE_BACKEND=S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=silvertalk-prod
GEMINI_API_KEY=...
```

## 📋 Merge 체크리스트

### 병합 전
- [ ] 팀원과 수정 파일 리스트 공유
- [ ] config.py 변경사항 상세 확인
- [ ] DATABASE_URL 실제 값 확인 (RDS 엔드포인트)
- [ ] S3 버킷 이름 확인
- [ ] boto3 requirements.txt 추가 확인

### 병합 중
- [ ] git stash 또는 branch 전략 선택
- [ ] config.py 수동 병합 (모든 설정 유지)
- [ ] requirements.txt boto3 추가
- [ ] .env.example 통합

### 병합 후
- [ ] 로컬 docker-compose up 테스트
- [ ] config.py import 에러 없는지 확인
- [ ] S3 업로드 테스트 (팀원 코드)
- [ ] Redis 연결 테스트
- [ ] Git Push

## 🚀 추천 순서

**가장 안전한 방법:**
```
1. 팀원 먼저 Push (S3 + RDS)
2. 나 Pull + 수동 병합
3. 충돌 해결 (config.py 주의)
4. 로컬 테스트
5. Push
```

이유: 팀원이 S3 코드까지 완성했으니 기능 우선 반영하고, 내 인프라 설정을 그 위에 추가하는 게 안전합니다.

## 💬 팀원과 공유할 메시지 템플릿

```
안녕! S3 + RDS 작업 고생했어 👏

push 하기 전에 확인:
1. config.py 어떤 필드 추가했는지 알려줘
2. DATABASE_URL을 직접 설정했는지 환경 변수로 했는지
3. requirements.txt에 boto3 추가했는지

나는 다음 추가했어:
- DEPLOYMENT_MODE (LOCAL/CLOUD)
- @property redis_url (Upstash 자동 선택)
- @property database_url (RDS 자동 선택)
- RunPod 설정

충돌 날 거 같으니 네가 먼저 push하고 내가 병합할게!
DATABASE_URL, S3 설정 정보 공유 부탁해~
```
