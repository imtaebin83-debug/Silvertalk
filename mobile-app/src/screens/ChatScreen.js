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
import { useKeepAwake } from 'expo-keep-awake';
import { colors, fonts } from '../theme';
import api from '../api/config';
import useVoiceRecording from '../hooks/useVoiceRecording';
import useChatSession, { CHAT_STATES } from '../hooks/useChatSession';
import DogAnimation from '../components/DogAnimation';

const { width, height } = Dimensions.get('window');

// 복실이 이미지
const DOG_IMAGE = require('../../assets/dog_nukki.png');

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

  const scrollViewRef = useRef(null);

  // 초기 인사
  useEffect(() => {
    const greeting = '우와, 할머니 이 사진 어디서 찍은 거예요? 정말 멋진 곳이네요!';
    setLocalMessages([{ role: 'assistant', content: greeting, timestamp: new Date() }]);

    return () => chatSession.stopSpeaking();
  }, [initialSessionId]);

  // 새 메시지 시 자동 스크롤
  useEffect(() => {
    if (scrollViewRef.current) {
      scrollViewRef.current.scrollToEnd({ animated: true });
    }
  }, [localMessages, chatSession.messages]);

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
        // 세션 종료 + 영상 생성 요청
        const result = await chatSession.endSession(true);

        // [수정] video_task_id가 아닌 video_id를 사용하여 상태 조회 진행
        if (result.success && result.video_id) {
          await pollForVideo(result.video_id);
        } else {
          throw new Error('영상 생성 요청 실패');
        }
      } catch (error) {
        console.error('영상 생성 실패:', error);
        setIsCreatingVideo(false);
        Alert.alert(
          '알림',
          '대화가 저장되었어요. 영상 생성은 나중에 시도해주세요.',
          [{ text: '확인', onPress: () => navigation.navigate('Home') }]
        );
      }
    } else {
      try {
        await chatSession.endSession(false);
        Alert.alert(
          '저장 완료',
          '대화가 기록되었어요.',
          [{ text: '확인', onPress: () => navigation.navigate('Home') }]
        );
      } catch (error) {
        console.error('세션 종료 실패:', error);
        navigation.navigate('Home');
      }
    }
  };

  // [수정] 비디오 ID를 기반으로 폴링 수행
  const pollForVideo = async (videoId) => {
    const startTime = Date.now();
    const timeout = 180000; // 3분

    while (Date.now() - startTime < timeout) {
      try {
        // [수정] 경로를 /videos/{video_id}/status 로 정확히 요청
        const result = await api.get(`/videos/${videoId}/status`);

        // [수정] 백엔드 VideoStatus enum과 일치하는지 확인 (SUCCESS 또는 COMPLETED)
        if (result.status === 'SUCCESS' || result.status === 'COMPLETED') {
          setIsCreatingVideo(false);
          Alert.alert(
            '완료',
            '추억 영상이 만들어졌어요! 추억 극장에서 확인해보세요.',
            [{ text: '확인', onPress: () => navigation.navigate('Home') }]
          );
          return;
        }

        if (result.status === 'FAILURE' || result.status === 'FAILED') {
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
          {[...localMessages, ...chatSession.messages].map((msg, index) => (
            <View key={index} style={styles.messageRow}>
              {msg.role === 'assistant' ? (
                <View style={styles.assistantMessageContainer}>
                  <Image source={DOG_IMAGE} style={styles.dogImage} />
                  <View style={styles.assistantBubbleContainer}>
                    <Text style={styles.senderName}>복실이</Text>
                    <View style={styles.assistantBubble}>
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
          ))}
          {(chatSession.chatState === CHAT_STATES.POLLING || chatSession.chatState === CHAT_STATES.UPLOADING) && (
            <View style={styles.animationContainer}>
              <DogAnimation emotion={chatSession.emotion} isAnimating={true} customMessage="복실이가 생각하고 있어요..." />
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
  assistantBubble: {
    backgroundColor: colors.white,
    padding: 15,
    borderRadius: 18,
    borderTopLeftRadius: 4,
    elevation: 2
  },
  messageText: { fontSize: 18, color: colors.text, lineHeight: 26 },

  // 사용자 메시지
  userMessageContainer: { flexDirection: 'row', justifyContent: 'flex-end' },
  userBubble: {
    maxWidth: '75%',
    backgroundColor: colors.primary,
    padding: 15,
    borderRadius: 18,
    borderTopRightRadius: 4
  },
  userMessageText: { fontSize: 18, color: colors.white, lineHeight: 26 },

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
});

export default ChatScreen;
