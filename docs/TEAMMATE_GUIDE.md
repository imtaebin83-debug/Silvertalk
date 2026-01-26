# 🤝 팀원용 가이드: S3 연동 작업 시작 전 읽어주세요

## 📢 알림: 프로덕션 인프라 변경 사항

저 (imtae)가 다음 작업을 완료했습니다:
- ✅ Upstash Redis (Tokyo) 연동
- ✅ RunPod GPU Worker 설정
- ✅ AWS RDS PostgreSQL 준비

**중요: 여러분의 로컬 개발 환경은 전혀 변경되지 않았습니다!** 🎯

## ✅ 변경되지 않은 것 (안심하고 계속 작업하세요)

### 로컬 개발 환경
```bash
# 기존 명령어 그대로 사용 가능
docker-compose up
docker-compose down
docker-compose logs -f
```

### 기존 파일들
- `docker-compose.yml` - 변경 없음 (로컬 Redis, PostgreSQL 그대로)
- `backend/Dockerfile.api` - 변경 없음
- `backend/Dockerfile.worker` - 변경 없음
- `backend/requirements.txt` - 변경 없음

### 로컬 서비스
```
localhost:8000 - FastAPI (그대로)
localhost:5432 - PostgreSQL (그대로)
localhost:6379 - Redis (그대로)
localhost:5555 - Flower (그대로)
```

## 🆕 추가된 것 (프로덕션 전용)

### 새로운 파일들 (무시해도 됨)
```
docker-compose.production.yml  # EC2 프로덕션 전용
backend/Dockerfile.runpod      # RunPod GPU Worker 전용
.env.ec2                        # EC2 환경 변수 (Git 제외)
.env.runpod                     # RunPod 환경 변수 (Git 제외)
.env.production.example         # 환경 변수 예시
docs/RUNPOD_SETUP.md            # RunPod 설정 가이드
docs/RUNPOD_DEPLOY.md           # RunPod 배포 가이드
docs/DEPLOYMENT_CHECKLIST.md    # 배포 체크리스트
docs/TEAMMATE_GUIDE.md          # 이 파일
```

### config.py 변경 사항
`backend/common/config.py`에 다음이 추가되었습니다:

```python
# 새로 추가된 필드 (프로덕션 전용)
DEPLOYMENT_MODE: str = "LOCAL"  # LOCAL or CLOUD
STORAGE_BACKEND: str = "LOCAL"  # LOCAL or S3
RUNPOD_SSH_HOST: Optional[str] = None
RUNPOD_SSH_PORT: Optional[int] = None
RUNPOD_SSH_KEY_PATH: Optional[str] = None
UPSTASH_REDIS_URL: Optional[str] = None
PROD_DATABASE_URL: Optional[str] = None

# 동적 속성 (로컬 개발에는 영향 없음)
@property
def redis_url(self):
    if self.DEPLOYMENT_MODE == "CLOUD" and self.UPSTASH_REDIS_URL:
        return self.UPSTASH_REDIS_URL
    return self.REDIS_URL  # 로컬 Redis (기존)

@property
def database_url(self):
    if self.DEPLOYMENT_MODE == "CLOUD" and self.PROD_DATABASE_URL:
        return self.PROD_DATABASE_URL
    return self.DATABASE_URL  # 로컬 PostgreSQL (기존)
```

**로컬 환경에서는 자동으로 기존 설정 사용됩니다.**

## 🎯 S3 연동 작업 시작하기

### 1. 최신 코드 Pull
```bash
cd c:\Users\imtae\OneDrive\바탕 화면\2026madcamp\silvertalk
git pull origin main  # 또는 feature/runpod-upstash
```

### 2. S3 패키지 설치 (로컬에서)
```bash
# backend 디렉토리로 이동
cd backend

# boto3 설치 (Poetry 사용)
poetry add boto3

# 또는 requirements.txt에 추가
echo "boto3>=1.34.0" >> requirements.txt
pip install boto3
```

### 3. S3 설정 코드 작성

#### 3.1. S3 클라이언트 생성
`backend/common/s3_client.py` 파일 생성:

```python
import boto3
from botocore.exceptions import ClientError
from .config import settings

def get_s3_client():
    """S3 클라이언트 생성"""
    if settings.STORAGE_BACKEND != "S3":
        return None
    
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def upload_file_to_s3(file_path: str, s3_key: str, bucket: str = None) -> str:
    """파일을 S3에 업로드하고 URL 반환"""
    if bucket is None:
        bucket = settings.S3_BUCKET_NAME
    
    s3_client = get_s3_client()
    if s3_client is None:
        raise ValueError("S3 is not configured")
    
    try:
        s3_client.upload_file(file_path, bucket, s3_key)
        url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        return url
    except ClientError as e:
        raise Exception(f"S3 upload failed: {str(e)}")

def download_file_from_s3(s3_key: str, local_path: str, bucket: str = None):
    """S3에서 파일 다운로드"""
    if bucket is None:
        bucket = settings.S3_BUCKET_NAME
    
    s3_client = get_s3_client()
    if s3_client is None:
        raise ValueError("S3 is not configured")
    
    try:
        s3_client.download_file(bucket, s3_key, local_path)
    except ClientError as e:
        raise Exception(f"S3 download failed: {str(e)}")
```

#### 3.2. 환경 변수 추가
`.env` 파일 (로컬 개발용):

```bash
# S3 설정 (로컬 테스트용)
STORAGE_BACKEND=LOCAL  # 로컬에서는 LOCAL 유지
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=silvertalk-prod
```

#### 3.3. Router에서 S3 사용
`backend/app/routers/gallery.py` 수정 예시:

```python
from common.s3_client import upload_file_to_s3
from common.config import settings

@router.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    # 1. 임시 파일 저장
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # 2. S3 업로드 (프로덕션) 또는 로컬 저장 (개발)
    if settings.STORAGE_BACKEND == "S3":
        s3_key = f"photos/{user_id}/{photo_id}.jpg"
        photo_url = upload_file_to_s3(temp_path, s3_key)
    else:
        # 로컬 저장 (기존 방식)
        photo_url = f"./data/photos/{photo_id}.jpg"
        shutil.copy(temp_path, photo_url)
    
    # 3. DB에 URL 저장
    photo = Photo(id=photo_id, url=photo_url, user_id=user_id)
    db.add(photo)
    db.commit()
    
    return {"photo_url": photo_url}
```

### 4. 로컬 테스트

```bash
# Docker 다시 시작 (boto3 설치 반영)
docker-compose down
docker-compose build
docker-compose up

# API 테스트
curl -X POST http://localhost:8000/gallery/upload \
  -F "file=@test_photo.jpg" \
  -F "user_id=test-user"

# 로그 확인
docker logs silvertalk-worker -f
```

### 5. Git Commit & Push

```bash
git add backend/common/s3_client.py
git add backend/app/routers/gallery.py
git add backend/requirements.txt  # boto3 추가된 경우
git commit -m "feat: add S3 integration for photo storage"
git push origin main
```

## ⚠️ 주의사항

### 1. .env 파일 관리
```bash
# 절대 커밋하지 말 것!
.env
.env.ec2
.env.runpod
.env.production

# 커밋해도 됨 (예시 파일)
.env.example
.env.production.example
```

### 2. 로컬과 프로덕션 분리
```python
# config.py의 동적 설정 활용
if settings.STORAGE_BACKEND == "S3":
    # S3 사용 (프로덕션)
    upload_to_s3()
else:
    # 로컬 파일 시스템 (개발)
    save_locally()
```

### 3. EC2에서 S3 Role 사용 (추천)
EC2 IAM Role을 사용하면 Access Key 불필요:

```python
# EC2에서는 자동으로 Role 사용
s3_client = boto3.client('s3')  # Access Key 없이 가능
```

## 📊 작업 흐름도

```
[로컬 개발]
1. Git Pull
2. boto3 설치
3. s3_client.py 작성
4. Router에서 S3 함수 호출
5. 로컬 테스트 (STORAGE_BACKEND=LOCAL)
6. Git Commit & Push

[EC2 배포 - imtae 담당]
1. EC2에서 Git Pull
2. .env.ec2에 S3 설정 추가
   STORAGE_BACKEND=S3
   S3_BUCKET_NAME=silvertalk-prod
3. IAM Role 연결 (Access Key 대신)
4. 서비스 재시작
5. 프로덕션 테스트
```

## 🎯 완료 기준

- [x] S3 클라이언트 코드 작성
- [x] Gallery Router에 S3 업로드 함수 통합
- [x] 로컬 테스트 성공 (STORAGE_BACKEND=LOCAL)
- [x] Git Push 완료

**프로덕션 배포는 제가 (imtae) 담당하니 신경 쓰지 마세요!**

## 💬 소통

작업 중 궁금한 점:
1. Discord/Slack에 메시지
2. Git Issues 등록
3. 코드 리뷰 요청 (PR)

**화이팅! S3 연동 작업 응원합니다!** 🚀

---

## 📚 참고 자료

- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)
- 로컬 테스트: `STORAGE_BACKEND=LOCAL` 유지
- 프로덕션: imtae가 `STORAGE_BACKEND=S3` 설정