/**
 * expo-speech 래퍼 유틸리티
 * 어르신 사용자를 위한 고정 설정: 한국어, 속도 0.8, 피치 1.1
 */
import * as Speech from 'expo-speech';

// 고정 설정 (사용자 변경 불가)
const SPEECH_CONFIG = {
  language: 'ko-KR',
  rate: 0.8,      // 느린 속도 (어르신 배려)
  pitch: 1.1,     // 약간 높은 피치 (또렷한 발음)
};

/**
 * TTS로 텍스트 읽기
 * @param {string} text - 읽을 텍스트
 * @param {object} options - 추가 옵션 (onDone, onError, onStart)
 * @returns {Promise<void>}
 */
export const speak = (text, options = {}) => {
  return new Promise((resolve, reject) => {
    // 현재 재생 중이면 중지
    Speech.stop();
    
    Speech.speak(text, {
      ...SPEECH_CONFIG,
      onDone: () => {
        if (options.onDone) options.onDone();
        resolve();
      },
      onError: (error) => {
        if (options.onError) options.onError(error);
        reject(error);
      },
      onStart: () => {
        if (options.onStart) options.onStart();
      },
    });
  });
};

/**
 * TTS 중지
 */
export const stopSpeaking = () => {
  Speech.stop();
};

/**
 * TTS 재생 중인지 확인
 * @returns {Promise<boolean>}
 */
export const isSpeaking = async () => {
  return await Speech.isSpeakingAsync();
};

/**
 * 사용 가능한 음성 목록 조회 (디버깅용)
 * @returns {Promise<Array>}
 */
export const getAvailableVoices = async () => {
  return await Speech.getAvailableVoicesAsync();
};

export default {
  speak,
  stopSpeaking,
  isSpeaking,
  getAvailableVoices,
};
