# 📋 SilverTalk Chat Session 구현 계획서

> **작성일**: 2026-01-27  
> **버전**: v1.0  
> **상태**: 설계 완료, 승인 대기

---

## 📑 목차

1. [프로젝트 현황 분석](#1-프로젝트-현황-분석)
2. [아키텍처 플로우차트](#2-아키텍처-플로우차트)
3. [백엔드 태스크](#3-백엔드-태스크)
4. [프론트엔드 태스크](#4-프론트엔드-태스크)
5. [누락 사항 및 개선 제안](#5-누락-사항-및-개선-제안)
6. [구현 우선순위 및 일정](#6-구현-우선순위-및-일정)
7. [테스트 계획](#7-테스트-계획)

---

## 1. 프로젝트 현황 분석

### 1.1 AS-IS (현재 상태)

#### ✅ 완료된 항목
| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| EC2 ↔ Redis ↔ RunPod 연결 | ✅ | Upstash Redis TLS 사용 |
| Faster-Whisper (STT) | ✅ | medium 모델, 한국어 지원 |
| Gemini 1.5 Flash (LLM) | ✅ | API 키 연동 완료 |
| `generate_reply_from_text` 태스크 | ✅ | 텍스트 대화 테스트 통과 |
| DB 스키마 (PostgreSQL) | ✅ | ChatSession, ChatLog, SessionPhoto 등 |
| API 엔드포인트 스캐폴딩 | ✅ | `/chat/*` 라우터 정의됨 |
| 모바일 앱 UI 스캐폴딩 | ✅ | ChatScreen, GalleryScreen 등 |

#### ⚠️ 제거 예정
| 구성 요소 | 상태 | 사유 |
|----------|------|------|
| QWEN3-TTS | 🗑️ 제거 | GPU 메모리/최적화 이슈 |
| Coqui XTTS v2 | 🗑️ 제거 | 동일 |

#### ❌ 미구현 (TO-DO)
| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| 음성 녹음 → 서버 전송 | ❌ | expo-av 코드 존재, API 미연동 |
| Polling 로직 | ❌ | task_id 활용 미구현 |
| 대기 애니메이션 | ❌ | Lottie/GIF 미적용 |
| expo-speech (기기 TTS) | ❌ | 패키지 미설치 |
| 에러 핸들링 (사용자 친화적) | ❌ | Alert만 사용 중 |

### 1.2 코드 분석 결과

#### Backend (`worker/tasks.py`)
```python
# 현재 상태: TTS 관련 코드가 주석 처리되어 있으나, synthesize_speech 함수가 
# generate_memory_video 내에서 여전히 호출됨 (Line 573)
# → 영상 생성 시 런타임 에러 발생 가능

# 반환 구조:
{
    "status": "success",
    "user_text": "인식된 텍스트",
    "ai_reply": "AI 답변",
    "audio_url": None  # TTS 비활성화
}
```

#### Backend (`app/routers/chat.py`)
```python
# 현재 상태: POST /messages/voice 구현됨
# 문제점:
# 1. 음성 파일 저장 경로가 하드코딩됨 (/app/data/)
# 2. ChatLog에 AI 응답 저장 로직 누락
# 3. sentiment(감정 태그) 미반환
```

#### Frontend (`ChatScreen.js`)
```javascript
// 현재 상태: 녹음 기능 존재
// 문제점:
// 1. API 호출 주석 처리 (임시 데이터 사용)
// 2. Polling 로직 없음
// 3. 로딩 중 단순 setTimeout으로 대체
// 4. expo-speech 미사용
```

---

## 2. 아키텍처 플로우차트

### 2.1 수정된 대화 세션 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              🎙️ 음성 대화 플로우                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐                                              ┌──────────────┐
│   📱 Mobile   │                                              │   🖥️ EC2     │
│  (React Native)                                             │  (FastAPI)   │
└──────┬───────┘                                              └──────┬───────┘
       │                                                              │
       │  1️⃣ 음성 녹음 (expo-av)                                       │
       │  ─────────────────────                                       │
       │  [onPressIn] → 녹음 시작                                      │
       │  [onPressOut] → 녹음 종료                                     │
       │                                                              │
       │  2️⃣ 음성 파일 업로드                                          │
       │ ─────────────────────────────────────────────────────────────►
       │  POST /chat/messages/voice                                   │
       │  FormData: { session_id, audio_file (m4a) }                  │
       │                                                              │
       │                           ┌──────────────────────────────────┤
       │                           │ 3️⃣ 음성 파일 S3 업로드 (선택)      │
       │                           │    Celery Task 큐잉               │
       │                           │    └─► Redis (Upstash)           │
       │                           └──────────────────────────────────┤
       │                                                              │
       │  4️⃣ task_id 즉시 반환                                        │
       │ ◄─────────────────────────────────────────────────────────────
       │  { task_id, status: "processing" }                           │
       │                                                              │
       │                                              ┌───────────────┴───────────────┐
       │                                              │         ⬇️ Redis              │
       │                                              └───────────────────────────────┘
       │                                                              │
       │                                              ┌───────────────┴───────────────┐
       │                                              │   🚀 RunPod (RTX 3090)        │
       │                                              │   Celery Worker               │
       │                                              │                               │
       │                                              │   ┌─────────────────────┐     │
       │                                              │   │ 5️⃣ STT (Whisper)    │     │
       │                                              │   │    음성 → 텍스트     │     │
       │                                              │   └──────────┬──────────┘     │
       │                                              │              │                │
       │                                              │   ┌──────────▼──────────┐     │
       │                                              │   │ 6️⃣ LLM (Gemini)     │     │
       │                                              │   │    대화 생성 + 감정  │     │
       │                                              │   └──────────┬──────────┘     │
       │                                              │              │                │
       │                                              │   ┌──────────▼──────────┐     │
       │                                              │   │ 7️⃣ DB 저장 (RDS)    │     │
       │                                              │   │    ChatLog 기록     │     │
       │                                              │   └──────────┬──────────┘     │
       │                                              │              │                │
       │                                              │   Result → Redis              │
       │                                              └───────────────────────────────┘
       │                                                              │
       │  8️⃣ Polling (1~2초 간격)                                     │
       │ ─────────────────────────────────────────────────────────────►
       │  GET /api/task/{task_id}                                     │
       │                                                              │
       │  9️⃣ 결과 반환                                                │
       │ ◄─────────────────────────────────────────────────────────────
       │  {                                                           │
       │    status: "success",                                        │
       │    user_text: "할머니가 말한 내용",                            │
       │    ai_reply: "AI 답변 텍스트",                                │
       │    sentiment: "happy" | "nostalgic" | "curious"              │
       │  }                                                           │
       │                                                              │
       │  🔟 UI 업데이트                                               │
       │  ─────────────────                                           │
       │  - 메시지 버블 추가                                           │
       │  - expo-speech로 TTS 재생                                    │
       │  - 강아지 애니메이션 전환                                      │
       │                                                              │
       ▼                                                              ▼
```

### 2.2 상태 머신 (State Machine)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ChatScreen 상태 머신                              │
└─────────────────────────────────────────────────────────────────────┘

                         ┌───────────────┐
                         │    IDLE       │
                         │  (대기 상태)   │
                         └───────┬───────┘
                                 │
                    [onPressIn - 마이크 버튼 누름]
                                 │
                                 ▼
                         ┌───────────────┐
                         │  RECORDING    │
                         │  (녹음 중)     │
                         │  🎤 빨간 표시  │
                         └───────┬───────┘
                                 │
                    [onPressOut - 마이크 버튼 뗌]
                                 │
                                 ▼
                         ┌───────────────┐
                         │  UPLOADING    │
                         │  (업로드 중)   │
                         │  📤 진행 표시  │
                         └───────┬───────┘
                                 │
                    [task_id 수신 성공]
                                 │
                                 ▼
                         ┌───────────────┐
                         │  PROCESSING   │
                         │  (AI 처리 중)  │◄────────┐
                         │  🐕 애니메이션  │         │
                         └───────┬───────┘         │
                                 │                 │
                    [Polling - 1.5초마다]           │
                                 │                 │
                    ┌────────────┴────────────┐    │
                    │                         │    │
            [status: pending/processing] [status: success/error]
                    │                         │
                    └─────────────────────────┘
                                              │
                                              ▼
                         ┌───────────────┐
                         │   SPEAKING    │
                         │  (TTS 재생 중) │
                         │  🔊 expo-speech │
                         └───────┬───────┘
                                 │
                    [TTS 재생 완료]
                                 │
                                 ▼
                         ┌───────────────┐
                         │    IDLE       │
                         └───────────────┘

                    ─────── 에러 발생 시 ───────
                    
                         ┌───────────────┐
                         │    ERROR      │
                         │  (에러 상태)   │
                         │  친화적 메시지  │
                         │  + 재시도 버튼 │
                         └───────┬───────┘
                                 │
                    [재시도 버튼 클릭]
                                 │
                                 ▼
                         ┌───────────────┐
                         │    IDLE       │
                         └───────────────┘
```

---

## 3. 백엔드 태스크

### 3.1 수정 대상 파일 목록

| 파일 | 수정 유형 | 설명 |
|------|---------|------|
| `worker/tasks.py` | 🔧 수정 | TTS 관련 코드 완전 제거, sentiment 반환 추가 |
| `app/routers/chat.py` | 🔧 수정 | ChatLog 저장 로직 추가, 응답 구조 개선 |
| `app/main.py` | 🔧 수정 | Task 결과 조회 엔드포인트 추가 |
| `common/s3_client.py` | 🔧 수정 | 음성 파일 업로드 함수 추가 (선택) |

### 3.2 상세 수정 포인트

#### 3.2.1 `worker/tasks.py` - TTS 제거 및 감정 분석 추가

```python
# ========== 수정 전 (Line 233-241) ==========
return {
    "status": "success",
    "user_text": user_text,
    "ai_reply": ai_reply,
    "audio_url": None  # TTS 비활성화
}

# ========== 수정 후 ==========
return {
    "status": "success",
    "user_text": user_text,
    "ai_reply": ai_reply,
    "sentiment": analyze_sentiment(ai_reply),  # 감정 태그 추가
    "turn_count": turn_count  # 현재 턴 수 반환
}

# ========== 새로 추가할 함수 ==========
def analyze_sentiment(text: str) -> str:
    """
    AI 답변의 감정을 분석하여 강아지 애니메이션 결정
    
    Returns:
        str: "happy" | "curious" | "nostalgic" | "excited" | "comforting"
    """
    # 간단한 키워드 기반 분석 (향후 Gemini로 개선 가능)
    happy_keywords = ["좋", "기뻐", "행복", "웃", "재밌"]
    curious_keywords = ["뭐", "어디", "누구", "언제", "왜", "어떻게"]
    nostalgic_keywords = ["추억", "옛날", "그때", "기억", "예전"]
    
    for kw in curious_keywords:
        if kw in text:
            return "curious"
    for kw in nostalgic_keywords:
        if kw in text:
            return "nostalgic"
    for kw in happy_keywords:
        if kw in text:
            return "happy"
    
    return "comforting"  # 기본값
```

#### 3.2.2 `worker/tasks.py` - 영상 생성에서 TTS 호출 제거

```python
# ========== 수정 전 (Line 573) ==========
synthesize_speech(narration_text, narration_audio_path)

# ========== 수정 후 ==========
# TTS 제거: 영상은 배경음악만 사용하거나, 텍스트 자막으로 대체
# 옵션 1: 배경음악 사용
bgm_path = "/app/data/bgm_emotional.mp3"  # 미리 준비된 BGM

# 옵션 2: TTS API 외부 서비스 사용 (선택)
# narration_audio_path = call_external_tts_api(narration_text)
```

#### 3.2.3 `app/routers/chat.py` - ChatLog 저장 로직 추가

```python
# ========== 수정 전: POST /messages/voice (Line 280-315) ==========
# 현재: task_id만 반환, ChatLog 저장 없음

# ========== 수정 후 ==========
@router.post("/messages/voice", summary="음성 메시지 처리")
async def send_voice_message(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """음성 메시지 전송 및 처리 (개선됨)"""
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 1. 음성 파일 S3 업로드 (영구 저장)
    from common.s3_client import upload_audio_file
    audio_s3_url = await upload_audio_file(
        file=audio_file,
        user_id=str(session.user_id),
        session_id=session_id
    )
    
    # 2. 사용자 메시지 ChatLog에 저장 (음성 URL 포함)
    user_log = ChatLog(
        session_id=session.id,
        role="user",
        content="[음성 메시지]",
        voice_url=audio_s3_url
    )
    db.add(user_log)
    
    # 3. 턴 수 증가
    session.turn_count += 1
    db.commit()
    
    # 4. Celery 태스크 실행
    task = celery_app.send_task(
        "worker.tasks.process_audio_and_reply",
        args=[
            audio_s3_url,  # S3 URL 전달 (로컬 경로 대신)
            str(session.user_id),
            str(session.id)
        ],
        queue="ai_tasks"
    )
    
    return {
        "task_id": task.id,
        "status": "processing",
        "message": "복실이가 듣고 있어요...",
        "turn_count": session.turn_count,
        "can_finish": session.turn_count >= 3
    }
```

#### 3.2.4 `app/main.py` - Task 결과 조회 엔드포인트

```python
# ========== 새로 추가 ==========
from celery.result import AsyncResult

@app.get("/api/task/{task_id}", summary="Celery 태스크 결과 조회")
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """
    Celery 비동기 태스크의 결과를 조회합니다.
    프론트엔드에서 Polling 방식으로 호출합니다.
    """
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state == "PENDING":
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "복실이가 열심히 듣고 있어요..."
        }
    
    elif result.state == "STARTED" or result.state == "PROCESSING":
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "복실이가 생각하고 있어요..."
        }
    
    elif result.state == "SUCCESS":
        task_result = result.get()
        
        # AI 응답을 ChatLog에 저장 (Worker에서 처리 안 된 경우)
        if task_result.get("status") == "success":
            session_id = task_result.get("session_id")
            if session_id:
                ai_log = ChatLog(
                    session_id=uuid.UUID(session_id),
                    role="assistant",
                    content=task_result.get("ai_reply", "")
                )
                db.add(ai_log)
                db.commit()
        
        return {
            "task_id": task_id,
            "status": "success",
            **task_result
        }
    
    elif result.state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "error",
            "message": "죄송해요, 다시 말씀해주세요.",
            "error_detail": str(result.info)
        }
    
    return {
        "task_id": task_id,
        "status": result.state.lower()
    }
```

### 3.3 API Response 예시

#### POST `/chat/messages/voice` (즉시 응답)
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "message": "복실이가 듣고 있어요...",
  "turn_count": 2,
  "can_finish": false
}
```

#### GET `/api/task/{task_id}` (Polling 응답 - 처리 중)
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "message": "복실이가 생각하고 있어요..."
}
```

#### GET `/api/task/{task_id}` (Polling 응답 - 완료)
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "success",
  "user_text": "그때 바닷가에서 조개를 주웠어요",
  "ai_reply": "와, 바닷가에서 조개를 주우셨군요! 그때 누구랑 함께 가셨어요? 정말 재밌었겠어요!",
  "sentiment": "curious"
}
```

---

## 4. 프론트엔드 태스크

### 4.1 수정 대상 파일 목록

| 파일 | 수정 유형 | 설명 |
|------|---------|------|
| `package.json` | 📦 패키지 추가 | expo-speech 추가 |
| `src/api/config.js` | 🔧 수정 | FormData 전송 함수 추가 |
| `src/screens/ChatScreen.js` | 🔧 대폭 수정 | 상태 머신, Polling, TTS 구현 |
| `src/hooks/useChatSession.js` | ✨ 신규 | 대화 세션 상태 관리 커스텀 훅 |
| `src/hooks/useVoiceRecording.js` | ✨ 신규 | 음성 녹음 로직 분리 |
| `src/hooks/usePolling.js` | ✨ 신규 | Polling 로직 커스텀 훅 |
| `src/components/DogAnimation.js` | ✨ 신규 | 강아지 애니메이션 컴포넌트 |
| `src/utils/speech.js` | ✨ 신규 | expo-speech 유틸리티 |

### 4.2 패키지 설치

```bash
# expo-speech 설치 (기기 내장 TTS)
npx expo install expo-speech

# Lottie 애니메이션 (선택)
npx expo install lottie-react-native
```

### 4.3 상세 구현 계획

#### 4.3.1 `src/api/config.js` - FormData 지원 추가

```javascript
// ========== 추가할 함수 ==========

/**
 * FormData(파일 업로드) 전송용 함수
 */
export const uploadFormData = async (endpoint, formData) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  // Content-Type은 FormData에서 자동 설정 (multipart/form-data)
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return response.json();
};

/**
 * Polling용 함수 (타임아웃 포함)
 */
export const pollTaskResult = async (taskId, options = {}) => {
  const {
    interval = 1500,      // 폴링 간격 (ms)
    timeout = 60000,      // 최대 대기 시간 (ms)
    onProgress = () => {} // 진행 콜백
  } = options;
  
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const result = await api.get(`/api/task/${taskId}`);
    
    onProgress(result);
    
    if (result.status === 'success' || result.status === 'error') {
      return result;
    }
    
    // 대기
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error('TIMEOUT');
};
```

#### 4.3.2 `src/hooks/useVoiceRecording.js` - 음성 녹음 훅

```javascript
import { useState, useRef, useCallback } from 'react';
import { Audio } from 'expo-av';
import { Alert } from 'react-native';

export const useVoiceRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const recordingRef = useRef(null);

  // 권한 요청
  const requestPermission = useCallback(async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionGranted(status === 'granted');
      
      if (status !== 'granted') {
        Alert.alert(
          '마이크 권한 필요',
          '복실이와 대화하려면 마이크 권한이 필요해요.',
          [{ text: '알겠어요', style: 'default' }]
        );
        return false;
      }
      return true;
    } catch (error) {
      console.error('권한 요청 실패:', error);
      return false;
    }
  }, []);

  // 녹음 시작
  const startRecording = useCallback(async () => {
    if (!permissionGranted) {
      const granted = await requestPermission();
      if (!granted) return null;
    }

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      recordingRef.current = recording;
      setIsRecording(true);
      return recording;
    } catch (error) {
      console.error('녹음 시작 실패:', error);
      Alert.alert('녹음 오류', '녹음을 시작할 수 없어요. 다시 시도해주세요.');
      return null;
    }
  }, [permissionGranted, requestPermission]);

  // 녹음 종료
  const stopRecording = useCallback(async () => {
    if (!recordingRef.current) return null;

    try {
      setIsRecording(false);
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });

      return uri;
    } catch (error) {
      console.error('녹음 종료 실패:', error);
      return null;
    }
  }, []);

  // 녹음 취소
  const cancelRecording = useCallback(async () => {
    if (recordingRef.current) {
      try {
        await recordingRef.current.stopAndUnloadAsync();
      } catch {}
      recordingRef.current = null;
    }
    setIsRecording(false);
  }, []);

  return {
    isRecording,
    permissionGranted,
    startRecording,
    stopRecording,
    cancelRecording,
    requestPermission,
  };
};
```

#### 4.3.3 `src/hooks/usePolling.js` - Polling 훅

```javascript
import { useState, useRef, useCallback, useEffect } from 'react';
import api from '../api/config';

export const usePolling = (options = {}) => {
  const {
    interval = 1500,
    timeout = 60000,
    onSuccess = () => {},
    onError = () => {},
    onProgress = () => {},
  } = options;

  const [isPolling, setIsPolling] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [progressMessage, setProgressMessage] = useState('');
  
  const pollingRef = useRef(null);
  const startTimeRef = useRef(null);

  const startPolling = useCallback(async (taskId) => {
    setCurrentTaskId(taskId);
    setIsPolling(true);
    startTimeRef.current = Date.now();

    const poll = async () => {
      // 타임아웃 체크
      if (Date.now() - startTimeRef.current > timeout) {
        setIsPolling(false);
        onError({ type: 'TIMEOUT', message: '응답 시간이 너무 오래 걸려요.' });
        return;
      }

      try {
        const result = await api.get(`/api/task/${taskId}`);
        
        setProgressMessage(result.message || '');
        onProgress(result);

        if (result.status === 'success') {
          setIsPolling(false);
          onSuccess(result);
          return;
        }

        if (result.status === 'error') {
          setIsPolling(false);
          onError(result);
          return;
        }

        // 계속 폴링
        pollingRef.current = setTimeout(poll, interval);
      } catch (error) {
        setIsPolling(false);
        onError({ type: 'NETWORK', message: '네트워크 연결을 확인해주세요.' });
      }
    };

    poll();
  }, [interval, timeout, onSuccess, onError, onProgress]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    setIsPolling(false);
    setCurrentTaskId(null);
  }, []);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
      }
    };
  }, []);

  return {
    isPolling,
    currentTaskId,
    progressMessage,
    startPolling,
    stopPolling,
  };
};
```

#### 4.3.4 `src/utils/speech.js` - expo-speech 유틸리티

```javascript
import * as Speech from 'expo-speech';

/**
 * 노인 사용자를 위한 TTS 설정
 */
const SPEECH_OPTIONS = {
  language: 'ko-KR',    // 한국어
  pitch: 1.1,           // 약간 높은 피치 (밝은 느낌)
  rate: 0.8,            // 느린 속도 (또박또박)
  volume: 1.0,          // 최대 볼륨
};

/**
 * 텍스트를 음성으로 읽어주기
 */
export const speakText = (text, options = {}) => {
  return new Promise((resolve, reject) => {
    Speech.speak(text, {
      ...SPEECH_OPTIONS,
      ...options,
      onDone: resolve,
      onError: reject,
      onStopped: resolve,
    });
  });
};

/**
 * TTS 재생 중지
 */
export const stopSpeaking = () => {
  Speech.stop();
};

/**
 * TTS 재생 중인지 확인
 */
export const isSpeaking = async () => {
  return await Speech.isSpeakingAsync();
};

/**
 * 감정에 따른 TTS 옵션 조정
 */
export const getSpeechOptionsForSentiment = (sentiment) => {
  const baseOptions = { ...SPEECH_OPTIONS };
  
  switch (sentiment) {
    case 'happy':
    case 'excited':
      return { ...baseOptions, pitch: 1.2, rate: 0.85 };
    case 'curious':
      return { ...baseOptions, pitch: 1.15, rate: 0.8 };
    case 'nostalgic':
      return { ...baseOptions, pitch: 1.0, rate: 0.75 };
    case 'comforting':
    default:
      return { ...baseOptions, pitch: 1.05, rate: 0.8 };
  }
};
```

#### 4.3.5 `src/components/DogAnimation.js` - 강아지 애니메이션

```javascript
import React, { useEffect, useRef } from 'react';
import { View, Animated, Easing, StyleSheet, Text } from 'react-native';
// import LottieView from 'lottie-react-native'; // Lottie 사용 시

/**
 * 강아지 애니메이션 컴포넌트
 * 상태에 따라 다른 애니메이션 표시
 */
const DogAnimation = ({ state, message }) => {
  const bounceAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    let animation;

    switch (state) {
      case 'listening':
        // 귀 기울이는 애니메이션 (갸웃)
        animation = Animated.loop(
          Animated.sequence([
            Animated.timing(rotateAnim, {
              toValue: 1,
              duration: 500,
              useNativeDriver: true,
            }),
            Animated.timing(rotateAnim, {
              toValue: -1,
              duration: 1000,
              useNativeDriver: true,
            }),
            Animated.timing(rotateAnim, {
              toValue: 0,
              duration: 500,
              useNativeDriver: true,
            }),
          ])
        );
        break;

      case 'thinking':
        // 생각하는 애니메이션 (통통 튀기)
        animation = Animated.loop(
          Animated.sequence([
            Animated.timing(bounceAnim, {
              toValue: -20,
              duration: 400,
              easing: Easing.out(Easing.quad),
              useNativeDriver: true,
            }),
            Animated.timing(bounceAnim, {
              toValue: 0,
              duration: 400,
              easing: Easing.in(Easing.bounce),
              useNativeDriver: true,
            }),
          ])
        );
        break;

      case 'speaking':
        // 말하는 애니메이션 (꼬리 흔들기)
        animation = Animated.loop(
          Animated.sequence([
            Animated.timing(rotateAnim, {
              toValue: 1,
              duration: 200,
              useNativeDriver: true,
            }),
            Animated.timing(rotateAnim, {
              toValue: -1,
              duration: 400,
              useNativeDriver: true,
            }),
            Animated.timing(rotateAnim, {
              toValue: 0,
              duration: 200,
              useNativeDriver: true,
            }),
          ])
        );
        break;

      default:
        // idle - 정지
        bounceAnim.setValue(0);
        rotateAnim.setValue(0);
        return;
    }

    animation.start();
    return () => animation.stop();
  }, [state, bounceAnim, rotateAnim]);

  const rotation = rotateAnim.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-10deg', '0deg', '10deg'],
  });

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.dogContainer,
          {
            transform: [
              { translateY: bounceAnim },
              { rotate: rotation },
            ],
          },
        ]}
      >
        {/* 강아지 이미지 또는 Lottie */}
        <Text style={styles.dogEmoji}>🐕</Text>
      </Animated.View>
      
      {message && (
        <View style={styles.messageBubble}>
          <Text style={styles.messageText}>{message}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  dogContainer: {
    width: 100,
    height: 100,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dogEmoji: {
    fontSize: 80,
  },
  messageBubble: {
    backgroundColor: '#FFF',
    borderRadius: 15,
    padding: 12,
    marginTop: 10,
    maxWidth: '80%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  messageText: {
    fontSize: 16,
    color: '#333',
    textAlign: 'center',
  },
});

export default DogAnimation;
```

#### 4.3.6 `src/screens/ChatScreen.js` - 전체 리팩토링

```javascript
/**
 * 대화 화면 (리팩토링 버전)
 * - 상태 머신 기반 UI 제어
 * - Polling을 통한 비동기 처리
 * - expo-speech TTS 연동
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  Alert,
  Modal,
  Dimensions,
} from 'react-native';
import { colors, fonts } from '../theme';
import { useVoiceRecording } from '../hooks/useVoiceRecording';
import { usePolling } from '../hooks/usePolling';
import { uploadFormData } from '../api/config';
import { speakText, stopSpeaking, getSpeechOptionsForSentiment } from '../utils/speech';
import DogAnimation from '../components/DogAnimation';
import api from '../api/config';

const { width } = Dimensions.get('window');

// 상태 정의
const CHAT_STATE = {
  IDLE: 'idle',
  RECORDING: 'recording',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  SPEAKING: 'speaking',
  ERROR: 'error',
};

const ChatScreen = ({ route, navigation }) => {
  const { photoId, photoUrl, photoDate } = route.params;
  
  // ============ 상태 ============
  const [chatState, setChatState] = useState(CHAT_STATE.IDLE);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [turnCount, setTurnCount] = useState(0);
  const [relatedPhotos, setRelatedPhotos] = useState([]);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');
  
  // 모달 상태
  const [showEndModal, setShowEndModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);
  
  const scrollViewRef = useRef(null);

  // ============ 훅 ============
  const {
    isRecording,
    startRecording,
    stopRecording,
    cancelRecording,
    requestPermission,
  } = useVoiceRecording();

  const {
    isPolling,
    progressMessage,
    startPolling,
    stopPolling,
  } = usePolling({
    interval: 1500,
    timeout: 60000,
    onProgress: (result) => {
      setProcessingMessage(result.message || '복실이가 생각하고 있어요...');
    },
    onSuccess: handleAIResponse,
    onError: handleError,
  });

  // ============ 초기화 ============
  useEffect(() => {
    initializeSession();
    requestPermission();
    
    return () => {
      stopSpeaking();
      stopPolling();
    };
  }, []);

  const initializeSession = async () => {
    try {
      // 1. 세션 시작 API 호출
      const response = await api.post('/chat/sessions', {
        kakao_id: 'test_user',  // TODO: 실제 사용자 ID
        photo_id: photoId,
      });
      setSessionId(response.id);
      
      // 2. 연관 사진 가져오기
      const photosResponse = await api.get(
        `/chat/sessions/next-photos?session_id=${response.id}`
      );
      setRelatedPhotos([
        { id: photoId, url: photoUrl, date: photoDate },
        ...photosResponse,
      ]);
      
      // 3. 첫 인사 메시지
      const greeting = '우와, 할머니! 이 사진 어디서 찍은 거예요? 정말 멋진 곳이네요!';
      addMessage('assistant', greeting);
      
      // 4. 첫 인사 TTS 재생
      await speakText(greeting);
      
    } catch (error) {
      console.error('세션 초기화 실패:', error);
      // 오프라인 또는 에러 시 임시 세션으로 진행
      setSessionId('temp-session-id');
      addMessage('assistant', '안녕하세요, 할머니! 이 사진에 대해 이야기해주세요~');
    }
  };

  // ============ 메시지 관리 ============
  const addMessage = useCallback((role, content, extra = {}) => {
    setMessages(prev => [...prev, { 
      id: Date.now(),
      role, 
      content,
      ...extra,
    }]);
    
    // 스크롤 하단으로
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, []);

  // ============ AI 응답 처리 ============
  async function handleAIResponse(result) {
    setChatState(CHAT_STATE.SPEAKING);
    
    // 1. 사용자 메시지 업데이트 (STT 결과)
    setMessages(prev => {
      const updated = [...prev];
      const lastUserMsg = updated.findIndex(
        m => m.role === 'user' && m.content === '[음성 메시지]'
      );
      if (lastUserMsg !== -1) {
        updated[lastUserMsg].content = result.user_text;
      }
      return updated;
    });
    
    // 2. AI 응답 메시지 추가
    addMessage('assistant', result.ai_reply, { sentiment: result.sentiment });
    setTurnCount(prev => prev + 1);
    
    // 3. TTS로 읽어주기
    const speechOptions = getSpeechOptionsForSentiment(result.sentiment);
    try {
      await speakText(result.ai_reply, speechOptions);
    } catch (error) {
      console.warn('TTS 재생 실패:', error);
    }
    
    setChatState(CHAT_STATE.IDLE);
  }

  // ============ 에러 처리 ============
  function handleError(error) {
    setChatState(CHAT_STATE.ERROR);
    
    let errorMessage = '다시 한번 말씀해주세요.';
    
    if (error.type === 'TIMEOUT') {
      errorMessage = '응답이 늦어지고 있어요. 다시 시도해주세요.';
    } else if (error.type === 'NETWORK') {
      errorMessage = '인터넷 연결을 확인해주세요.';
    }
    
    // 친화적인 에러 표시
    Alert.alert(
      '앗, 잠깐요!',
      errorMessage,
      [
        {
          text: '다시 시도',
          onPress: () => setChatState(CHAT_STATE.IDLE),
        },
      ]
    );
  }

  // ============ 녹음 핸들러 ============
  const handlePressIn = async () => {
    if (chatState !== CHAT_STATE.IDLE) return;
    
    const recording = await startRecording();
    if (recording) {
      setChatState(CHAT_STATE.RECORDING);
    }
  };

  const handlePressOut = async () => {
    if (chatState !== CHAT_STATE.RECORDING) return;
    
    const audioUri = await stopRecording();
    
    if (!audioUri) {
      setChatState(CHAT_STATE.IDLE);
      return;
    }
    
    // 업로드 및 처리
    await uploadAndProcess(audioUri);
  };

  const uploadAndProcess = async (audioUri) => {
    setChatState(CHAT_STATE.UPLOADING);
    addMessage('user', '[음성 메시지]');
    
    try {
      // FormData 생성
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('audio_file', {
        uri: audioUri,
        type: 'audio/x-m4a',
        name: 'recording.m4a',
      });
      
      // 업로드
      const response = await uploadFormData('/chat/messages/voice', formData);
      
      // Polling 시작
      setChatState(CHAT_STATE.PROCESSING);
      setProcessingMessage('복실이가 듣고 있어요...');
      startPolling(response.task_id);
      
    } catch (error) {
      console.error('업로드 실패:', error);
      handleError({ type: 'NETWORK' });
    }
  };

  // ============ 사진 네비게이션 ============
  const handleNextPhoto = () => {
    if (currentPhotoIndex < relatedPhotos.length - 1) {
      setCurrentPhotoIndex(prev => prev + 1);
      addMessage('assistant', '다른 사진도 있네요! 이건 어떤 사진이에요?');
    }
  };

  const handlePrevPhoto = () => {
    if (currentPhotoIndex > 0) {
      setCurrentPhotoIndex(prev => prev - 1);
    }
  };

  // ============ 대화 종료 ============
  const handleEndChat = () => {
    if (turnCount < 3) {
      Alert.alert(
        '조금 더 이야기해요',
        '복실이와 조금 더 대화한 후에 종료할 수 있어요.',
        [{ text: '알겠어요', style: 'default' }]
      );
      return;
    }
    setShowEndModal(true);
  };

  const confirmEndChat = async (wantToEnd) => {
    setShowEndModal(false);
    if (wantToEnd) {
      setShowVideoModal(true);
    }
  };

  const confirmCreateVideo = async (wantToCreate) => {
    setShowVideoModal(false);
    
    if (wantToCreate) {
      setIsCreatingVideo(true);
      try {
        const response = await api.patch(
          `/chat/sessions/${sessionId}/finish?create_video=true`
        );
        
        // 영상 생성 상태 폴링 (별도 구현 필요)
        Alert.alert(
          '영상 제작 시작!',
          '영상이 완성되면 알려드릴게요. 추억 극장에서 확인해주세요!',
          [{ text: '홈으로', onPress: () => navigation.navigate('Home') }]
        );
      } catch (error) {
        Alert.alert('오류', '영상 제작을 시작할 수 없어요.');
      } finally {
        setIsCreatingVideo(false);
      }
    } else {
      navigation.navigate('Home');
    }
  };

  // ============ 렌더링 헬퍼 ============
  const getMicButtonStyle = () => {
    switch (chatState) {
      case CHAT_STATE.RECORDING:
        return [styles.micButton, styles.micButtonRecording];
      case CHAT_STATE.UPLOADING:
      case CHAT_STATE.PROCESSING:
        return [styles.micButton, styles.micButtonDisabled];
      default:
        return styles.micButton;
    }
  };

  const getMicButtonText = () => {
    switch (chatState) {
      case CHAT_STATE.RECORDING:
        return '말하는 중...';
      case CHAT_STATE.UPLOADING:
        return '전송 중...';
      case CHAT_STATE.PROCESSING:
        return processingMessage || '생각 중...';
      case CHAT_STATE.SPEAKING:
        return '복실이가 말하는 중...';
      default:
        return '꾹 눌러서 말하기';
    }
  };

  const currentPhoto = relatedPhotos[currentPhotoIndex] || { url: photoUrl };

  // ============ 렌더링 ============
  return (
    <View style={styles.container}>
      {/* 사진 영역 */}
      <View style={styles.photoSection}>
        <Image
          source={{ uri: currentPhoto.url }}
          style={styles.mainPhoto}
          resizeMode="cover"
        />
        
        {/* 사진 네비게이션 */}
        {currentPhotoIndex > 0 && (
          <TouchableOpacity
            style={[styles.navButton, styles.prevButton]}
            onPress={handlePrevPhoto}
          >
            <Text style={styles.navButtonText}>{'<'}</Text>
          </TouchableOpacity>
        )}
        {currentPhotoIndex < relatedPhotos.length - 1 && (
          <TouchableOpacity
            style={[styles.navButton, styles.nextButton]}
            onPress={handleNextPhoto}
          >
            <Text style={styles.navButtonText}>{'>'}</Text>
          </TouchableOpacity>
        )}
        
        {/* 인디케이터 */}
        <View style={styles.photoIndicator}>
          {relatedPhotos.map((_, index) => (
            <View
              key={index}
              style={[
                styles.indicatorDot,
                index === currentPhotoIndex && styles.indicatorDotActive,
              ]}
            />
          ))}
        </View>
      </View>

      {/* 대화 영역 */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.chatArea}
        contentContainerStyle={styles.chatContent}
      >
        {messages.map((msg) => (
          <View
            key={msg.id}
            style={[
              styles.messageBubble,
              msg.role === 'user' ? styles.userBubble : styles.assistantBubble,
            ]}
          >
            {msg.role === 'assistant' && (
              <Text style={styles.senderName}>복실이</Text>
            )}
            <Text style={styles.messageText}>{msg.content}</Text>
          </View>
        ))}
        
        {/* 처리 중 애니메이션 */}
        {(chatState === CHAT_STATE.PROCESSING || chatState === CHAT_STATE.SPEAKING) && (
          <DogAnimation
            state={chatState === CHAT_STATE.PROCESSING ? 'thinking' : 'speaking'}
            message={processingMessage}
          />
        )}
      </ScrollView>

      {/* 하단 컨트롤 */}
      <View style={styles.controlArea}>
        <TouchableOpacity
          style={getMicButtonStyle()}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          disabled={chatState !== CHAT_STATE.IDLE}
        >
          <Text style={styles.micIcon}>
            {chatState === CHAT_STATE.RECORDING ? '🔴' : '🎤'}
          </Text>
          <Text style={styles.micButtonText}>{getMicButtonText()}</Text>
        </TouchableOpacity>

        {turnCount >= 3 && chatState === CHAT_STATE.IDLE && (
          <TouchableOpacity style={styles.endButton} onPress={handleEndChat}>
            <Text style={styles.endButtonText}>대화 종료</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* 모달들 (기존 코드 유지) */}
      {/* ... 기존 Modal 컴포넌트들 ... */}
    </View>
  );
};

// 스타일 (기존 + 추가)
const styles = StyleSheet.create({
  // ... 기존 스타일 유지 ...
  
  micButtonRecording: {
    backgroundColor: '#FF6347',
    transform: [{ scale: 1.1 }],
  },
  micButtonDisabled: {
    backgroundColor: '#CCCCCC',
    opacity: 0.7,
  },
});

export default ChatScreen;
```

---

## 5. 누락 사항 및 개선 제안

### 5.1 현재 UI 코드에서 발견된 누락 사항

| 항목 | 현재 상태 | 필요 조치 |
|------|---------|----------|
| **실제 API 연동** | 모든 API 호출 주석 처리 | 주석 해제 및 연동 |
| **kakao_id 하드코딩** | `'test_user'` 고정 | 로그인 상태에서 동적 로드 |
| **에러 핸들링** | 단순 Alert | 사용자 친화적 모달 + 재시도 |
| **오프라인 대응** | 없음 | NetInfo 활용 체크 |
| **애니메이션** | 없음 (텍스트만) | Lottie/Animated 적용 |
| **TTS** | 없음 | expo-speech 통합 |

### 5.2 UX 개선 제안

#### 5.2.1 expo-speech 활용 (✅ 필수)
```javascript
// 서버 TTS 없이 기기 내장 TTS 사용
// 장점: 지연 시간 없음, 추가 비용 없음
// 설정: 한국어(ko-KR), 느린 속도(0.8), 높은 피치(1.1)

await Speech.speak("할머니, 그때 정말 좋았겠어요!", {
  language: 'ko-KR',
  rate: 0.8,
  pitch: 1.1,
});
```

#### 5.2.2 오프라인 대응
```javascript
import NetInfo from '@react-native-community/netinfo';

// 네트워크 상태 확인
const checkNetwork = async () => {
  const state = await NetInfo.fetch();
  if (!state.isConnected) {
    Alert.alert(
      '인터넷 연결 필요',
      '복실이와 대화하려면 인터넷이 필요해요.',
      [{ text: '다시 확인', onPress: checkNetwork }]
    );
    return false;
  }
  return true;
};
```

#### 5.2.3 친화적 에러 메시지

| 에러 유형 | 기존 메시지 | 개선 메시지 |
|----------|-----------|-----------|
| 녹음 실패 | "녹음을 시작할 수 없습니다." | "마이크가 작동하지 않아요. 다시 눌러주세요." |
| 네트워크 에러 | "Error" | "인터넷 연결이 끊겼어요. 잠시 후 다시 해주세요." |
| 타임아웃 | (없음) | "복실이가 생각이 많아요. 잠시만 기다려주세요." |
| 서버 에러 | "500 Error" | "복실이가 잠깐 졸았어요. 다시 말씀해주세요." |

#### 5.2.4 시각적 피드백 강화

```javascript
// 녹음 중 시각적 피드백
// 1. 마이크 버튼 색상 변경 (노란색 → 빨간색)
// 2. 펄스 애니메이션 (크기 변화)
// 3. 진동 피드백 (Haptics)

import * as Haptics from 'expo-haptics';

const handlePressIn = async () => {
  // 햅틱 피드백
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  // ...
};
```

### 5.3 추가 화면 필요 여부

현재 구현된 화면들로 MVP는 충분하나, 다음 화면 개선 권장:

| 화면 | 현재 상태 | 개선 사항 |
|------|---------|----------|
| `ChatHistoryDetailScreen.js` | 기본 구현 | 대화 로그 재생(TTS) 기능 |
| `VideoGalleryScreen.js` | 미확인 | 영상 재생 + 공유 기능 |
| `ProfileScreen.js` | 기본 구현 | 반려견 이름 설정 |

---

## 6. 구현 우선순위 및 일정

### 6.1 우선순위 매트릭스

```
긴급도 ↑
     │
  P1 │ ████████████████
     │ • Polling 구현
     │ • API 연동 (음성 전송)
     │ • expo-speech 통합
     │ ────────────────────
  P2 │ ████████████
     │ • 에러 핸들링 개선
     │ • 상태 머신 적용
     │ • 강아지 애니메이션
     │ ────────────────────
  P3 │ ████████
     │ • 오프라인 대응
     │ • 햅틱 피드백
     │ • 성능 최적화
     │
     └──────────────────────→ 중요도
```

### 6.2 구현 일정 (예상)

| Phase | 기간 | 태스크 |
|-------|------|--------|
| **Phase 1** | Day 1-2 | Backend TTS 제거, sentiment 추가, Task API |
| **Phase 2** | Day 2-3 | Frontend hooks 구현 (Recording, Polling) |
| **Phase 3** | Day 3-4 | ChatScreen 리팩토링, API 연동 |
| **Phase 4** | Day 4-5 | expo-speech 통합, 애니메이션 |
| **Phase 5** | Day 5-6 | 테스트 및 버그 수정 |
| **Phase 6** | Day 6-7 | UX 개선, 에러 핸들링 강화 |

---

## 7. 테스트 계획

### 7.1 단위 테스트

| 모듈 | 테스트 항목 |
|------|-----------|
| `useVoiceRecording` | 권한 요청, 녹음 시작/종료, 파일 생성 |
| `usePolling` | 상태 변화, 타임아웃, 성공/실패 콜백 |
| `speech.js` | TTS 재생, 감정별 설정 |

### 7.2 통합 테스트

```bash
# 1. EC2 API 서버 테스트
curl -X POST "http://54.180.28.75:8000/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{"kakao_id": "test", "photo_id": "uuid"}'

# 2. 음성 업로드 테스트
curl -X POST "http://54.180.28.75:8000/chat/messages/voice" \
  -F "session_id=uuid" \
  -F "audio_file=@test.m4a"

# 3. Task 결과 조회 테스트
curl "http://54.180.28.75:8000/api/task/{task_id}"
```

### 7.3 E2E 시나리오 테스트

1. **정상 플로우**
   - 앱 실행 → 갤러리 → 사진 선택 → 대화 시작
   - 마이크 버튼 누름 → 녹음 → 버튼 뗌
   - 로딩 애니메이션 표시
   - AI 응답 표시 + TTS 재생
   - 3턴 후 종료 버튼 활성화
   - 영상 생성 → 완료

2. **에러 플로우**
   - 네트워크 끊김 시 재시도 버튼
   - 녹음 권한 거부 시 안내
   - 서버 타임아웃 시 친화적 메시지

3. **어르신 UX 테스트**
   - 글씨 크기 가독성 (70대 기준)
   - 버튼 터치 영역 충분한지
   - TTS 속도/피치 적절한지

---

## 📌 체크리스트

### Backend
- [ ] `worker/tasks.py` - TTS 관련 코드 완전 제거
- [ ] `worker/tasks.py` - `analyze_sentiment()` 함수 추가
- [ ] `worker/tasks.py` - `generate_memory_video` TTS 호출 제거
- [ ] `app/routers/chat.py` - ChatLog AI 응답 저장 로직
- [ ] `app/main.py` - `/api/task/{task_id}` 엔드포인트
- [ ] 테스트: Celery 태스크 실행 확인

### Frontend
- [ ] `expo-speech` 패키지 설치
- [ ] `src/hooks/useVoiceRecording.js` 생성
- [ ] `src/hooks/usePolling.js` 생성
- [ ] `src/utils/speech.js` 생성
- [ ] `src/components/DogAnimation.js` 생성
- [ ] `src/api/config.js` - `uploadFormData` 추가
- [ ] `ChatScreen.js` 리팩토링
- [ ] 테스트: 녹음 → 업로드 → Polling → TTS

---

## 🚀 다음 단계

승인 후 다음 순서로 진행됩니다:

1. **Backend 수정** (Phase 1)
2. **Frontend hooks 구현** (Phase 2)
3. **ChatScreen 리팩토링** (Phase 3)
4. **통합 테스트** (Phase 5)

---

> **문서 버전**: v1.0  
> **최종 수정**: 2026-01-27  
> **작성자**: GitHub Copilot (Claude Opus 4.5)
