/**
 * Polling 커스텀 훅
 * Task 결과 확인을 위한 1초 간격 폴링
 */
import { useState, useCallback, useRef } from 'react';
import { pollTaskResult } from '../api/config';

/**
 * Polling 상태 관리 훅
 * @param {Object} options - 설정 옵션
 * @returns {Object} polling 관련 상태와 함수
 */
const usePolling = (options = {}) => {
  const {
    interval = 1000,      // 1초 간격
    timeout = 60000,      // 60초 타임아웃
  } = options;

  const [isPolling, setIsPolling] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(false);

  /**
   * Polling 시작
   * @param {string} taskId - Task ID
   * @param {Function} onSuccess - 성공 콜백
   * @param {Function} onError - 실패 콜백
   */
  const startPolling = useCallback(async (taskId, onSuccess, onError) => {
    if (isPolling) {
      console.warn('이미 Polling 중입니다.');
      return;
    }

    setIsPolling(true);
    setError(null);
    setProgress(null);
    abortRef.current = false;

    const result = await pollTaskResult(taskId, {
      interval,
      timeout,
      onProgress: (data) => {
        if (abortRef.current) return;
        setProgress(data);
      },
    });

    if (abortRef.current) {
      setIsPolling(false);
      return;
    }

    setIsPolling(false);

    if (result.success) {
      if (onSuccess) onSuccess(result.data);
    } else {
      setError(result.error);
      if (onError) onError(result.error);
    }
  }, [isPolling, interval, timeout]);

  /**
   * Polling 중지
   */
  const stopPolling = useCallback(() => {
    abortRef.current = true;
    setIsPolling(false);
    setProgress(null);
  }, []);

  /**
   * 에러 초기화
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isPolling,
    progress,
    error,
    startPolling,
    stopPolling,
    clearError,
  };
};

export default usePolling;
