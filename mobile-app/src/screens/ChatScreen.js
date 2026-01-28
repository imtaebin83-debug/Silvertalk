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
  Animated,
} from 'react-native';
import { useKeepAwake } from 'expo-keep-awake';
import { colors, fonts, commonStyles, sentimentEmoji } from '../theme';
import api from '../api/config';
import useVoiceRecording from '../hooks/useVoiceRecording';
import useChatSession, { CHAT_STATES } from '../hooks/useChatSession';
import DogAnimation from '../components/DogAnimation';

const { width, height } = Dimensions.get('window');

// 복실이 이미지
const DOG_IMAGE = require('../../assets/dog_nukki.png');
const SAD_DOG_IMAGE = require('../../assets/dog_nukki.png'); // TODO: 슬픈 강아지 이미지

const ChatScreen = ({ route, navigation }) => {
  useKeepAwake(); // 화면 꺼짐 방지

  const {
    sessionId: initialSessionId,
    photoUrl,
    photoDate,
    allPhotoUrls = [],
    mainPhotoIndex = 0
  } = route.params;

  // === 훅 초기화 ===
  const chatSession = useChatSession({ initialSessionId });
  const voiceRecording = useVoiceRecording();

  // === 상태 관리 ===
  const [localMessages, setLocalMessages] = useState([]);
  const [relatedPhotos, setRelatedPhotos] = useState(
    allPhotoUrls.map((url, idx) => ({ url, order: idx }))
  );
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [currentPhotoTurnCount, setCurrentPhotoTurnCount] = useState(0);

  // 모달 상태
  const [showEndModal, setShowEndModal] = useState(false);
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);

  // 커스텀 토스트 상태
  const [toastMessage, setToastMessage] = useState('');
  const [showToast, setShowToast] = useState(false);

  // Breathing 애니메이션 (어르신 친화적 피드백)
  const breathingAnim = useRef(new Animated.Value(0.6)).current;

  const scrollViewRef = useRef(null);

  // 초기 인사 및 세션 시작
  useEffect(() => {
    const startSessionAndGreet = async () => {
      try {
        console.log('🚀 세션 시작 시도...');
        console.log('   - initialSessionId:', initialSessionId);

        // 세션 시작 API 호출
        const response = await api.post('/chat/sessions', {
          kakao_id: 'test_user', // 실제로는 로그인 정보에서 가져와야 함
          photo_id: initialSessionId // photo_id로 사용
        });

        console.log('📥 세션 생성 응답:', JSON.stringify(response, null, 2));

        // ai_reply 검증
        const aiReply = response.ai_reply || response.greeting;
        if (!aiReply) {
          console.error('❌ ai_reply가 응답에 없습니다:', response);
          throw new Error('서버 응답에 ai_reply가 없습니다.');
        }

        // 세션 ID 설정
        if (response.session_id) {
          chatSession.setSession(response.session_id);
        }

        console.log('📋 세션 생성 응답:', response);

        // greeting_task_id가 있으면 polling으로 첫 인사 받기
        if (response.greeting_task_id) {
          console.log('🔄 첫 인사 polling 시작:', response.greeting_task_id);

          const greetingResult = await pollForGreeting(response.greeting_task_id);

          if (greetingResult.success && greetingResult.ai_reply) {
            const greetingMessage = {
              role: 'assistant',
              content: greetingResult.ai_reply,
              timestamp: new Date()
            };
            setLocalMessages([greetingMessage]);

            // TTS로 첫 인사 재생
            if (chatSession.speakText) {
              await chatSession.speakText(greetingResult.ai_reply);
            }
          } else {
            // Polling 실패 시 fallback
            throw new Error('첫 인사 생성 실패');
          }
        } else if (response.ai_reply) {
          // 즉시 반환된 ai_reply 사용 (사진 없는 경우)
          const greetingMessage = {
            role: 'assistant',
            content: response.ai_reply,
            timestamp: new Date()
          };
          setLocalMessages([greetingMessage]);

          if (chatSession.speakText) {
            await chatSession.speakText(response.ai_reply);
          }
        } else {
          // Fallback
          throw new Error('인사 메시지 없음');
        }

        // 연관 사진 업데이트
        if (response.related_photos) {
          setRelatedPhotos(response.related_photos.map((photo, idx) => ({
            ...photo,
            order: idx
          })));
        }

      } catch (error) {
        console.error('❌ 세션 시작 실패:', error);
        // Fallback 메시지
        const fallbackMessage = {
          role: 'assistant',
          content: '안녕하세요! 저는 복실이에요. 오늘 기분이 어떠세요? 멍!',
          timestamp: new Date()
        };
        setLocalMessages([fallbackMessage]);
        if (chatSession.speakText) {
          await chatSession.speakText(fallbackMessage.content);
        }
      }
    };

    // Polling 함수 (greeting 전용)
    const pollForGreeting = async (taskId) => {
      const startTime = Date.now();
      const timeout = 30000; // 30초 타임아웃
      const interval = 1000; // 1초 간격

      while (Date.now() - startTime < timeout) {
        try {
          const result = await api.get(`/api/task/${taskId}`);
          console.log('🐕 Greeting poll result:', result);

          // 대소문자 구분 없이 체크
          const statusLower = result.status?.toLowerCase();

          if (statusLower === 'success') {
            // GreetingTaskResult 스키마: ai_greeting 필드 사용 (ai_reply fallback)
            const greeting = result.ai_greeting || result.ai_reply;
            return {
              success: true,
              ai_reply: greeting,
              analysis: result.analysis
            };
          }

          if (statusLower === 'failure' || statusLower === 'error') {
            return { success: false, error: result.message };
          }

          // 대기
          await new Promise(resolve => setTimeout(resolve, interval));
        } catch (error) {
          console.error('Greeting poll error:', error);
          return { success: false, error: error.message };
        }
      }

      return { success: false, error: 'timeout' };
    };

    if (initialSessionId) {
      startSessionAndGreet();
    }

    return () => chatSession.stopSpeaking();
  }, [initialSessionId]);

  // 새 메시지 시 자동 스크롤
  useEffect(() => {
    if (scrollViewRef.current) {
      scrollViewRef.current.scrollToEnd({ animated: true });
    }
  }, [localMessages, chatSession.messages]);

  // Breathing 애니메이션 (로딩 시 강아지 아바타)
  useEffect(() => {
    if (chatSession.chatState === CHAT_STATES.POLLING || chatSession.chatState === CHAT_STATES.UPLOADING) {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.timing(breathingAnim, { toValue: 1.0, duration: 800, useNativeDriver: true }),
          Animated.timing(breathingAnim, { toValue: 0.6, duration: 800, useNativeDriver: true }),
        ])
      );
      animation.start();
      return () => animation.stop();
    } else {
      breathingAnim.setValue(1);
    }
  }, [chatSession.chatState]);

  // 커스텀 토스트 표시 함수
  const showCustomToast = (message, duration = 2500) => {
    setToastMessage(message);
    setShowToast(true);
    setTimeout(() => setShowToast(false), duration);
  };

  // 턴 카운트 감지
  useEffect(() => {
    if (chatSession.turnCount > 0) {
      setCurrentPhotoTurnCount(prev => prev + 1);
    }
  }, [chatSession.turnCount]);

  // 녹음 제어
  const handleMicToggle = async () => {
    if (!voiceRecording.isRecording) {
      if (chatSession.chatState !== CHAT_STATES.IDLE) return;
      const success = await voiceRecording.startRecording();
      if (success) chatSession.setRecordingState(true);
    } else {
      const audioUri = await voiceRecording.stopRecording();
      chatSession.setRecordingState(false);
      if (audioUri) await chatSession.sendVoiceMessage(audioUri);
    }
  };

  const handleNextPhoto = () => {
    if (currentPhotoIndex < relatedPhotos.length - 1) {
      setCurrentPhotoIndex((prev) => prev + 1);
      setCurrentPhotoTurnCount(0);
    }
  };

  // 대화 종료 버튼 클릭
  const handleEndChat = () => {
    if (!chatSession.canFinish && chatSession.turnCount < 3) {
      Alert.alert('조금 더 이야기해요', '조금 더 대화한 후에 종료할 수 있어요.');
      return;
    }
    chatSession.stopSpeaking();
    setShowEndModal(true);
  };

  // 1단계: 대화 종료 확인
  const confirmEndChat = (wantToEnd) => {
    setShowEndModal(false);
    if (wantToEnd) {
      // 2단계: 추억 기록 여부 확인
      setShowRecordModal(true);
    }
  };

  // 2단계: 추억 기록 여부 결정
  const confirmRecordMemory = async (wantToRecord) => {
    setShowRecordModal(false);

    if (wantToRecord) {
      setIsCreatingVideo(true);
      try {
        const result = await chatSession.endSession(true);

        // [수정] useChatSession이 준 video_id가 있는지 확인
        if (result && result.video_id) {
          await pollForVideo(result.video_id);
        } else {
          // 이 에러가 났던 이유는 result.video_id가 없었기 때문
          throw new Error('서버로부터 비디오 ID를 받지 못했습니다.');
        }
      } catch (error) {
        console.error('영상 생성 실패:', error);
        setIsCreatingVideo(false);
        Alert.alert('알림', '영상 생성 요청 중 오류가 발생했습니다.');
      }
    }
  };

  const pollForVideo = async (videoId) => {
    const startTime = Date.now();
    const timeout = 180000;

    while (Date.now() - startTime < timeout) {
      try {
        // [중요] 로그에 /api/task가 찍히지 않도록 /videos/{id}/status 경로 사용
        // 백엔드 video.py의 @router.get("/{video_id}/status")와 일치해야 함
        const result = await api.get(`/videos/${videoId}/status`);

        // 대소문자 구분 없이 체크
        const statusLower = result.status?.toLowerCase();

        if (statusLower === 'success' || statusLower === 'completed') {
          setIsCreatingVideo(false);
          Alert.alert('완료', '추억 영상이 만들어졌어요!');
          navigation.navigate('Home');
          return;
        }

        if (statusLower === 'failure' || statusLower === 'failed' || statusLower === 'error') {
          throw new Error('영상 생성 실패');
        }

        await new Promise(resolve => setTimeout(resolve, 3000));
      } catch (error) {
        console.error('폴링 에러:', error);
        break;
      }
    }

    setIsCreatingVideo(false);
    Alert.alert(
      '알림',
      '영상이 만들어지고 있어요. 추억 극장에서 나중에 확인해주세요.',
      [{ text: '확인', onPress: () => navigation.navigate('Home') }]
    );
  };

  const currentPhoto = relatedPhotos[currentPhotoIndex] || { url: photoUrl };
  const isMicDisabled = [CHAT_STATES.UPLOADING, CHAT_STATES.POLLING, CHAT_STATES.SPEAKING].includes(chatSession.chatState);

  return (
    <View style={styles.container}>
      {/* 상단: 사진 영역 (고정) */}
      <View style={styles.photoSection}>
        <Image
          source={{ uri: currentPhoto.url }}
          style={styles.mainPhoto}
          resizeMode="contain"
        />
        <View style={styles.photoIndicator}>
          {relatedPhotos.map((_, index) => (
            <View key={index} style={[styles.indicatorDot, index === currentPhotoIndex && styles.indicatorDotActive]} />
          ))}
        </View>
      </View>

      {/* 하단: 채팅 영역 */}
      <View style={styles.chatSection}>
        <ScrollView
          ref={scrollViewRef}
          style={styles.chatScrollView}
          contentContainerStyle={styles.chatContent}
        >
          {/* 1. 메시지 리스트 렌더링 구역 */}
          {(() => {
            const allMessages = [...localMessages, ...chatSession.messages];
            console.log('현재 메시지 목록:', allMessages);

            return allMessages.map((msg, index) => {
              // 감정 이모지 가져오기 (AI 메시지에만)
              const emoji = msg.sentiment ? (sentimentEmoji[msg.sentiment] || '🐕') : null;

              return (
                <View key={index} style={styles.messageRow}>
                  {msg.role === 'assistant' ? (
                    <View style={styles.assistantMessageContainer}>
                      <Animated.Image
                        source={DOG_IMAGE}
                        style={[
                          styles.dogImage,
                          { opacity: chatSession.chatState === CHAT_STATES.POLLING ? breathingAnim : 1 }
                        ]}
                      />
                      <View style={styles.assistantBubbleContainer}>
                        <Text style={styles.senderName}>복실이</Text>
                        <View style={styles.assistantBubble}>
                          {emoji && <Text style={styles.sentimentEmoji}>{emoji}</Text>}
                          <Text style={styles.messageText}>{msg.content}</Text>
                        </View>
                      </View>
                    </View>
                  ) : (
                    <View style={styles.userMessageContainer}>
                      <View style={styles.userBubble}>
                        <Text style={styles.userMessageText}>{msg.content}</Text>
                      </View>
                    </View>
                  )}
                </View>
              );
            });
          })() /* 👈 이 부분에 '()'와 '}'가 정확히 있어야 함수가 실행됩니다! */}

          {/* 2. 애니메이션 구역 (조건부 렌더링) */}
          {(chatSession.chatState === CHAT_STATES.POLLING || chatSession.chatState === CHAT_STATES.UPLOADING) && (
            <View style={styles.animationContainer}>
              <DogAnimation
                emotion={chatSession.emotion}
                isAnimating={true}
                customMessage="복실이가 생각하고 있어요..."
              />
            </View>
          )}
        </ScrollView>
      </View>

      {/* 컨트롤 영역 */}
      <View style={styles.controlArea}>
        <TouchableOpacity
          style={[styles.micButton, voiceRecording.isRecording && styles.micButtonActive, isMicDisabled && styles.micButtonDisabled]}
          onPress={handleMicToggle}
          disabled={isMicDisabled}
        >
          <Text style={styles.micIcon}>{chatSession.chatState === CHAT_STATES.SPEAKING ? '🐕' : '🎤'}</Text>
          <Text style={styles.micButtonText}>
            {voiceRecording.isRecording ? '듣고 있어요' : isMicDisabled ? '기다려주세요' : '눌러서 말하기'}
          </Text>
        </TouchableOpacity>

        {(currentPhotoTurnCount >= 3 || chatSession.turnCount >= 3) && (
          <View style={styles.navigationButtonsContainer}>
            {currentPhotoIndex < relatedPhotos.length - 1 && (
              <TouchableOpacity style={styles.nextPhotoButton} onPress={handleNextPhoto}>
                <Text style={styles.nextPhotoButtonText}>다음 사진으로 →</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.endButton} onPress={handleEndChat}>
              <Text style={styles.endButtonText}>대화 종료</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* 모달 1: 대화 종료 확인 */}
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

      {/* 모달 2: 추억 기록 여부 */}
      <Modal visible={showRecordModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalEmoji}>📸</Text>
            <Text style={styles.modalTitle}>추억을 기록해 드릴까요?</Text>
            <Text style={styles.modalSubtitle}>
              대화했던 사진들로{'\n'}추억 영상을 만들어 드려요
            </Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonNo]}
                onPress={() => confirmRecordMemory(false)}
              >
                <Text style={styles.modalButtonText}>아니요</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalButtonYes]}
                onPress={() => confirmRecordMemory(true)}
              >
                <Text style={styles.modalButtonText}>예</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* 모달 3: 영상 생성 중 로딩 */}
      <Modal visible={isCreatingVideo} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.loadingContent}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>추억 영상을 만들고 있어요...</Text>
            <Text style={styles.loadingSubText}>잠시만 기다려주세요</Text>
          </View>
        </View>
      </Modal>

      {/* 커스텀 토스트 (어르신 친화적 피드백) */}
      {showToast && (
        <View style={styles.toastContainer}>
          <View style={styles.toast}>
            <Text style={styles.toastText}>{toastMessage}</Text>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },

  // 사진 영역
  photoSection: {
    width: '100%',
    height: height * 0.5,
    backgroundColor: 'transparent',
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 0,
  },
  mainPhoto: {
    width: '100%',
    height: '100%',
  },
  photoIndicator: {
    position: 'absolute',
    bottom: 20,
    flexDirection: 'row',
    gap: 6
  },
  indicatorDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.5)'
  },
  indicatorDotActive: {
    backgroundColor: colors.primary,
    width: 10,
    height: 10,
    borderRadius: 5
  },

  // 채팅 영역
  chatSection: { flex: 1, marginTop: 10 },
  chatScrollView: { flex: 1 },
  chatContent: { padding: 15 },
  messageRow: { marginVertical: 8 },

  // 복실이 메시지
  assistantMessageContainer: { flexDirection: 'row', alignItems: 'flex-start' },
  dogImage: { width: 45, height: 45, borderRadius: 22.5, marginRight: 10 },
  assistantBubbleContainer: { flex: 1, maxWidth: '80%' },
  senderName: { fontSize: 12, color: colors.textLight, marginBottom: 4 },
  // AI 버블
  assistantBubble: {
    maxWidth: '85%',
    backgroundColor: colors.card,
    padding: 16,
    borderRadius: 20,
    borderTopLeftRadius: 4,
    ...commonStyles.shadow,
  },
  sentimentEmoji: {
    fontSize: 28,
    marginBottom: 6,
  },
  messageText: {
    fontSize: fonts.sizes.medium,
    color: colors.text,
    lineHeight: 28,
    fontFamily: fonts.body,
  },

  // 사용자 메시지
  userMessageContainer: { flexDirection: 'row', justifyContent: 'flex-end' },
  userBubble: {
    maxWidth: '75%',
    backgroundColor: colors.primary,
    padding: 16,
    borderRadius: 20,
    borderTopRightRadius: 4
  },
  userMessageText: {
    fontSize: fonts.sizes.medium,
    color: colors.textWhite,
    lineHeight: 28,
    fontFamily: fonts.body,
  },

  animationContainer: { alignItems: 'center', paddingVertical: 10 },

  // 컨트롤 영역
  controlArea: { padding: 20, alignItems: 'center', backgroundColor: colors.background },
  micButton: {
    width: 180,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#FFD700',
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
    elevation: 5
  },
  micButtonActive: { backgroundColor: '#FF6347' },
  micButtonDisabled: { backgroundColor: '#CCC' },
  micIcon: { fontSize: 24 },
  micButtonText: { fontSize: 16, fontWeight: 'bold', color: '#FFF' },

  navigationButtonsContainer: { flexDirection: 'row', marginTop: 15, gap: 10 },
  nextPhotoButton: { backgroundColor: '#4A90D9', padding: 12, borderRadius: 12 },
  nextPhotoButtonText: { color: '#FFF', fontWeight: 'bold' },
  endButton: { backgroundColor: '#32CD32', padding: 12, borderRadius: 12 },
  endButtonText: { color: '#FFF', fontWeight: 'bold' },

  // 모달 스타일
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  modalContent: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    padding: 30,
    width: '85%',
    alignItems: 'center'
  },
  modalEmoji: {
    fontSize: 50,
    marginBottom: 15,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 10,
    textAlign: 'center',
    color: colors.text,
  },
  modalSubtitle: {
    fontSize: 16,
    color: colors.textLight,
    textAlign: 'center',
    marginBottom: 25,
    lineHeight: 24,
  },
  modalButtons: { flexDirection: 'row', gap: 15 },
  modalButton: {
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 12,
    minWidth: 100,
    alignItems: 'center',
  },
  modalButtonNo: { backgroundColor: '#EEE' },
  modalButtonYes: { backgroundColor: '#FFD700' },
  modalButtonText: { fontWeight: 'bold', fontSize: 16 },

  // 로딩 모달
  loadingContent: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    padding: 40,
    alignItems: 'center',
    width: '80%',
  },
  loadingText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 20,
    textAlign: 'center',
  },
  loadingSubText: {
    fontSize: 14,
    color: colors.textLight,
    marginTop: 10,
  },

  // 커스텀 토스트 (어르신 친화적)
  toastContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    pointerEvents: 'none',
  },
  toast: {
    backgroundColor: 'rgba(62, 39, 35, 0.9)',
    paddingVertical: 20,
    paddingHorizontal: 40,
    borderRadius: 16,
    ...commonStyles.shadow,
  },
  toastText: {
    color: colors.textWhite,
    fontSize: fonts.sizes.large,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});

export default ChatScreen;
