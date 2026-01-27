/**
 * 음성 녹음 커스텀 훅
 * expo-av를 사용한 녹음 로직 캡슐화
 */
import { useState, useCallback, useRef } from 'react';
import { Audio } from 'expo-av';
import { Alert } from 'react-native';

/**
 * @returns {Object} 녹음 관련 상태와 함수
 */
const useVoiceRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(null);
  const recordingRef = useRef(null);

  /**
   * 마이크 권한 요청
   */
  const requestPermission = useCallback(async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      setPermissionGranted(permission.granted);
      return permission.granted;
    } catch (error) {
      console.error('마이크 권한 요청 실패:', error);
      setPermissionGranted(false);
      return false;
    }
  }, []);

  /**
   * 녹음 시작
   * @returns {Promise<boolean>} 성공 여부
   */
  const startRecording = useCallback(async () => {
    try {
      // 권한 확인
      if (permissionGranted === null) {
        const granted = await requestPermission();
        if (!granted) {
          Alert.alert('권한 필요', '마이크 권한이 필요합니다.');
          return false;
        }
      } else if (!permissionGranted) {
        Alert.alert('권한 필요', '마이크 권한이 필요합니다.');
        return false;
      }

      // 오디오 모드 설정
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      // 녹음 시작
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      recordingRef.current = recording;
      setIsRecording(true);
      return true;
    } catch (error) {
      console.error('녹음 시작 실패:', error);
      Alert.alert('오류', '녹음을 시작할 수 없습니다.');
      return false;
    }
  }, [permissionGranted, requestPermission]);

  /**
   * 녹음 중지
   * @returns {Promise<string|null>} 녹음 파일 URI 또는 null
   */
  const stopRecording = useCallback(async () => {
    try {
      if (!recordingRef.current) {
        console.warn('녹음 중이 아닙니다.');
        return null;
      }

      setIsRecording(false);
      await recordingRef.current.stopAndUnloadAsync();
      
      // 오디오 모드 복원 (재생 가능하도록)
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      });

      const uri = recordingRef.current.getURI();
      recordingRef.current = null;
      
      return uri;
    } catch (error) {
      console.error('녹음 중지 실패:', error);
      setIsRecording(false);
      recordingRef.current = null;
      return null;
    }
  }, []);

  /**
   * 녹음 취소 (파일 저장 안 함)
   */
  const cancelRecording = useCallback(async () => {
    try {
      if (recordingRef.current) {
        await recordingRef.current.stopAndUnloadAsync();
        recordingRef.current = null;
      }
      setIsRecording(false);
    } catch (error) {
      console.error('녹음 취소 실패:', error);
      setIsRecording(false);
      recordingRef.current = null;
    }
  }, []);

  return {
    isRecording,
    permissionGranted,
    requestPermission,
    startRecording,
    stopRecording,
    cancelRecording,
  };
};

export default useVoiceRecording;
