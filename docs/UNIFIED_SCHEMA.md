# SilverTalk 통합 스키마 명세서 (Data Contract)

> **버전:** 2.0.0
> **최종 수정:** 2026-01-28
> **Status 규칙:** 모든 status 값은 **소문자** 사용

---

## 목차
1. [Status 값 정의 (소문자)](#1-status-값-정의-소문자)
2. [Pydantic 스키마 정의](#2-pydantic-스키마-정의)
3. [API 요청/응답 매핑](#3-api-요청응답-매핑)
4. [Celery Task 반환값](#4-celery-task-반환값)
5. [Frontend 구현 체크리스트](#5-frontend-구현-체크리스트)

---

## 1. Status 값 정의 (소문자)

### 1.1 TaskStatus - Celery 태스크 상태

```python
# backend/common/enums.py

class TaskStatus(str, Enum):
    pending = "pending"        # 대기 중
    processing = "processing"  # 처리 중
    success = "success"        # 성공
    failure = "failure"        # 실패
    error = "error"            # 에러
```

**사용처:**
- `GET /api/task/{task_id}` 응답의 `status` 필드
- Celery task 반환값의 `status` 필드

---

### 1.2 SessionStatus - 대화 세션 상태

```python
class SessionStatus(str, Enum):
    active = "active"          # 진행 중
    completed = "completed"    # 완료
    abandoned = "abandoned"    # 중단됨
```

**사용처:**
- `chat_sessions` 테이블의 `status` 컬럼
- 세션 조회 API 응답

---

### 1.3 VideoStatus - 영상 상태

```python
class VideoStatus(str, Enum):
    PENDING = "pending"        # 대기 중
    PROCESSING = "processing"  # 생성 중
    COMPLETED = "completed"    # 완료
    FAILED = "failed"          # 실패
```

**사용처:**
- `generated_videos` 테이블의 `status` 컬럼
- `GET /videos/{video_id}/status` 응답

---

### 1.4 VideoType - 영상 타입

```python
class VideoType(str, Enum):
    SLIDESHOW = "slideshow"      # FFmpeg Ken Burns 슬라이드쇼
    AI_ANIMATED = "ai_animated"  # Replicate SVD AI 애니메이션
```

**사용처:**
- `generated_videos` 테이블의 `video_type` 컬럼

---

### 1.5 Sentiment - AI 감정 표현

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

**사용처:**
- Celery task 반환값의 `sentiment` 필드
- 폴링 API 응답의 `sentiment` 필드

---

## 2. Pydantic 스키마 정의

### 2.1 채팅 세션 스키마

```python
# backend/app/schemas/chat.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ============================================================
# 세션 생성
# ============================================================

class CreateSessionRequest(BaseModel):
    """POST /chat/sessions 요청"""
    kakao_id: str = Field(..., description="카카오 사용자 ID (필수)")
    photo_id: Optional[str] = Field(None, description="UserPhoto UUID")


class CreateSessionResponse(BaseModel):
    """POST /chat/sessions 응답"""
    session_id: str
    ai_reply: str              # 필수 - 첫 인사 메시지
    turn_count: int = 0
    related_photos: List[dict] = []


# ============================================================
# 음성 메시지
# ============================================================

class VoiceMessageResponse(BaseModel):
    """POST /chat/messages/voice 응답"""
    task_id: str
    status: str = "processing"  # 소문자
    message: str
    turn_count: int
    can_finish: bool = False


# ============================================================
# Task 폴링
# ============================================================

class TaskPendingResponse(BaseModel):
    """GET /api/task/{task_id} - 대기 중"""
    task_id: str
    status: str = "pending"     # 소문자
    message: str


class TaskProcessingResponse(BaseModel):
    """GET /api/task/{task_id} - 처리 중"""
    task_id: str
    status: str = "processing"  # 소문자
    message: str


class TaskSuccessResponse(BaseModel):
    """GET /api/task/{task_id} - 성공"""
    task_id: str
    status: str = "success"     # 소문자
    user_text: str
    ai_reply: str
    sentiment: str
    session_id: Optional[str] = None


class TaskFailureResponse(BaseModel):
    """GET /api/task/{task_id} - 실패"""
    task_id: str
    status: str = "failure"     # 소문자
    message: str
    error_detail: Optional[str] = None


# ============================================================
# AI 응답 저장
# ============================================================

class SaveAIResponseRequest(BaseModel):
    """POST /chat/messages/save-ai-response 요청"""
    session_id: str
    user_text: Optional[str] = ""  # 빈 문자열 허용
    ai_reply: str                  # 필수


class SaveAIResponseResponse(BaseModel):
    """POST /chat/messages/save-ai-response 응답"""
    status: str = "success"        # 소문자
    message: str = "대화가 저장되었습니다."


# ============================================================
# 세션 종료
# ============================================================

class FinishSessionResponse(BaseModel):
    """PATCH /chat/sessions/{session_id}/finish 응답"""
    success: bool = True
    message: str
    session_id: str
    video_id: Optional[str] = None
    video_task_id: Optional[str] = None
```

### 2.2 비디오 스키마

```python
# backend/app/schemas/video.py

class VideoStatusResponse(BaseModel):
    """GET /videos/{video_id}/status 응답"""
    video_id: str
    status: str                    # pending, processing, completed, failed
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
```

---

## 3. API 요청/응답 매핑

### 3.1 세션 생성

```
Frontend                      Backend
─────────────────────────────────────────────
Request:
{
  "kakao_id": "test_user",
  "photo_id": "uuid"          // optional
}

                              ↓

Response:
{
  "session_id": "uuid",
  "ai_reply": "첫 인사...",   // 필수!
  "turn_count": 0,
  "related_photos": []
}
```

### 3.2 Task 폴링 (핵심)

```
Frontend                      Backend (main.py)
─────────────────────────────────────────────

GET /api/task/{task_id}

                              ↓

# 대기 중
{
  "task_id": "...",
  "status": "pending",        // ← 소문자!
  "message": "복실이가 준비..."
}

# 처리 중
{
  "task_id": "...",
  "status": "processing",     // ← 소문자!
  "message": "복실이가 생각..."
}

# 성공
{
  "task_id": "...",
  "status": "success",        // ← 소문자!
  "user_text": "...",
  "ai_reply": "...",
  "sentiment": "happy",
  "session_id": "..."
}

# 실패
{
  "task_id": "...",
  "status": "failure",        // ← 소문자!
  "message": "앗, 문제가...",
  "error_detail": "..."
}
```

### 3.3 비디오 상태

```
Frontend                      Backend
─────────────────────────────────────────────

GET /videos/{video_id}/status

                              ↓

# 대기 중
{
  "video_id": "...",
  "status": "pending",        // ← 소문자!
  ...
}

# 완료
{
  "video_id": "...",
  "status": "completed",      // ← 소문자!
  "video_url": "https://...",
  ...
}

# 실패
{
  "video_id": "...",
  "status": "failed",         // ← 소문자!
  "error_message": "...",
  ...
}
```

---

## 4. Celery Task 반환값

### 4.1 process_audio_and_reply

```python
# worker/tasks.py

# 성공 시 반환값
{
    "status": "success",      # 소문자!
    "user_text": "사용자 음성 텍스트",
    "ai_reply": "AI 응답 텍스트",
    "sentiment": "happy",     # 소문자!
    "session_id": "uuid"
}

# 실패 시 반환값
{
    "status": "error",        # 소문자!
    "message": "에러 메시지"
}
```

### 4.2 generate_memory_video

```python
# worker/tasks.py

# 성공 시 반환값
{
    "status": "success",      # 소문자!
    "video_url": "https://s3.../video.mp4",
    "thumbnail_url": "https://s3.../thumb.jpg",
    "duration_seconds": 60.5
}

# 실패 시 반환값
    "status": "error",        # 소문자!
    "message": "에러 메시지"
}
```

### 4.3 generate_greeting (신규)

```python
# worker/tasks.py

# 성공 시 반환값
{
    "status": "success",      # 소문자!
    "ai_greeting": "우와! 정말 멋진 바다 사진이네요! 언제 다녀오셨어요?",
    "analysis": "A photo of a beautiful beach with blue sky...",
    "session_id": "uuid-string"
}

# 실패 시 반환값
{
    "status": "failure",
    "message": "이미지를 분석할 수 없습니다.",
    "session_id": "uuid-string"
}
```

---

## 5. Frontend 구현 체크리스트

### 5.1 폴링 상태 체크 (config.js)

```javascript
// ✅ 소문자로 비교
if (result.status === 'success') {
    return { success: true, data: result };
}

if (result.status === 'failure') {
    return { success: false, error: result.error || result.message };
}
```

### 5.2 데이터 추출 (useChatSession.js)

```javascript
// pollTaskResult가 { success: true, data: result }를 반환
const result = await pollTaskResult(taskId, options);

if (result.success) {
    // result.data에서 직접 추출
    const user_text = result.data?.user_text || '';
    const ai_reply = result.data?.ai_reply || '';
    const sentiment = result.data?.sentiment || 'neutral';

    // ai_reply 검증
    if (!ai_reply) {
        throw new Error('AI 응답이 비어있습니다.');
    }

    // 메시지 추가
    updateLastUserMessage(user_text || '[인식 실패]');
    addMessage('assistant', ai_reply);
    setEmotion(sentiment);
}
```

### 5.3 비디오 폴링 (ChatScreen.js)

```javascript
const pollForVideo = async (videoId) => {
    const result = await api.get(`/videos/${videoId}/status`);

    // ✅ 소문자로 비교
    if (result.status === 'completed') {
        // 완료 처리
    }

    if (result.status === 'failed') {
        // 실패 처리
    }
};
```

### 5.4 세션 시작 (ChatScreen.js)

```javascript
const response = await api.post('/chat/sessions', {
    kakao_id: 'test_user',
    photo_id: photoId
});

// 새 세션 ID 설정
if (response.session_id) {
    chatSession.setSession(response.session_id);
}

// ai_reply 검증 후 표시
const aiReply = response.ai_reply;
if (!aiReply) {
    throw new Error('서버 응답에 ai_reply가 없습니다.');
}

setLocalMessages([{
    role: 'assistant',
    content: aiReply,
    timestamp: new Date()
}]);
```

---

## 6. 변경 체크리스트

### Backend (EC2) 수정 필요

- [ ] `main.py`: 폴링 응답 `status`를 **소문자**로 반환
  ```python
  # 변경 전
  if task.state == "SUCCESS":
      return { "status": "success", ... }  # ✅ 이미 소문자

  # 확인 필요: Celery task.state 비교는 대문자로
  if task.state == "PENDING":  # Celery는 대문자
      return { "status": "pending", ... }  # 응답은 소문자로
  ```

- [x] `chat.py`: `SaveAIResponseRequest.user_text`를 `Optional[str] = ""`로 수정

### Frontend (Mobile) 수정 완료

- [x] `config.js`: 폴링 상태 소문자 체크
- [x] `useChatSession.js`: 디버깅 로그 및 검증 추가
- [x] `ChatScreen.js`: 세션 ID 설정 및 ai_reply 검증

### Worker (RunPod)

- [x] `tasks.py`: 반환값 `status`는 이미 소문자 (`"success"`, `"error"`)

---

## 7. 담당자별 체크리스트

### 본인 (Celery/RunPod)

- [x] `tasks.py` 반환값 소문자 확인
- [ ] 비디오 생성 task 반환값 확인

### 팀원 (EC2/FastAPI)

- [ ] `main.py` 폴링 API 소문자 응답 확인
- [ ] `video.py` 상태 조회 API 소문자 응답 확인
- [ ] Pydantic 스키마 업데이트
