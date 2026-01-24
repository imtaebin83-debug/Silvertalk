# 🌐 SilverTalk API 명세서

## 📋 목차
1. [인증 (Auth)](#1-인증-auth)
2. [사용자 관리 (Users)](#2-사용자-관리-users)
3. [메인 화면 (Home)](#3-메인-화면-home)
4. [갤러리 (Gallery)](#4-갤러리-gallery)
5. [캘린더 (Calendar)](#5-캘린더-calendar)
6. [대화 서비스 (Chat)](#6-대화-서비스-chat)
7. [추억 영상 (Video)](#7-추억-영상-video)
8. [기억 인사이트 (Memory)](#8-기억-인사이트-memory)

---

## 1. 인증 (Auth)

### POST `/auth/kakao` - 카카오 회원가입

**Request Body:**
```json
{
  "kakao_id": "string",
  "nickname": "string (optional)",
  "profile_image": "string (optional)"
}
```

**Response:**
```json
{
  "id": "uuid",
  "kakao_id": "string",
  "nickname": "string",
  "profile_image": "string",
  "pet_name": "string",
  "is_active": true
}
```

### POST `/auth/logout` - 로그아웃

### GET `/auth/me` - 사용자 정보 조회

---

## 2. 사용자 관리 (Users)

### GET `/users/me` - 어르신 정보

**Query Params:**
- `kakao_id`: string (required)

### PATCH `/users/me` - 어르신 정보 수정

**Request Body:**
```json
{
  "nickname": "string (optional)",
  "pet_name": "string (optional)",
  "birth_date": "datetime (optional)"
}
```

### DELETE `/users/me` - 회원 탈퇴

---

## 3. 메인 화면 (Home)

### GET `/home/greeting` - 강아지 첫 인사 조회

**Query Params:**
- `kakao_id`: string

**Response:**
```json
{
  "pet_name": "복실이",
  "message": "할머니, 오셨어요? 심심해요 놀아주세요~",
  "voice_url": "string (optional)"
}
```

### POST `/home/notification/push` - 강아지 알림

---

## 4. 갤러리 (Gallery)

### POST `/photos/sync` - 사진 메타데이터 동기화

**Request Body:**
```json
{
  "photos": [
    {
      "taken_at": "datetime (optional)",
      "location_name": "string (optional)",
      "latitude": "float (optional)",
      "longitude": "float (optional)"
    }
  ]
}
```

### POST `/photos/presign` - 사진 업로드 URL 발급

**Response:**
```json
{
  "presign_url": "https://s3.amazonaws.com/...",
  "expires_in": 3600
}
```

### GET `/photos/random` - 초기 랜덤 사진 조회

**Query Params:**
- `kakao_id`: string
- `limit`: int (default: 6)

**Response:**
```json
[
  {
    "id": "uuid",
    "s3_url": "string",
    "taken_at": "datetime",
    "location_name": "string",
    "ai_analysis": "string",
    "view_count": 0
  }
]
```

### GET `/photos/refresh` - 사진 리스트 갱신

---

## 5. 캘린더 (Calendar)

### POST `/calendars/sync` - 캘린더 일정 동기화

**Request Body:**
```json
{
  "events": [
    {
      "title": "string",
      "start_time": "datetime",
      "end_time": "datetime",
      "location": "string",
      "is_all_day": false
    }
  ]
}
```

### GET `/calendars/` - 일정 목록 조회

---

## 6. 대화 서비스 (Chat)

### POST `/chat/sessions` - 대화 세션 시작

**Request Body:**
```json
{
  "kakao_id": "string",
  "photo_id": "uuid"
}
```

**Response:**
```json
{
  "id": "uuid",
  "main_photo_id": "uuid",
  "turn_count": 0,
  "is_completed": false,
  "status": "active",
  "created_at": "datetime"
}
```

### GET `/chat/sessions/next-photos` - 유사 사진 추천

### POST `/chat/messages/voice` - 음성 메시지 처리

**Form Data:**
- `session_id`: uuid
- `audio_file`: file (mp3, wav)

**Response:**
```json
{
  "task_id": "uuid",
  "status": "processing",
  "message": "AI가 듣고 있어요...",
  "turn_count": 1
}
```

### GET `/chat/animations` - 대기 애니메이션 조회

**Response:**
```json
{
  "type": "tail_wag",
  "message": "꼬리 흔들흔들~"
}
```

### GET `/chat/sessions/{session_id}/turns` - 대화 턴 수 확인

**Response:**
```json
{
  "session_id": "uuid",
  "turn_count": 3,
  "can_finish": true
}
```

### PATCH `/chat/sessions/{session_id}/finish` - 대화 종료 및 요약

**Query Params:**
- `create_video`: bool (default: true)

**Response:**
```json
{
  "message": "대화가 종료되었습니다. 영상을 만들고 있어요!",
  "session_id": "uuid",
  "video_task_id": "uuid"
}
```

### GET `/chat/sessions` - 전체 대화 목록 조회

### GET `/chat/sessions/{session_id}` - 대화 상세 기록 조회

### DELETE `/chat/sessions/{session_id}` - 대화 기록 삭제

---

## 7. 추억 영상 (Video)

### POST `/videos/generate` - 애니메이션 제작 요청

**Request Body:**
```json
{
  "session_id": "uuid",
  "voice_id": "string (optional)"
}
```

**Response:**
```json
{
  "message": "영상 생성이 시작되었습니다.",
  "video_id": "uuid",
  "task_id": "uuid",
  "status": "pending"
}
```

### GET `/videos/{video_id}/status` - 제작 상태 조회

**Response:**
```json
{
  "video_id": "uuid",
  "status": "completed",
  "video_url": "https://s3.amazonaws.com/...",
  "thumbnail_url": "https://s3.amazonaws.com/...",
  "created_at": "datetime"
}
```

### GET `/videos/voices` - 나레이션 보이스 목록

### POST `/videos/{video_id}/share` - 카카오톡 공유 데이터

**Response:**
```json
{
  "title": "할머니의 추억",
  "description": "소중한 추억을 영상으로 만들었어요",
  "thumbnail_url": "string",
  "video_url": "string",
  "share_url": "https://silvertalk.app/videos/{video_id}"
}
```

### GET `/videos/` - 추억 영상 목록 조회

### DELETE `/videos/{video_id}` - 영상 삭제

---

## 8. 기억 인사이트 (Memory)

### GET `/memories/` - 핵심 기억 목록 조회

**Query Params:**
- `kakao_id`: string
- `category`: string (optional)

**Response:**
```json
[
  {
    "id": 1,
    "category": "family",
    "fact": "손주 이름: 민수",
    "importance": 5,
    "updated_at": "datetime"
  }
]
```

### GET `/memories/{category}` - 카테고리별 기억 조회

### GET `/memories/photos/{photo_id}/analysis` - 사진별 누적 분석 조회

---

## 🔧 공통 API

### GET `/api/task/{task_id}` - Celery 태스크 결과 조회

**Response:**
```json
{
  "task_id": "uuid",
  "status": "success",
  "result": {
    "user_text": "인식된 텍스트",
    "ai_reply": "AI 답변",
    "audio_url": "/app/data/reply.wav"
  }
}
```

### GET `/health` - 헬스체크

### GET `/api/debug/celery-status` - Celery Worker 상태 확인
