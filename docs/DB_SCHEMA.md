# SilverTalk 데이터베이스 스키마

> **버전:** 2.1.0
> **최종 수정:** 2026-01-28
> **Status 규칙:** 모든 status 값은 **소문자** 사용

---

## ERD 개요

```
users (사용자)
  │
  ├─── 1:N ──→ user_photos (사진)
  │              └─── N:M ──→ session_photos (세션-사진 연결)
  │
  ├─── 1:N ──→ user_calendars (캘린더)
  │
  ├─── 1:N ──→ chat_sessions (대화 세션)
  │              │
  │              ├─── 1:N ──→ chat_logs (대화 로그)
  │              └─── 1:N ──→ session_photos
  │
  ├─── 1:N ──→ generated_videos (생성된 영상)
  │
  └─── 1:N ──→ memory_insights (기억 인사이트)
```

---

## 테이블 상세

### 1. `users` - 사용자 테이블

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 사용자 ID | PK |
| kakao_id | String | 카카오 ID | UNIQUE, NOT NULL, INDEX |
| nickname | String | 닉네임 | NULL |
| profile_image | Text | 프로필 이미지 URL | NULL |
| pet_name | String | 반려견 이름 | NULL |
| birth_date | DateTime | 생년월일 | NULL |
| is_active | Boolean | 활성 상태 | DEFAULT true |
| created_at | DateTime | 가입일 | DEFAULT NOW() |

**관계:**
- `user_photos`: 1:N (user_id)
- `user_calendars`: 1:N (user_id)
- `chat_sessions`: 1:N (user_id)
- `generated_videos`: 1:N (user_id)
- `memory_insights`: 1:N (user_id)

---

### 2. `user_photos` - 사진 메타데이터

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 사진 ID | PK |
| user_id | UUID | 사용자 ID | FK → users.id, NOT NULL |
| local_uri | Text | 로컬 파일 경로 | NULL |
| s3_url | Text | S3 URL (업로드 시) | NULL |
| taken_at | DateTime | 촬영 날짜 | NULL |
| location_name | Text | 장소명 | NULL |
| latitude | Float | 위도 | NULL |
| longitude | Float | 경도 | NULL |
| ai_analysis | Text | Vision AI 분석 결과 (JSON) | NULL |
| view_count | Integer | 대화 사용 횟수 | DEFAULT 0 |
| last_chat_session_id | UUID | 마지막 대화 세션 ID | FK → chat_sessions.id, NULL |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**인덱스:**
- `idx_user_photos_user_id` (user_id)
- `idx_user_photos_taken_at` (taken_at)
- `idx_user_photos_view_count` (view_count)

---

### 3. `user_calendars` - 캘린더 일정

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 일정 ID | PK |
| user_id | UUID | 사용자 ID | FK → users.id, NOT NULL |
| title | Text | 일정 제목 | NULL |
| start_time | DateTime | 시작 시간 | NULL |
| end_time | DateTime | 종료 시간 | NULL |
| location | Text | 장소 | NULL |
| is_all_day | Boolean | 종일 여부 | DEFAULT false |

**인덱스:**
- `idx_user_calendars_user_id` (user_id)
- `idx_user_calendars_start_time` (start_time)

---

### 4. `chat_sessions` - 대화 세션

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 세션 ID | PK |
| user_id | UUID | 사용자 ID | FK → users.id, NOT NULL |
| main_photo_id | UUID | 메인 사진 ID | FK → user_photos.id, NULL |
| summary | Text | 대화 요약 | NULL |
| turn_count | Integer | 대화 턴 수 | DEFAULT 0 |
| is_completed | Boolean | 완료 여부 | DEFAULT false |
| status | Enum(SessionStatus) | 세션 상태 | DEFAULT 'active' |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**Enum: SessionStatus (소문자)**
```python
class SessionStatus(str, Enum):
    ACTIVE = "active"        # 진행 중
    COMPLETED = "completed"  # 완료
    ABANDONED = "abandoned"  # 중단됨
```

**인덱스:**
- `idx_chat_sessions_user_id` (user_id)
- `idx_chat_sessions_status` (status)
- `idx_chat_sessions_created_at` (created_at)

---

### 5. `session_photos` - 세션-사진 연결 테이블

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | Integer | ID | PK, AUTO_INCREMENT |
| session_id | UUID | 세션 ID | FK → chat_sessions.id, NOT NULL |
| photo_id | UUID | 사진 ID | FK → user_photos.id, NULL |
| s3_url | Text | 사진 S3 URL (스냅샷) | NULL |
| display_order | Integer | 표시 순서 (1=메인) | DEFAULT 1, NOT NULL |
| added_at | DateTime | 추가된 시간 | DEFAULT NOW() |

**제약조건:**
- `uq_session_photo`: UNIQUE(session_id, photo_id)

**인덱스:**
- `idx_session_photos_session_id` (session_id)
- `idx_session_photos_photo_id` (photo_id)

---

### 6. `chat_logs` - 대화 로그

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | Integer | 로그 ID | PK, AUTO_INCREMENT |
| session_id | UUID | 세션 ID | FK → chat_sessions.id, NOT NULL |
| role | String(20) | 역할 | 'user' or 'assistant' |
| content | Text | 메시지 내용 | NOT NULL |
| voice_url | Text | TTS 음성 URL | NULL |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**인덱스:**
- `idx_chat_logs_session_id` (session_id)
- `idx_chat_logs_created_at` (created_at)

---

### 7. `generated_videos` - 생성된 영상

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 영상 ID | PK |
| user_id | UUID | 사용자 ID | FK → users.id, NOT NULL |
| session_id | UUID | 세션 ID | FK → chat_sessions.id, NOT NULL |
| video_url | Text | 영상 S3 URL | NULL |
| thumbnail_url | Text | 썸네일 URL | NULL |
| video_type | Enum(VideoType) | 영상 타입 | DEFAULT 'slideshow' |
| duration_seconds | Float | 영상 길이 (초) | NULL |
| status | Enum(VideoStatus) | 생성 상태 | DEFAULT 'pending' |
| created_at | DateTime | 생성일 | DEFAULT NOW() |

**Enum: VideoStatus (소문자)**
```python
class VideoStatus(str, Enum):
    PENDING = "pending"        # 대기 중
    PROCESSING = "processing"  # 생성 중
    COMPLETED = "completed"    # 완료
    FAILED = "failed"          # 실패
```

**Enum: VideoType (소문자)**
```python
class VideoType(str, Enum):
    SLIDESHOW = "slideshow"      # FFmpeg Ken Burns 슬라이드쇼
    AI_ANIMATED = "ai_animated"  # Replicate SVD AI 애니메이션
```

**인덱스:**
- `idx_generated_videos_user_id` (user_id)
- `idx_generated_videos_session_id` (session_id)
- `idx_generated_videos_status` (status)
- `idx_generated_videos_created_at` (created_at)

---

### 8. `memory_insights` - 기억 인사이트

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | Integer | 인사이트 ID | PK, AUTO_INCREMENT |
| user_id | UUID | 사용자 ID | FK → users.id, NOT NULL |
| category | String(50) | 카테고리 | family/travel/food/hobby 등 |
| fact | Text | 추출된 사실 | NULL |
| source_log_id | Integer | 출처 로그 ID | FK → chat_logs.id, NULL |
| importance | Integer | 중요도 (1-5) | DEFAULT 1 |
| updated_at | DateTime | 수정일 | DEFAULT NOW() |

**인덱스:**
- `idx_memory_insights_user_id` (user_id)
- `idx_memory_insights_category` (category)
- `idx_memory_insights_importance` (importance)

---

## Enum 정의 (공통)

### TaskStatus - Celery 태스크 상태 (소문자)

```python
class TaskStatus(str, Enum):
    pending = "pending"        # 대기 중
    processing = "processing"  # 처리 중
    success = "success"        # 성공
    failure = "failure"        # 실패
    error = "error"            # 에러
```

### Sentiment - AI 감정 표현 (소문자)

```python
class Sentiment(str, Enum):
    happy = "happy"            # 행복
    sad = "sad"                # 슬픔
    curious = "curious"        # 궁금함
    excited = "excited"        # 신남
    nostalgic = "nostalgic"    # 향수
    comforting = "comforting"  # 위로
    neutral = "neutral"        # 중립
    thinking = "thinking"      # 생각 중
```

---

## 관계도 (SQL)

```sql
-- 사용자 → 사진
users.id ← user_photos.user_id (1:N)

-- 사용자 → 캘린더
users.id ← user_calendars.user_id (1:N)

-- 사용자 → 대화 세션
users.id ← chat_sessions.user_id (1:N)

-- 사진 → 대화 세션 (메인 사진)
user_photos.id ← chat_sessions.main_photo_id (1:N)

-- 대화 세션 ↔ 사진 (다대다, session_photos로 연결)
chat_sessions.id ← session_photos.session_id
user_photos.id ← session_photos.photo_id

-- 대화 세션 → 대화 로그
chat_sessions.id ← chat_logs.session_id (1:N)

-- 대화 세션 → 생성 영상
chat_sessions.id ← generated_videos.session_id (1:N)

-- 사용자 → 생성 영상
users.id ← generated_videos.user_id (1:N)

-- 사용자 → 기억 인사이트
users.id ← memory_insights.user_id (1:N)

-- 대화 로그 → 기억 인사이트
chat_logs.id ← memory_insights.source_log_id (N:1)
```

---

## 초기 데이터베이스 설정

### 1. PostgreSQL 컨테이너 실행

```bash
docker-compose up -d postgres
```

### 2. 테이블 자동 생성

FastAPI 앱 실행 시 자동으로 테이블 생성:

```python
# backend/common/database.py
from common.database import init_db

init_db()  # CREATE TABLE IF NOT EXISTS
```

### 3. 환경변수

```bash
# .env
DATABASE_URL=postgresql://silvertalk:password@localhost:5432/silvertalk
```

---

## 쿼리 예제

### 사용자의 모든 대화 세션 조회

```python
from common.models import SessionStatus

sessions = (
    db.query(ChatSession)
    .filter(ChatSession.user_id == user.id)
    .filter(ChatSession.status == SessionStatus.COMPLETED)
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

### 완료된 영상 목록 조회

```python
from common.models import VideoStatus

videos = (
    db.query(GeneratedVideo)
    .filter(GeneratedVideo.user_id == user.id)
    .filter(GeneratedVideo.status == VideoStatus.COMPLETED)
    .order_by(GeneratedVideo.created_at.desc())
    .all()
)
```
