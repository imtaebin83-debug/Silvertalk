/**
 * 채팅 세션 관리 커스텀 훅
 * 세션 생명주기, API 통신, 상태 머신, TTS 재생 통합 관리
 */
import { useState, useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import api, { uploadFormData, pollTaskResult } from '../api/config';
import * as Speech from 'expo-speech';

// 상태 머신 상태 정의
export const CHAT_STATES = {
  IDLE: 'IDLE',               // 대기 (버튼 활성화)
  RECORDING: 'RECORDING',     // 녹음 중
  UPLOADING: 'UPLOADING',     // 서버 전송 중
  POLLING: 'POLLING',         // AI 처리 대기 중
  SPEAKING: 'SPEAKING',       // TTS 재생 중
};

// Fallback 응답 (에러 시 사용)
const FALLBACK_RESPONSE = {
  user_text: '[인식 실패]',
  ai_reply: '할머니, 제가 잘 못 들었어요. 다시 말씀해 주시겠어요? 멍!',
  sentiment: 'curious',
};

/**
 * @param {Object} options - 옵션
 * @param {Function} options.onError - 에러 핸들러
 * @returns {Object} 세션 관련 상태와 함수
 */
const useChatSession = ({ onError } = {}) => {
  // === 세션 상태 ===
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [turnCount, setTurnCount] = useState(0);
  const [canFinish, setCanFinish] = useState(false);
  const [relatedPhotos, setRelatedPhotos] = useState([]);

  // === 상태 머신 ===
  const [chatState, setChatState] = useState(CHAT_STATES.IDLE);
  const [emotion, setEmotion] = useState('neutral');
  const [error, setError] = useState(null);

  // === Refs ===
  const isSpeakingRef = useRef(false);
  const currentTaskIdRef = useRef(null);

  /**
   * TTS 음성 설정 (노인 맞춤)
   */
  const TTS_OPTIONS = {
    language: 'ko-KR',
    rate: 0.85,      // 느린 속도
    pitch: 1.1,      // 약간 높은 음조
    voice: null,     // 기본 음성
  };

  /**
   * 메시지 추가
   */
  const addMessage = useCallback((role, content) => {
    setMessages((prev) => [
      ...prev,
      { role, content, timestamp: new Date() },
    ]);
  }, []);

  /**
   * 마지막 사용자 메시지 업데이트
   */
  const updateLastUserMessage = useCallback((content) => {
    setMessages((prev) => {
      const newMessages = [...prev];
      const lastUserIndex = newMessages.findLastIndex(
        (msg) => msg.role === 'user'
      );
      if (lastUserIndex !== -1) {
        newMessages[lastUserIndex].content = content;
      }
      return newMessages;
    });
  }, []);

  /**
   * TTS로 텍스트 읽기
   */
  const speakText = useCallback(async (text) => {
    return new Promise((resolve) => {
      isSpeakingRef.current = true;
      setChatState(CHAT_STATES.SPEAKING);

      Speech.speak(text, {
        ...TTS_OPTIONS,
        onDone: () => {
          isSpeakingRef.current = false;
          setChatState(CHAT_STATES.IDLE);
          setEmotion('neutral');
          resolve();
        },
        onStopped: () => {
          isSpeakingRef.current = false;
          setChatState(CHAT_STATES.IDLE);
          setEmotion('neutral');
          resolve();
        },
        onError: (error) => {
          console.error('TTS 에러:', error);
          isSpeakingRef.current = false;
          setChatState(CHAT_STATES.IDLE);
          setEmotion('neutral');
          resolve();
        },
      });
    });
  }, []);

  /**
   * TTS 중지
   */
  const stopSpeaking = useCallback(() => {
    if (isSpeakingRef.current) {
      Speech.stop();
      isSpeakingRef.current = false;
      setChatState(CHAT_STATES.IDLE);
      setEmotion('neutral');
    }
  }, []);

  /**
   * 세션 시작
   */
  const startSession = useCallback(async (photoId) => {
    try {
      setChatState(CHAT_STATES.POLLING);
      setEmotion('happy');

      // POST /chat/sessions
      const response = await api.post('/chat/sessions', {
        photo_id: photoId,
      });

      setSessionId(response.session_id || response.id);
      setRelatedPhotos(response.related_photos || []);

      // 첫 인사 메시지
      const greeting =
        response.greeting ||
        '우와, 할머니 이 사진 어디서 찍은 거예요? 정말 멋진 곳이네요!';

      addMessage('assistant', greeting);

      // TTS로 읽기
      await speakText(greeting);

      return { success: true, sessionId: response.session_id || response.id };
    } catch (error) {
      console.error('세션 시작 실패:', error);
      setError('세션을 시작할 수 없습니다.');
      setChatState(CHAT_STATES.IDLE);
      setEmotion('neutral');

      if (onError) {
        onError(error);
      }

      // Fallback: 데모 세션
      const demoSessionId = `demo-${Date.now()}`;
      setSessionId(demoSessionId);
      const demoGreeting = '우와, 할머니 이 사진 어디서 찍은 거예요?';
      addMessage('assistant', demoGreeting);
      await speakText(demoGreeting);

      return { success: false, error: error.message, sessionId: demoSessionId };
    }
  }, [addMessage, speakText, onError]);

  /**
   * 음성 메시지 전송
   */
  const sendVoiceMessage = useCallback(
    async (audioUri) => {
      try {
        if (!sessionId) {
          throw new Error('세션이 시작되지 않았습니다.');
        }

        // 상태 변경: UPLOADING
        setChatState(CHAT_STATES.UPLOADING);
        setEmotion('thinking');

        // 임시 메시지 추가
        addMessage('user', '[음성 인식 중...]');

        // FormData 생성
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('audio_file', {
          uri: audioUri,
          type: 'audio/m4a',
          name: `recording_${Date.now()}.m4a`,
        });

        // POST /chat/messages/voice
        const response = await uploadFormData('/chat/messages/voice', formData);

        if (!response.task_id) {
          throw new Error('Task ID를 받지 못했습니다.');
        }

        // Turn count 업데이트
        if (response.turn_count !== undefined) {
          setTurnCount(response.turn_count);
        }
        if (response.can_finish !== undefined) {
          setCanFinish(response.can_finish);
        }

        currentTaskIdRef.current = response.task_id;

        // Polling 시작
        await pollTask(response.task_id);

        return { success: true };
      } catch (error) {
        console.error('음성 전송 실패:', error);

        // 에러 메시지 업데이트
        updateLastUserMessage('[전송 실패]');

        setError('음성을 전송할 수 없습니다.');
        setChatState(CHAT_STATES.IDLE);
        setEmotion('neutral');

        Alert.alert('오류', '음성을 전송할 수 없습니다. 다시 시도해주세요.');

        if (onError) {
          onError(error);
        }

        return { success: false, error: error.message };
      }
    },
    [sessionId, addMessage, updateLastUserMessage, onError]
  );

  /**
   * Task Polling
   */
  const pollTask = useCallback(
    async (taskId) => {
      try {
        // 상태 변경: POLLING
        setChatState(CHAT_STATES.POLLING);
        setEmotion('thinking');

        // 1.5초 간격 폴링 (60초 타임아웃)
        const result = await pollTaskResult(taskId, {
          interval: 1500,
          timeout: 60000,
          onProgress: (status) => {
            console.log('Task status:', status.status);
          },
        });

        if (!result.success) {
          throw new Error(result.error || '처리 실패');
        }

        // 성공: 결과 처리
        const { user_text, ai_reply, sentiment } = result.data.result || FALLBACK_RESPONSE;

        // 사용자 메시지 업데이트
        updateLastUserMessage(user_text || '[인식 실패]');

        // AI 응답 추가
        addMessage('assistant', ai_reply);
        setEmotion(sentiment || 'neutral');

        // 서버에 대화 저장 (실패해도 계속 진행)
        try {
          await api.post('/chat/messages/save-ai-response', {
            session_id: sessionId,
            user_text: user_text || '',
            ai_reply: ai_reply,
          });
        } catch (saveError) {
          console.warn('대화 저장 실패:', saveError);
        }

        // TTS로 AI 응답 읽기
        await speakText(ai_reply);

        // Turn count 증가
        setTurnCount((prev) => prev + 1);
        if (turnCount + 1 >= 3) {
          setCanFinish(true);
        }

        return { success: true };
      } catch (error) {
        console.error('Polling 실패:', error);

        // Fallback 응답 사용
        updateLastUserMessage(FALLBACK_RESPONSE.user_text);
        addMessage('assistant', FALLBACK_RESPONSE.ai_reply);
        setEmotion(FALLBACK_RESPONSE.sentiment);

        await speakText(FALLBACK_RESPONSE.ai_reply);

        Alert.alert('알림', '응답을 받지 못했습니다. 다시 말씀해 주세요.');

        if (onError) {
          onError(error);
        }

        return { success: false, error: error.message };
      }
    },
    [sessionId, turnCount, addMessage, updateLastUserMessage, speakText, onError]
  );

  /**
   * 세션 종료
   */
  const endSession = useCallback(
    async (createVideo = false) => {
      try {
        stopSpeaking();

        if (!sessionId) {
          return { success: true };
        }

        // POST /chat/sessions/end
        const response = await api.post('/chat/sessions/end', {
          session_id: sessionId,
          create_video: createVideo,
        });

        // 영상 생성 Task ID 반환
        if (createVideo && response.video_task_id) {
          return {
            success: true,
            videoTaskId: response.video_task_id,
          };
        }

        return { success: true };
      } catch (error) {
        console.error('세션 종료 실패:', error);

        if (onError) {
          onError(error);
        }

        return { success: false, error: error.message };
      }
    },
    [sessionId, stopSpeaking, onError]
  );

  /**
   * 세션 리셋
   */
  const resetSession = useCallback(() => {
    stopSpeaking();
    setSessionId(null);
    setMessages([]);
    setTurnCount(0);
    setCanFinish(false);
    setRelatedPhotos([]);
    setChatState(CHAT_STATES.IDLE);
    setEmotion('neutral');
    setError(null);
    currentTaskIdRef.current = null;
  }, [stopSpeaking]);

  return {
    // 상태
    sessionId,
    messages,
    turnCount,
    canFinish,
    relatedPhotos,
    chatState,
    emotion,
    error,
    isSpeaking: isSpeakingRef.current,

    // 액션
    startSession,
    sendVoiceMessage,
    endSession,
    resetSession,
    stopSpeaking,

    // 상수
    CHAT_STATES,
  };
};

export default useChatSession;
