# 🗄️ SilverTalk 데이터베이스 스키마

## ERD 개요

```
users (사용자)
  ↓ 1:N
user_photos (사진)
  ↓ 1:N
user_calendars (캘린더)
  ↓
chat_sessions (대화 세션)
  ↓ 1:N
chat_logs (대화 로그)
  ↓
generated_videos (생성된 영상)
  ↓
memory_insights (기억 인사이트)
```

---

## 📋 테이블 상세

### 1. `users` - 사용자 테이블

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 사용자 ID | PK |
| kakao_id | String | 카카오 ID | UNIQUE, NOT NULL |
| nickname | String | 닉네임 | NULL |
| profile_image | Text | 프로필 이미지 URL | NULL |
| is_active | Boolean | 활성 상태 | DEFAULT TRUE |
| created_at | DateTime | 가입일 | DEFAULT NOW() |
| pet_name | String | 반려견 이름 | NULL |
| birth_date | DateTime | 생년월일 | NULL |

**관계:**
- `user_photos`: 1:N
- `user_calendars`: 1:N
- `chat_sessions`: 1:N
- `generated_videos`: 1:N
- `memory_insights`: 1:N

---

### 2. `user_photos` - 사진 메타데이터

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 사진 ID | PK |
| user_id | UUID | 사용자 ID | FK (users.id) |
| s3_url | Text | S3 URL | NULL |
| taken_at | DateTime | 촬영 날짜 | NULL |
| location_name | Text | 장소명 | NULL |
| latitude | Float | 위도 | NULL |
| longitude | Float | 경도 | NULL |
| ai_analysis | Text | Vision AI 분석 결과 (JSON) | NULL |
| last_chat_session_id | UUID | 마지막 대화 세션 ID | FK (chat_sessions.id) |
| created_at | DateTime | 생성일 | DEFAULT NOW() |
| view_count | Integer | 대화 사용 횟수 | DEFAULT 0 |

**인덱스:**
- `user_id`
- `taken_at`
- `view_count`

---

### 3. `user_calendars` - 캘린더 일정

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 일정 ID | PK |
| user_id | UUID | 사용자 ID | FK (users.id) |
| title | Text | 일정 제목 | NULL |
| start_time | DateTime | 시작 시간 | NULL |
| end_time | DateTime | 종료 시간 | NULL |
| location | Text | 장소 | NULL |
| is_all_day | Boolean | 종일 여부 | DEFAULT FALSE |

**인덱스:**
- `user_id`
- `start_time`

---

### 4. `chat_sessions` - 대화 세션

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 세션 ID | PK |
| user_id | UUID | 사용자 ID | FK (users.id) |
| main_photo_id | UUID | 메인 사진 ID | FK (user_photos.id) |
| summary | Text | 대화 요약 | NULL |
| is_completed | Boolean | 완료 여부 | DEFAULT FALSE |
| status | Enum | 세션 상태 | active/completed/abandoned |
| created_at | DateTime | 생성일 | DEFAULT NOW() |
| turn_count | Integer | 대화 턴 수 | DEFAULT 0 |

**Enum: SessionStatus**
- `active`: 진행 중
- `completed`: 완료
- `abandoned`: 중단됨

**인덱스:**
- `user_id`
- `created_at`
- `status`

---

### 5. `chat_logs` - 대화 로그

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | Serial | 로그 ID | PK |
| session_id | UUID | 세션 ID | FK (chat_sessions.id) |
| role | String | 역할 | user/assistant |
| content | Text | 메시지 내용 | NOT NULL |
| voice_url | Text | TTS 음성 URL | NULL |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**인덱스:**
- `session_id`
- `created_at`

---

### 6. `generated_videos` - 생성된 영상

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 영상 ID | PK |
| user_id | UUID | 사용자 ID | FK (users.id) |
| session_id | UUID | 세션 ID | FK (chat_sessions.id) |
| video_url | Text | 영상 S3 URL | NULL |
| thumbnail_url | Text | 썸네일 URL | NULL |
| status | Enum | 생성 상태 | pending/processing/completed/failed |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**Enum: VideoStatus**
- `pending`: 대기 중
- `processing`: 생성 중
- `completed`: 완료
- `failed`: 실패

**인덱스:**
- `user_id`
- `status`
- `created_at`

---

### 7. `memory_insights` - 기억 인사이트

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | Serial | 인사이트 ID | PK |
| user_id | UUID | 사용자 ID | FK (users.id) |
| category | String | 카테고리 | family/travel/food/hobby 등 |
| fact | Text | 추출된 사실 | NULL |
| source_log_id | Integer | 출처 로그 ID | FK (chat_logs.id) |
| importance | Integer | 중요도 (1-5) | DEFAULT 1 |
| updated_at | DateTime | 수정일 | DEFAULT NOW() |

**인덱스:**
- `user_id`
- `category`
- `importance`

---

## 🔗 관계도

```sql
-- 사용자 → 사진
users.id ← user_photos.user_id (1:N)

-- 사용자 → 캘린더
users.id ← user_calendars.user_id (1:N)

-- 사용자 → 대화 세션
users.id ← chat_sessions.user_id (1:N)

-- 사진 → 대화 세션
user_photos.id ← chat_sessions.main_photo_id (1:1)

-- 대화 세션 → 대화 로그
chat_sessions.id ← chat_logs.session_id (1:N)

-- 대화 세션 → 생성 영상
chat_sessions.id ← generated_videos.session_id (1:N)

-- 사용자 → 기억 인사이트
users.id ← memory_insights.user_id (1:N)

-- 대화 로그 → 기억 인사이트
chat_logs.id ← memory_insights.source_log_id (N:1)
```

---

## 🚀 초기 데이터베이스 설정

### 1. PostgreSQL 컨테이너 실행 (Docker Compose)

```bash
docker-compose up -d postgres
```

### 2. 테이블 자동 생성

FastAPI 앱 실행 시 자동으로 테이블이 생성됩니다:

```python
# backend/common/database.py
from common.database import init_db

init_db()  # CREATE TABLE IF NOT EXISTS
```

### 3. 수동 테이블 생성 (필요 시)

```bash
docker exec -it silvertalk-postgres psql -U silvertalk -d silvertalk

# SQL 실행
CREATE TABLE users (...);
CREATE TABLE user_photos (...);
# ...
```

---

## 📝 마이그레이션 (Alembic)

향후 스키마 변경 시 Alembic을 사용합니다:

```bash
# 초기 마이그레이션 생성
cd backend
alembic init alembic

# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Initial tables"

# 마이그레이션 적용
alembic upgrade head
```

---

## 🔍 쿼리 예제

### 사용자의 모든 대화 세션 조회

```python
sessions = (
    db.query(ChatSession)
    .filter(ChatSession.user_id == user.id)
    .order_by(ChatSession.created_at.desc())
    .all()
)
```

### 오래되고 덜 본 사진 우선 조회

```python
photos = (
    db.query(UserPhoto)
    .filter(UserPhoto.user_id == user.id)
    .order_by(
        UserPhoto.view_count.asc(),
        func.random()
    )
    .limit(6)
    .all()
)
```

### 특정 세션의 대화 로그 조회

```python
logs = (
    db.query(ChatLog)
    .filter(ChatLog.session_id == session_id)
    .order_by(ChatLog.created_at.asc())
    .all()
)
```
