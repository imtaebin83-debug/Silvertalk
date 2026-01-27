/**
 * 대화 화면
 * 설계도 7-8번: 대표 사진 크게 표시, 연관 사진으로 넘기기, 3턴 후 종료 가능
 * 
 * 상태 머신:
 * - IDLE: 대기 (버튼 클릭 가능)
 * - RECORDING: 녹음 중 (PTT)
 * - PROCESSING: Polling 중 (버튼 비활성화)
 * - SPEAKING: TTS 재생 중 (버튼 비활성화)
 */
import React, { useState, useEffect, useRef } from 'react';
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
  ActivityIndicator,
} from 'react-native';
import { colors, fonts } from '../theme';
import api, { uploadFormData, pollTaskResult } from '../api/config';
import useVoiceRecording from '../hooks/useVoiceRecording';
import usePolling from '../hooks/usePolling';
import { speak, stopSpeaking } from '../utils/speech';
import DogAnimation from '../components/DogAnimation';

const { width } = Dimensions.get('window');

// 상태 머신 상태 정의
const STATES = {
  IDLE: 'IDLE',
  RECORDING: 'RECORDING',
  PROCESSING: 'PROCESSING',
  SPEAKING: 'SPEAKING',
};
 
const ChatScreen = ({ route, navigation }) => {
  // GalleryScreen에서 전달받은 파라미터
  const {
    sessionId: initialSessionId,
    photoUrl,
    photoDate,
    allPhotoUrls = [],  // S3에 업로드된 전체 사진 URL 배열
    mainPhotoIndex = 0  // 선택한 메인 사진의 인덱스
  } = route.params;

  // 디버그 로그
  console.log('📸 ChatScreen params:', {
    sessionId: initialSessionId,
    photoUrl,
    allPhotoUrls,
    mainPhotoIndex,
    allPhotoUrlsLength: allPhotoUrls?.length
  });

  // === 세션 상태 ===
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [messages, setMessages] = useState([]);
  const [turnCount, setTurnCount] = useState(0);
  const [canFinish, setCanFinish] = useState(false);

  // === 상태 머신 ===
  const [chatState, setChatState] = useState(STATES.IDLE);
  const [emotion, setEmotion] = useState('neutral');

  // === 연관 사진 (S3 URL 사용) ===
  const [relatedPhotos, setRelatedPhotos] = useState(
    allPhotoUrls.map((url, idx) => ({ url, order: idx }))
  );
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(mainPhotoIndex);
 
  // === 모달 상태 ===
  const [showEndModal, setShowEndModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);
  const [videoTaskId, setVideoTaskId] = useState(null);
  
  // === 훅 ===
  const voiceRecording = useVoiceRecording();
  const polling = usePolling({ interval: 1000, timeout: 60000 });
  
  // === Refs ===
  const scrollViewRef = useRef(null);

  // ============================================================
  // 초기화
  // ============================================================
  useEffect(() => {
    // GalleryScreen에서 이미 세션 생성 및 사진 업로드 완료
    // 첫 인사 메시지만 표시
    startGreeting();

    // 클린업: 언마운트 시 TTS 중지
    return () => {
      stopSpeaking();
    };
  }, []);

  // 새 메시지 시 스크롤
  useEffect(() => {
    if (scrollViewRef.current) {
      scrollViewRef.current.scrollToEnd({ animated: true });
    }
  }, [messages]);

  // ============================================================
  // API 호출 함수들
  // ============================================================
  const startGreeting = async () => {
    // 첫 인사 메시지
    const greeting = '우와, 할머니 이 사진 어디서 찍은 거예요? 정말 멋진 곳이네요!';
    addMessage('assistant', greeting);

    // TTS로 읽기
    setChatState(STATES.SPEAKING);
    setEmotion('happy');
    await speak(greeting);
    setChatState(STATES.IDLE);
    setEmotion('neutral');
  };

  // ============================================================
  // 메시지 관리
  // ============================================================
  const addMessage = (role, content) => {
    setMessages((prev) => [...prev, { role, content, timestamp: new Date() }]);
  };

  // ============================================================
  // 녹음 처리 (PTT - Push To Talk)
  // ============================================================
  const handleRecordStart = async () => {
    if (chatState !== STATES.IDLE) return;
    
    const success = await voiceRecording.startRecording();
    if (success) {
      setChatState(STATES.RECORDING);
      setEmotion('listening');
    }
  };

  const handleRecordEnd = async () => {
    if (chatState !== STATES.RECORDING) return;
    
    const audioUri = await voiceRecording.stopRecording();
    if (!audioUri) {
      setChatState(STATES.IDLE);
      setEmotion('neutral');
      return;
    }
    
    // UI에 임시 메시지 추가
    addMessage('user', '[음성 인식 중...]');
    
    // 서버로 전송
    await sendVoiceMessage(audioUri);
  };

  const sendVoiceMessage = async (audioUri) => {
    setChatState(STATES.PROCESSING);
    setEmotion('thinking');
    
    try {
      // FormData 생성
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('audio_file', {
        uri: audioUri,
        type: 'audio/x-m4a',
        name: 'recording.m4a',
      });
      
      // 서버로 전송
      const response = await uploadFormData('/chat/messages/voice', formData);
      
      if (response.task_id) {
        setTurnCount(response.turn_count || turnCount + 1);
        setCanFinish(response.can_finish || false);
        
        // Polling 시작
        await pollForResult(response.task_id);
      } else {
        throw new Error('Task ID를 받지 못했습니다.');
      }
      
    } catch (error) {
      console.error('음성 전송 실패:', error);
      
      // 에러 시 마지막 메시지 수정
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        if (newMessages[lastIndex]?.content === '[음성 인식 중...]') {
          newMessages[lastIndex].content = '[전송 실패]';
        }
        return newMessages;
      });
      
      Alert.alert('오류', '음성을 전송할 수 없습니다. 다시 시도해주세요.');
      setChatState(STATES.IDLE);
      setEmotion('neutral');
    }
  };

  // ============================================================
  // Polling 처리
  // ============================================================
  const pollForResult = async (taskId) => {
    polling.startPolling(
      taskId,
      // 성공 콜백
      async (result) => {
        const { user_text, reply, sentiment } = result;
        
        // 사용자 메시지 업데이트
        setMessages(prev => {
          const newMessages = [...prev];
          const lastUserIndex = newMessages.findIndex(
            msg => msg.content === '[음성 인식 중...]'
          );
          if (lastUserIndex !== -1) {
            newMessages[lastUserIndex].content = user_text || '[인식 실패]';
          }
          return newMessages;
        });
        
        // AI 응답 추가
        addMessage('assistant', reply);
        
        // 감정 설정
        setEmotion(sentiment || 'neutral');
        
        // 서버에 대화 저장
        try {
          await api.post('/chat/messages/save-ai-response', {
            session_id: sessionId,
            user_text: user_text || '',
            ai_reply: reply,
          });
        } catch (e) {
          console.warn('대화 저장 실패:', e);
        }
        
        // TTS 재생
        setChatState(STATES.SPEAKING);
        await speak(reply);
        
        setChatState(STATES.IDLE);
        setEmotion('neutral');
      },
      // 실패 콜백
      (error) => {
        console.error('Polling 실패:', error);
        
        setMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          if (newMessages[lastIndex]?.content === '[음성 인식 중...]') {
            newMessages[lastIndex].content = '[처리 실패]';
          }
          return newMessages;
        });
        
        Alert.alert('오류', error || '응답을 받지 못했습니다.');
        setChatState(STATES.IDLE);
        setEmotion('neutral');
      }
    );
  };

  // ============================================================
  // 사진 네비게이션
  // ============================================================
  const handleNextPhoto = () => {
    if (currentPhotoIndex < relatedPhotos.length - 1) {
      setCurrentPhotoIndex((prev) => prev + 1);
      addMessage('assistant', '다른 사진도 있네요! 이건 어떤 사진이에요?');
    }
  };
 
  const handlePrevPhoto = () => {
    if (currentPhotoIndex > 0) {
      setCurrentPhotoIndex((prev) => prev - 1);
    }
  };

  // ============================================================
  // 대화 종료 처리
  // ============================================================
  const handleEndChat = () => {
    if (!canFinish && turnCount < 3) {
      Alert.alert('조금 더 이야기해요', '조금 더 대화한 후에 종료할 수 있어요.');
      return;
    }
    stopSpeaking();
    setShowEndModal(true);
  };
 
  const confirmEndChat = (wantToEnd) => {
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
        // 영상 생성 API 호출
        const response = await api.post('/chat/sessions/end', {
          session_id: sessionId,
          create_video: true,
        });
        
        if (response.video_task_id) {
          setVideoTaskId(response.video_task_id);
          // 영상 생성 Polling (최대 3분)
          await pollForVideo(response.video_task_id);
        } else {
          throw new Error('영상 생성을 시작할 수 없습니다.');
        }
        
      } catch (error) {
        console.error('영상 생성 실패:', error);
        setIsCreatingVideo(false);
        Alert.alert('완료', '대화가 저장되었어요. 영상 생성에 실패했습니다.');
        navigation.navigate('Home');
      }
    } else {
      // 영상 없이 종료
      try {
        await api.post('/chat/sessions/end', {
          session_id: sessionId,
          create_video: false,
        });
      } catch (e) {
        console.warn('세션 종료 실패:', e);
      }
      navigation.navigate('Home');
    }
  };

  const pollForVideo = async (taskId) => {
    const startTime = Date.now();
    const timeout = 180000; // 3분
    
    while (Date.now() - startTime < timeout) {
      try {
        const result = await api.get(`/api/task/${taskId}`);
        
        if (result.status === 'SUCCESS') {
          setIsCreatingVideo(false);
          Alert.alert('완료', '영상이 만들어졌어요! 추억 극장에서 확인해보세요.');
          navigation.navigate('Home');
          return;
        }
        
        if (result.status === 'FAILURE') {
          throw new Error(result.error || '영상 생성 실패');
        }
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
      } catch (error) {
        console.error('영상 Polling 오류:', error);
        setIsCreatingVideo(false);
        Alert.alert('완료', '대화가 저장되었어요. 영상은 나중에 확인해주세요.');
        navigation.navigate('Home');
        return;
      }
    }
    
    // 타임아웃
    setIsCreatingVideo(false);
    Alert.alert('완료', '영상이 만들어지고 있어요. 추억 극장에서 나중에 확인해주세요.');
    navigation.navigate('Home');
  };

  // ============================================================
  // 렌더링 헬퍼
  // ============================================================
  const currentPhoto = relatedPhotos[currentPhotoIndex] || { url: photoUrl };
  
  const getMicButtonText = () => {
    switch (chatState) {
      case STATES.RECORDING:
        return '말하는 중...';
      case STATES.PROCESSING:
        return '듣고 있어요...';
      case STATES.SPEAKING:
        return '복실이가 말해요';
      default:
        return '눌러서 말하기';
    }
  };

  const isMicDisabled = chatState !== STATES.IDLE;
 
  return (
    <View style={styles.container}>
      {/* 상단: 사진 영역 */}
      <View style={styles.photoSection}>
        <Image
          source={{ uri: currentPhoto.url }}
          style={styles.mainPhoto}
          resizeMode="cover"
        />
 
        {/* 사진 넘기기 버튼 */}
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
 
        {/* 사진 인디케이터 */}
        <View style={styles.photoIndicator}>
  {Array.isArray(relatedPhotos) && relatedPhotos.length > 0 ? (
    relatedPhotos.map((_, index) => (
      <View
        key={index}
        style={[
          styles.indicatorDot,
          index === currentPhotoIndex && styles.indicatorDotActive,
        ]}
      />
    ))
  ) : (
    <View style={styles.indicatorDotActive} /> // 사진이 없을 때 기본 점 하나
  )}
</View>
      </View>
 
      {/* 대화 내역 */}
      <ScrollView 
        ref={scrollViewRef}
        style={styles.chatArea} 
        contentContainerStyle={styles.chatContent}
      >
        {messages.map((msg, index) => (
          <View
            key={index}
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
        {chatState === STATES.PROCESSING && (
          <View style={styles.animationContainer}>
            <DogAnimation 
              emotion={emotion} 
              isAnimating={true}
              customMessage="복실이가 생각하고 있어요..."
            />
          </View>
        )}
      </ScrollView>
 
      {/* 하단 컨트롤 영역 */}
      <View style={styles.controlArea}>
        <TouchableOpacity
          style={[
            styles.micButton, 
            chatState === STATES.RECORDING && styles.micButtonActive,
            isMicDisabled && chatState !== STATES.RECORDING && styles.micButtonDisabled,
          ]}
          onPressIn={handleRecordStart}
          onPressOut={handleRecordEnd}
          disabled={isMicDisabled}
        >
          <Text style={styles.micIcon}>
            {chatState === STATES.SPEAKING ? '🐕' : '🎤'}
          </Text>
          <Text style={styles.micButtonText}>
            {getMicButtonText()}
          </Text>
        </TouchableOpacity>
 
        {(canFinish || turnCount >= 3) && (
          <TouchableOpacity 
            style={[
              styles.endButton,
              isMicDisabled && styles.endButtonDisabled,
            ]} 
            onPress={handleEndChat}
            disabled={isMicDisabled}
          >
            <Text style={styles.endButtonText}>대화 종료</Text>
          </TouchableOpacity>
        )}
      </View>
 
      {/* 대화 종료 확인 모달 */}
      <Modal visible={showEndModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>대화를 종료하시겠습니까?</Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonNo]}
                onPress={() => confirmEndChat(false)}
              >
                <Text style={styles.modalButtonText}>아니요</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonYes]}
                onPress={() => confirmEndChat(true)}
              >
                <Text style={styles.modalButtonText}>예</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
 
      {/* 영상 제작 확인 모달 */}
      <Modal visible={showVideoModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>영상을 제작하시겠습니까?</Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonNo]}
                onPress={() => confirmCreateVideo(false)}
              >
                <Text style={styles.modalButtonText}>아니요</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonYes]}
                onPress={() => confirmCreateVideo(true)}
              >
                <Text style={styles.modalButtonText}>예</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
 
      {/* 영상 제작 중 로딩 모달 */}
      <Modal visible={isCreatingVideo} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.loadingContent}>
            <ActivityIndicator size="large" color="#FFD700" />
            <Text style={styles.loadingText}>영상 제작 중...</Text>
            <Text style={styles.loadingSubText}>잠시만 기다려주세요</Text>
          </View>
        </View>
      </Modal>
    </View>
  );
};
 
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  photoSection: {
    width: '100%',
    height: width * 0.7,
    backgroundColor: '#E0E0E0',
    position: 'relative',
  },
  mainPhoto: {
    width: '100%',
    height: '100%',
  },
  navButton: {
    position: 'absolute',
    top: '50%',
    marginTop: -25,
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  prevButton: {
    left: 10,
  },
  nextButton: {
    right: 10,
  },
  navButtonText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  photoIndicator: {
    position: 'absolute',
    bottom: 15,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  indicatorDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  indicatorDotActive: {
    backgroundColor: colors.primary,
  },
  photoSection: {
    width: '100%',
    height: width * 0.7,
    backgroundColor: '#E0E0E0',
    position: 'relative',
  },
  mainPhoto: {
    width: '100%',
    height: '100%',
  },
  navButton: {
    position: 'absolute',
    top: '50%',
    marginTop: -25,
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  prevButton: {
    left: 10,
  },
  nextButton: {
    right: 10,
  },
  navButtonText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  photoIndicator: {
    position: 'absolute',
    bottom: 15,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  indicatorDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  indicatorDotActive: {
    backgroundColor: '#FFD700',
  },
  chatArea: {
    flex: 1,
  },
  chatContent: {
    padding: 15,
    paddingBottom: 20,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 15,
    borderRadius: 15,
    marginVertical: 6,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: colors.primary,
  },
  assistantBubble: {
    alignSelf: 'flex-start',

    backgroundColor: colors.white,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  senderName: {
    fontSize: fonts.sizes.small,
    fontFamily: fonts.regular,
    color: colors.textLight,
    marginBottom: 5,
  },
  messageText: {
    fontSize: fonts.sizes.large,
    fontFamily: fonts.regular,
    color: colors.text,
    lineHeight: fonts.lineHeights.large,
  },
  controlArea: {
    padding: 15,
    alignItems: 'center',
  },
  micButton: {
    width: 150,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FFD700',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 6,
  },
  micButtonActive: {
    backgroundColor: '#FF6347',
  },
  micButtonDisabled: {
    backgroundColor: '#CCCCCC',
    opacity: 0.7,
  },
  micIcon: {
    fontSize: 28,
  },
  micButtonText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 4,
  },
  endButton: {
    marginTop: 15,
    backgroundColor: '#32CD32',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 12,
  },
  endButtonDisabled: {
    backgroundColor: '#CCCCCC',
    opacity: 0.7,
  },
  endButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 30,
    width: '80%',
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 25,
    textAlign: 'center',
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 15,
  },
  modalButton: {
    paddingVertical: 15,
    paddingHorizontal: 35,
    borderRadius: 12,
  },
  modalButtonNo: {
    backgroundColor: '#E0E0E0',
  },
  modalButtonYes: {
    backgroundColor: '#FFD700',
  },
  modalButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  loadingContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 40,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 20,
  },
  loadingSubText: {
    fontSize: 16,
    color: '#888',
    marginTop: 10,
  },
  animationContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
});
 
export default ChatScreen;