# SilverTalk API 명세서

> **버전:** 2.0.0
> **최종 수정:** 2026-01-28
> **Base URL:** `http://54.180.28.75:8000`
> **Status 규칙:** 모든 status 값은 **소문자** 사용

---

## 목차
1. [공통 규칙](#공통-규칙)
2. [인증 (Auth)](#1-인증-auth)
3. [사용자 관리 (Users)](#2-사용자-관리-users)
4. [메인 화면 (Home)](#3-메인-화면-home)
5. [갤러리 (Gallery)](#4-갤러리-gallery)
6. [캘린더 (Calendar)](#5-캘린더-calendar)
7. [대화 서비스 (Chat)](#6-대화-서비스-chat)
8. [추억 영상 (Video)](#7-추억-영상-video)
9. [시스템 API](#8-시스템-api)

---

## 공통 규칙

### Status 값 (모두 소문자)

```javascript
// Task 상태
"pending"     // 대기 중
"processing"  // 처리 중
"success"     // 성공
"failure"     // 실패

// 세션 상태
"active"      // 진행 중
"completed"   // 완료
"abandoned"   // 중단됨

// 비디오 상태
"pending"     // 대기 중
"processing"  // 생성 중
"completed"   // 완료
"failed"      // 실패
```

### 인증 헤더

```
Authorization: Bearer {jwt_token}
```

### 에러 응답 형식

```json
{
  "detail": "에러 메시지"
}
```

또는 (유효성 검증 실패 시):

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 1. 인증 (Auth)

### POST `/auth/kakao` - 카카오 로그인/회원가입

**Request Body:**
```json
{
  "kakao_id": "string (required)",
  "nickname": "string (optional)",
  "profile_image": "string (optional)"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "kakao_id": "string",
  "nickname": "string",
  "profile_image": "string",
  "pet_name": "복실이",
  "is_active": true,
  "access_token": "jwt_token"
}
```

### GET `/auth/me` - 현재 사용자 정보

**Headers:** `Authorization: Bearer {token}`

**Response (200 OK):**
```json
{
  "id": "uuid",
  "kakao_id": "string",
  "nickname": "string",
  "pet_name": "복실이"
}
```

---

## 2. 사용자 관리 (Users)

### GET `/users/me` - 사용자 정보 조회

**Query Params:**
- `kakao_id`: string (required)

**Response (200 OK):**
```json
{
  "id": "uuid",
  "kakao_id": "string",
  "nickname": "string",
  "profile_image": "string",
  "pet_name": "복실이",
  "birth_date": "datetime",
  "is_active": true
}
```

### PATCH `/users/me` - 사용자 정보 수정

**Request Body:**
```json
{
  "nickname": "string (optional)",
  "pet_name": "string (optional)",
  "birth_date": "datetime (optional)"
}
```

---

## 3. 메인 화면 (Home)

### GET `/home/greeting` - 복실이 첫 인사

**Query Params:**
- `kakao_id`: string (required)

**Response (200 OK):**
```json
{
  "pet_name": "복실이",
  "message": "할머니, 오셨어요? 심심해요 놀아주세요~",
  "voice_url": "string (optional)"
}
```

---

## 4. 갤러리 (Gallery)

### POST `/photos/sync` - 사진 메타데이터 동기화

**Request Body:**
```json
{
  "kakao_id": "string",
  "photos": [
    {
      "local_id": "string",
      "taken_at": "datetime (optional)",
      "location_name": "string (optional)",
      "latitude": 37.5665,
      "longitude": 126.9780
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "synced_count": 10,
  "photos": [
    {
      "id": "uuid",
      "local_id": "string",
      "upload_url": "https://s3.presigned.url"
    }
  ]
}
```

### GET `/photos/random` - 랜덤 사진 조회

**Query Params:**
- `kakao_id`: string (required)
- `limit`: int (default: 6)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "s3_url": "https://s3.../photo.jpg",
    "taken_at": "2024-01-15T10:30:00",
    "location_name": "제주도 서귀포",
    "view_count": 3
  }
]
```

---

## 5. 캘린더 (Calendar)

### POST `/calendars/sync` - 일정 동기화

**Request Body:**
```json
{
  "kakao_id": "string",
  "events": [
    {
      "title": "병원 진료",
      "start_time": "datetime",
      "end_time": "datetime",
      "location": "서울대병원",
      "is_all_day": false
    }
  ]
}
```

### GET `/calendars/` - 일정 목록 조회

**Query Params:**
- `kakao_id`: string (required)
- `start_date`: datetime (optional)
- `end_date`: datetime (optional)

---

## 6. 대화 서비스 (Chat)

### POST `/chat/sessions` - 대화 세션 시작

사진을 선택하여 새 대화 시작. 첫 인사 메시지 포함.

**Request Body:**
```json
{
  "kakao_id": "string (required)",
  "photo_id": "uuid (optional)"
}
```

**Response (200 OK):**
```json
{
  "session_id": "uuid",
  "ai_reply": "우와, 복실이가 사진을 봤어요! 이 사진에 대해 이야기해주세요!",
  "turn_count": 0,
  "related_photos": [
    {
      "id": "uuid",
      "s3_url": "https://s3.../photo.jpg"
    }
  ]
}
```

**Error (404 Not Found):**
```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

---

### POST `/chat/messages/voice` - 음성 메시지 전송

음성 파일을 업로드하여 AI와 대화. Celery 태스크 ID 반환.

**Request (FormData):**
- `session_id`: string (required)
- `audio_file`: File (.m4a, .wav, .mp3)

**Response (200 OK):**
```json
{
  "task_id": "celery-task-uuid",
  "status": "processing",
  "message": "복실이가 듣고 있어요...",
  "turn_count": 1,
  "can_finish": false
}
```

---

### GET `/api/task/{task_id}` - 태스크 결과 폴링

음성 처리 또는 영상 생성 태스크 결과 조회.

**Response (대기 중):**
```json
{
  "task_id": "uuid",
  "status": "pending",
  "message": "복실이가 준비하고 있어요..."
}
```

**Response (처리 중):**
```json
{
  "task_id": "uuid",
  "status": "processing",
  "message": "복실이가 생각하고 있어요..."
}
```

**Response (성공):**
```json
{
  "task_id": "uuid",
  "status": "success",
  "user_text": "옛날에 바닷가에서 놀았어요",
  "ai_reply": "바닷가요? 정말 좋았겠어요! 멍!",
  "sentiment": "happy",
  "session_id": "uuid"
}
```

**Response (실패):**
```json
{
  "task_id": "uuid",
  "status": "failure",
  "message": "앗, 잠깐 문제가 생겼어요. 다시 말씀해주세요!",
  "error_detail": "..."
}
```

---

### POST `/chat/messages/save-ai-response` - AI 응답 저장

폴링 성공 후 대화 내용을 DB에 저장.

**Request Body:**
```json
{
  "session_id": "uuid (required)",
  "user_text": "string (optional, default: '')",
  "ai_reply": "string (required)"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "대화가 저장되었습니다."
}
```

**Error (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "ai_reply"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### GET `/chat/sessions/{session_id}/turns` - 대화 턴 수 확인

**Response (200 OK):**
```json
{
  "session_id": "uuid",
  "turn_count": 3,
  "can_finish": true
}
```

---

### PATCH `/chat/sessions/{session_id}/finish` - 대화 종료

대화 종료 및 선택적으로 추억 영상 생성 시작.

**Query Params:**
- `create_video`: boolean (default: true)

**Response (200 OK - 영상 생성):**
```json
{
  "success": true,
  "message": "대화가 종료되었습니다. 영상을 만들고 있어요!",
  "session_id": "uuid",
  "video_id": "uuid",
  "video_task_id": "celery-task-uuid"
}
```

**Response (200 OK - 영상 미생성):**
```json
{
  "success": true,
  "message": "대화가 종료되었습니다.",
  "session_id": "uuid"
}
```

---

### GET `/chat/sessions` - 대화 목록 조회

**Query Params:**
- `kakao_id`: string (required)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "main_photo_id": "uuid",
    "turn_count": 5,
    "is_completed": true,
    "status": "completed",
    "created_at": "datetime"
  }
]
```

---

### GET `/chat/sessions/{session_id}` - 대화 상세 조회

**Response (200 OK):**
```json
{
  "session": {
    "id": "uuid",
    "turn_count": 5,
    "status": "completed"
  },
  "logs": [
    {
      "id": 1,
      "role": "assistant",
      "content": "우와, 복실이가 사진을 봤어요!",
      "created_at": "datetime"
    },
    {
      "id": 2,
      "role": "user",
      "content": "옛날에 바닷가에서 놀았어요",
      "created_at": "datetime"
    }
  ]
}
```

---

## 7. 추억 영상 (Video)

### GET `/videos/` - 영상 목록 조회

**Query Params:**
- `kakao_id`: string (required)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "video_url": "https://s3.../video.mp4",
    "thumbnail_url": "https://s3.../thumb.jpg",
    "status": "completed",
    "duration_seconds": 60.5,
    "created_at": "datetime"
  }
]
```

---

### GET `/videos/{video_id}/status` - 영상 상태 조회

**Response (대기 중):**
```json
{
  "video_id": "uuid",
  "status": "pending",
  "video_url": null,
  "thumbnail_url": null,
  "created_at": "datetime"
}
```

**Response (처리 중):**
```json
{
  "video_id": "uuid",
  "status": "processing",
  "video_url": null,
  "thumbnail_url": null,
  "created_at": "datetime"
}
```

**Response (완료):**
```json
{
  "video_id": "uuid",
  "status": "completed",
  "video_url": "https://s3.../video.mp4",
  "thumbnail_url": "https://s3.../thumb.jpg",
  "duration_seconds": 60.5,
  "created_at": "datetime",
  "completed_at": "datetime"
}
```

**Response (실패):**
```json
{
  "video_id": "uuid",
  "status": "failed",
  "video_url": null,
  "error_message": "영상 생성 중 오류가 발생했습니다.",
  "created_at": "datetime"
}
```

---

### DELETE `/videos/{video_id}` - 영상 삭제

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "영상이 삭제되었습니다."
}
```

---

## 8. 시스템 API

### GET `/health` - 헬스체크

**Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

### GET `/api/debug/celery-status` - Celery 상태 확인

**Response (200 OK):**
```json
{
  "celery": "connected",
  "workers": ["worker1@runpod"],
  "queues": ["ai_tasks", "video_tasks"]
}
```

---

## 데이터 흐름 다이어그램

### 음성 대화 흐름

```
┌─────────────┐     POST /chat/sessions     ┌─────────────┐
│   Mobile    │ ───────────────────────────→│   EC2 API   │
│    App      │     {kakao_id, photo_id}    │  (FastAPI)  │
└─────────────┘                              └─────────────┘
      │                                            │
      │         {session_id, ai_reply}             │
      │←───────────────────────────────────────────┘
      │
      │         POST /chat/messages/voice
      │────────────────────────────────────────────→
      │         (FormData: session_id, audio_file)
      │
      │         {task_id, status: "processing"}
      │←────────────────────────────────────────────
      │
      │         GET /api/task/{task_id}  (polling)
      │─────────────────────────────────────────────→ ┌─────────────┐
      │                                               │   RunPod    │
      │         {status: "success", ai_reply, ...}   │  (Celery)   │
      │←──────────────────────────────────────────────└─────────────┘
      │
      │         POST /chat/messages/save-ai-response
      │────────────────────────────────────────────→
      │         {session_id, user_text, ai_reply}
      │
      │         {status: "success"}
      │←────────────────────────────────────────────
```

### 영상 생성 흐름

```
┌─────────────┐  PATCH /sessions/{id}/finish  ┌─────────────┐
│   Mobile    │ ─────────────────────────────→│   EC2 API   │
│    App      │  ?create_video=true           │  (FastAPI)  │
└─────────────┘                                └─────────────┘
      │                                              │
      │    {video_id, video_task_id}                 │
      │←─────────────────────────────────────────────┘
      │                                              │
      │    GET /videos/{video_id}/status             │     ┌─────────────┐
      │────────────────────────────────────────→─────│────→│   RunPod    │
      │    (polling)                                 │     │  (FFmpeg)   │
      │                                              │     └─────────────┘
      │    {status: "completed", video_url}          │
      │←─────────────────────────────────────────────┘
```

---

## Frontend 구현 예시

### 세션 시작 및 첫 인사

```javascript
// ChatScreen.js
const response = await api.post('/chat/sessions', {
  kakao_id: 'test_user',
  photo_id: photoId
});

// 세션 ID 저장
chatSession.setSession(response.session_id);

// 첫 인사 표시
setLocalMessages([{
  role: 'assistant',
  content: response.ai_reply,  // 필수 필드
  timestamp: new Date()
}]);
```

### 폴링 및 응답 처리

```javascript
// useChatSession.js
const result = await pollTaskResult(taskId, { interval: 1500 });

if (result.success) {
  // result.data에서 직접 추출
  const { user_text, ai_reply, sentiment } = result.data;

  // 메시지 추가
  updateLastUserMessage(user_text || '[인식 실패]');
  addMessage('assistant', ai_reply);
  setEmotion(sentiment);
}
```

### 비디오 상태 폴링

```javascript
// ChatScreen.js
const pollForVideo = async (videoId) => {
  const result = await api.get(`/videos/${videoId}/status`);

  if (result.status === 'completed') {
    // 완료 처리
    navigation.navigate('VideoGallery');
  } else if (result.status === 'failed') {
    // 실패 처리
    Alert.alert('오류', result.error_message);
  }

  // 계속 폴링...
};
```
