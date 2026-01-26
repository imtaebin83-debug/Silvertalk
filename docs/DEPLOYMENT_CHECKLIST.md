# 🎯 RunPod + Upstash 통합 완료 체크리스트

## ✅ 완료된 작업

### 1. 아키텍처 설계
- [x] EC2 + RunPod + Upstash Redis 아키텍처 확정
- [x] RDS PostgreSQL 사용 결정
- [x] SSL/TLS 보안 연결 설정

### 2. 환경 변수 파일 생성
- [x] `.env.production.example` - 프로덕션 템플릿
- [x] `.env.ec2` - EC2 전용 설정
- [x] `.env.runpod` - RunPod Worker 전용 설정
- [x] `.gitignore` 업데이트 (실제 환경 변수 보호)

### 3. Docker 설정
- [x] `Dockerfile.runpod` - RunPod GPU 환경 전용
- [x] `docker-compose.production.yml` - EC2 프로덕션 환경
- [x] 로컬 개발 환경 유지 (팀원 영향 없음)

### 4. 문서 작성
- [x] `docs/RUNPOD_SETUP.md` - RunPod Pod 생성 가이드
- [x] `docs/RUNPOD_DEPLOY.md` - Worker 배포 상세 가이드
- [x] `docs/DEPLOYMENT_CHECKLIST.md` (이 파일)

### 5. 코드 수정
- [x] `backend/common/config.py` - 환경별 자동 설정
- [x] SSL/TLS 지원 (rediss://)
- [x] RDS 연결 지원

## 🔄 진행 중인 작업

### 팀원 작업 (S3 연동)
- [ ] boto3 설치
- [ ] S3 업로드 함수 구현
- [ ] EC2 → S3 연결 테스트

### 당신의 다음 작업
1. [ ] **RDS PostgreSQL 생성**
   - AWS Console → RDS
   - Free Tier db.t3.micro
   - 퍼블릭 접근 활성화
   - 보안 그룹 설정

2. [ ] **RunPod Pod 렌탈**
   - RTX 3090 24GB 선택
   - PyTorch 템플릿 사용
   - SSH 접속 확인

3. [ ] **환경 변수 설정**
   - `.env.ec2` 실제 값 입력
   - `.env.runpod` 실제 값 입력
   - Upstash URL 확인

4. [ ] **EC2 배포 테스트**
   ```bash
   # EC2에서 실행
   docker-compose -f docker-compose.production.yml up -d
   ```

5. [ ] **RunPod 배포**
   - SSH 접속
   - 코드 클론
   - Celery Worker 시작

6. [ ] **통합 테스트**
   - EC2 FastAPI → Celery task 호출
   - RunPod Worker → Task 수신
   - 결과 Redis 저장 확인

## 📋 배포 순서 (추천)

### Phase 1: RDS 준비 (20분)
```bash
1. AWS Console → RDS
2. PostgreSQL 15 Free Tier 생성
3. 엔드포인트 복사
4. 보안 그룹 설정 (EC2, RunPod IP 허용)
```

### Phase 2: 환경 변수 설정 (10분)
```bash
1. .env.ec2 파일 작성
   - UPSTASH_REDIS_URL 입력
   - PROD_DATABASE_URL 입력 (RDS)
   - GEMINI_API_KEY 입력

2. .env.runpod 파일 작성
   - .env.ec2와 동일한 내용
   - CUDA_VISIBLE_DEVICES=0 추가
```

### Phase 3: Git Push (5분)
```bash
git add .
git commit -m "feat: add RunPod + Upstash production setup

- Add docker-compose.production.yml for EC2
- Add Dockerfile.runpod for GPU worker
- Add deployment guides and environment templates
- Update config.py for multi-environment support"

git push origin main
```

### Phase 4: EC2 배포 (30분)
```bash
# SSH로 EC2 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 저장소 pull
cd silvertalk
git pull origin main

# .env.ec2 파일 생성 및 설정
nano .env.ec2
# (실제 값 입력)

# Production 모드로 실행
docker-compose -f docker-compose.production.yml up -d

# 로그 확인
docker logs silvertalk-web-prod -f
```

### Phase 5: RunPod 배포 (30분)
```bash
# RunPod Pod 생성 (대시보드)
1. RTX 3090 24GB 선택
2. Deploy

# SSH 접속
ssh root@xyz.proxy.runpod.net -p 12345

# 코드 클론
git clone https://github.com/YOUR_USERNAME/silvertalk.git
cd silvertalk/backend

# 환경 변수 설정
nano .env
# (.env.runpod 내용 복사)

# 의존성 설치
pip install -r requirements.txt

# Worker 시작
screen -S celery
celery -A worker.celery_app worker --loglevel=info --concurrency=2
# Ctrl+A, D로 세션 빠져나오기
```

### Phase 6: 통합 테스트 (15분)
```bash
# Flower 대시보드 확인
http://your-ec2-ip:5555

# API 테스트 (음성 업로드)
curl -X POST http://your-ec2-ip:8000/chat/sessions \
  -F "user_id=test-user" \
  -F "photo_id=test-photo"

# Worker 로그 확인 (RunPod)
screen -r celery
# GPU 사용률 확인
nvidia-smi
```

## 🚨 팀원과 충돌 방지

### Git 브랜치 전략
```bash
# 당신의 작업
git checkout -b feature/runpod-upstash

# 작업 완료 후
git push origin feature/runpod-upstash

# 팀원에게 알림:
"RunPod + Upstash 설정 완료했습니다.
docker-compose.yml은 기존대로 유지되어 로컬 개발에 영향 없습니다.
프로덕션은 docker-compose.production.yml 사용합니다."
```

### 로컬 개발 유지
```bash
# 팀원의 로컬 개발 (변화 없음)
docker-compose up

# 프로덕션 배포 (새로운 방식)
docker-compose -f docker-compose.production.yml up -d
```

## 📊 비용 추정

### 4일 사용 (1월 24일 ~ 1월 27일)

```
RunPod RTX 3090:
- $0.44/hr × 24hr × 4일 = $42.24
- 필요 시 중지: $0.44/hr × 8hr × 4일 = $14.08 (절약형)

RDS Free Tier:
- $0 (첫 12개월 무료)

Upstash Redis Free Tier:
- $0 (10,000 commands/day 무료)

EC2 (기존):
- 팀원이 사용 중

총 비용: $14-42 (RunPod만)
```

## ✅ 최종 확인 사항

### 배포 전
- [ ] Upstash Redis URL 확보
- [ ] RDS 엔드포인트 확보
- [ ] Gemini API Key 확인
- [ ] AWS S3 설정 (팀원 완료 시)
- [ ] RunPod Pod 생성

### 배포 후
- [ ] EC2 FastAPI 정상 실행
- [ ] Flower 대시보드 접속
- [ ] RunPod Worker 연결 확인
- [ ] Task 처리 테스트
- [ ] GPU 사용률 모니터링

## 🎉 성공 기준

1. ✅ EC2에서 API 호출 성공
2. ✅ Celery Task가 Upstash Redis에 저장
3. ✅ RunPod Worker가 Task를 받아서 처리
4. ✅ AI 모델 (Whisper, XTTS) GPU에서 실행
5. ✅ 결과가 RDS PostgreSQL에 저장
6. ✅ Flower에서 Task 모니터링 가능

## 📞 지원

문제 발생 시:
1. `docs/RUNPOD_DEPLOY.md` 문제 해결 섹션 확인
2. Upstash Console에서 Redis 연결 상태 확인
3. RDS 보안 그룹 설정 확인
4. RunPod GPU 사용률 확인 (`nvidia-smi`)

화이팅! 🚀