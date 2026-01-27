/**
 * 대화 화면
 * 설계도 7-8번: 대표 사진 크게 표시, 연관 사진으로 넘기기, 3턴 후 종료 가능
 * 
 * 리팩토링:
 * - useChatSession: 세션 생명주기, API 통신, TTS 통합 관리
 * - useVoiceRecording: .m4a 포맷 녹음
 * - expo-keep-awake: 화면 꺼짐 방지
 * - BackHandler: 안드로이드 뒤로가기 처리
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
  BackHandler,
} from 'react-native';
import { useKeepAwake } from 'expo-keep-awake';
import { useFocusEffect } from '@react-navigation/native';
import { colors, fonts } from '../theme';
import api from '../api/config';
import useVoiceRecording from '../hooks/useVoiceRecording';
import useChatSession, { CHAT_STATES } from '../hooks/useChatSession';
import DogAnimation from '../components/DogAnimation';

const { width } = Dimensions.get('window');
 
const ChatScreen = ({ route, navigation }) => {
  const { photoId, photoUrl, photoDate } = route.params;
 
  // 화면 꺼짐 방지
  useKeepAwake();
 
  // === Custom Hooks ===
  const voiceRecording = useVoiceRecording();
  const chatSession = useChatSession({
    onError: (error) => {
      console.error('Chat Session Error:', error);
    },
  });

  // === 연관 사진 네비게이션 ===
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
 
  // === 모달 상태 ===
  const [showEndModal, setShowEndModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);
  const [videoTaskId, setVideoTaskId] = useState(null);
  
  // === Refs ===
  const scrollViewRef = useRef(null);

  // ============================================================
  // 초기화
  // ============================================================
  useEffect(() => {
    // 세션 시작
    const initSession = async () => {
      await chatSession.startSession(photoId);
    };
    
    initSession();
    
    // 클린업: 언마운트 시 TTS 중지
    return () => {
      chatSession.stopSpeaking();
    };
  }, [photoId]);

  // 새 메시지 시 스크롤
  useEffect(() => {
    if (scrollViewRef.current && chatSession.messages.length > 0) {
      scrollViewRef.current.scrollToEnd({ animated: true });
    }
  }, [chatSession.messages]);

  // 뒤로가기 버튼 방지
  useFocusEffect(
    React.useCallback(() => {
      const onBackPress = () => {
        // 3가지 옵션 Alert 표시
        Alert.alert(
          '대화를 종료할까요?',
          '지금 종료하면 영상 생성을 시작할 수 있어요.',
          [
            {
              text: '취소',
              style: 'cancel',
              onPress: () => {},
            },
            {
              text: '영상 만들기',
              onPress: () => {
                handleEndChat();
              },
            },
            {
              text: '그냥 나가기',
              onPress: () => {
                chatSession.stopSpeaking();
                navigation.navigate('Home');
              },
            },
          ],
          { cancelable: true }
        );
        return true; // 기본 동작 방지
      };

      BackHandler.addEventListener('hardwareBackPress', onBackPress);

      return () => BackHandler.removeEventListener('hardwareBackPress', onBackPress);
    }, [navigation, chatSession.sessionId, chatSession.canFinish, chatSession.turnCount])
  );

  // ============================================================
  // 녹음 처리 (PTT - Push To Talk)
  // ============================================================
  const handleRecordStart = async () => {
    // IDLE 상태에서만 녹음 시작 가능
    if (chatSession.chatState !== CHAT_STATES.IDLE) {
      return;
    }
    
    const success = await voiceRecording.startRecording();
    if (success) {
      // 녹음 시작 성공 시 chatSession에 알림 (상태 관리는 useChatSession이 담당)
      console.log('녹음 시작');
    }
  };

  const handleRecordEnd = async () => {
    if (!voiceRecording.isRecording) {
      return;
    }
    
    const audioUri = await voiceRecording.stopRecording();
    if (!audioUri) {
      Alert.alert('오류', '녹음 파일을 저장할 수 없습니다.');
      return;
    }
    
    // 음성 메시지 전송
    await chatSession.sendVoiceMessage(audioUri);
  };

  // ============================================================
  // 사진 네비게이션
  // ============================================================
  const handleNextPhoto = () => {
    if (currentPhotoIndex < chatSession.relatedPhotos.length - 1) {
      setCurrentPhotoIndex((prev) => prev + 1);
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
    if (!chatSession.canFinish && chatSession.turnCount < 3) {
      Alert.alert('조금 더 이야기해요', '조금 더 대화한 후에 종료할 수 있어요.');
      return;
    }
    chatSession.stopSpeaking();
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
        // 세션 종료 및 영상 생성 시작
        const result = await chatSession.endSession(true);
        
        if (result.success && result.videoTaskId) {
          setVideoTaskId(result.videoTaskId);
          // 영상 생성 Polling (최대 3분)
          await pollForVideo(result.videoTaskId);
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
      await chatSession.endSession(false);
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
  const displayPhotos = chatSession.relatedPhotos.length > 0 
    ? chatSession.relatedPhotos 
    : [{ id: photoId, url: photoUrl, date: photoDate }];
  
  const currentPhoto = displayPhotos[currentPhotoIndex] || { url: photoUrl };
  
  const getMicButtonText = () => {
    switch (chatSession.chatState) {
      case CHAT_STATES.RECORDING:
        return '말하는 중...';
      case CHAT_STATES.UPLOADING:
        return '전송 중...';
      case CHAT_STATES.POLLING:
        return '듣고 있어요...';
      case CHAT_STATES.SPEAKING:
        return '복실이가 말해요';
      default:
        return '눌러서 말하기';
    }
  };

  const isMicDisabled = 
    chatSession.chatState !== CHAT_STATES.IDLE || 
    voiceRecording.isRecording;
 
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
        {currentPhotoIndex < displayPhotos.length - 1 && (
          <TouchableOpacity
            style={[styles.navButton, styles.nextButton]}
            onPress={handleNextPhoto}
          >
            <Text style={styles.navButtonText}>{'>'}</Text>
          </TouchableOpacity>
        )}
 
        {/* 사진 인디케이터 */}
        {displayPhotos.length > 1 && (
          <View style={styles.photoIndicator}>
            {displayPhotos.map((_, index) => (
              <View
                key={index}
                style={[
                  styles.indicatorDot,
                  index === currentPhotoIndex && styles.indicatorDotActive,
                ]}
              />
            ))}
          </View>
        )}
      </View>
 
      {/* 대화 내역 */}
      <ScrollView 
        ref={scrollViewRef}
        style={styles.chatArea} 
        contentContainerStyle={styles.chatContent}
      >
        {chatSession.messages.map((msg, index) => (
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
        {(chatSession.chatState === CHAT_STATES.POLLING || 
          chatSession.chatState === CHAT_STATES.UPLOADING) && (
          <View style={styles.animationContainer}>
            <DogAnimation 
              emotion={chatSession.emotion} 
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
            voiceRecording.isRecording && styles.micButtonActive,
            isMicDisabled && !voiceRecording.isRecording && styles.micButtonDisabled,
          ]}
          onPressIn={handleRecordStart}
          onPressOut={handleRecordEnd}
          disabled={isMicDisabled}
        >
          <Text style={styles.micIcon}>
            {chatSession.chatState === CHAT_STATES.SPEAKING ? '🐕' : '🎤'}
          </Text>
          <Text style={styles.micButtonText}>
            {getMicButtonText()}
          </Text>
        </TouchableOpacity>
 
        {(chatSession.canFinish || chatSession.turnCount >= 3) && (
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