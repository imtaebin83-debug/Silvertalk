/**
 * 대화 화면
 * 설계도 7-8번: 대표 사진 크게 표시, 연관 사진으로 넘기기, 3턴 후 종료 가능
 */
import React, { useState, useEffect } from 'react';
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
import { Audio } from 'expo-av';
 
const { width } = Dimensions.get('window');
 
const ChatScreen = ({ route, navigation }) => {
  const { photoId, photoUrl, photoDate } = route.params;
 
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState(null);
  const [turnCount, setTurnCount] = useState(0);
 
 // 연관 사진들 (비슷한 날짜의 사진 4장)
  const [relatedPhotos, setRelatedPhotos] = useState([]);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
 
  // 팝업 및 로딩 상태
  const [showEndModal, setShowEndModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);
 
  useEffect(() => {
    startChatSession();
    fetchRelatedPhotos();
  }, []);
 
  const startChatSession = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.post('http://localhost:8000/chat/sessions', {
      //   kakao_id: 'test',
      //   photo_id: photoId
      // });
      // setSessionId(response.data.id);
 
      setSessionId('temp-session-id');
      addMessage('assistant', '우와, 할머니 이 사진 어디서 찍은 거예요? 정말 멋진 곳이네요!');
    } catch (error) {
      console.error('세션 시작 실패:', error);
      Alert.alert('오류', '대화를 시작할 수 없습니다.');
    }
  };
 
  const fetchRelatedPhotos = async () => {
    try {
      // API 호출: 비슷한 날짜의 사진 4장 가져오기 (추후 구현)
      // const response = await axios.get(`http://localhost:8000/photos/related?photo_id=${photoId}`);
      // setRelatedPhotos(response.data);
 
      // 임시 데이터 - 연관 사진 4장
      setRelatedPhotos([
        { id: photoId, url: photoUrl, date: photoDate },
        { id: '2', url: 'https://via.placeholder.com/400', date: photoDate },
        { id: '3', url: 'https://via.placeholder.com/400', date: photoDate },
        { id: '4', url: 'https://via.placeholder.com/400', date: photoDate },
      ]);
    } catch (error) {
      console.error('연관 사진 불러오기 실패:', error);
    }
  };
 
  const addMessage = (role, content) => {
    setMessages((prev) => [...prev, { role, content }]);
    if (role === 'user') {
      setTurnCount((prev) => prev + 1);
    }
  };
 
  const startRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('권한 필요', '마이크 권한이 필요합니다.');
        return;
      }
 
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
 
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
 
      setRecording(recording);
      setIsRecording(true);
    } catch (error) {
      console.error('녹음 시작 실패:', error);
      Alert.alert('오류', '녹음을 시작할 수 없습니다.');
    }
  };
 
  const stopRecording = async () => {
    try {
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
 
      addMessage('user', '[음성 메시지]');
 
      // API 전송 (추후 구현)
      // const formData = new FormData();
      // formData.append('audio_file', { uri, type: 'audio/x-m4a', name: 'recording.m4a' });
      // formData.append('session_id', sessionId);
      // const response = await axios.post('http://localhost:8000/chat/messages/voice', formData);
 
      setTimeout(() => {
        addMessage('assistant', '아~ 정말 좋은 추억이네요! 더 들려주세요~');
      }, 2000);
 
      setRecording(null);
    } catch (error) {
      console.error('녹음 중지 실패:', error);
      Alert.alert('오류', '녹음을 처리할 수 없습니다.');
    }
  };
 
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
 
  const handleEndChat = () => {
    if (turnCount < 3) {
      Alert.alert('조금 더 이야기해요', '조금 더 대화한 후에 종료할 수 있어요.');
      return;
    }
    setShowEndModal(true);
  };
 
  const confirmEndChat = (wantToEnd) => {
    setShowEndModal(false);
    if (wantToEnd) {
      setShowVideoModal(true);
    }
  };
 
  const confirmCreateVideo = (wantToCreate) => {
    setShowVideoModal(false);
    if (wantToCreate) {
      setIsCreatingVideo(true);
      // 영상 생성 API 호출 (추후 구현)
      setTimeout(() => {
        setIsCreatingVideo(false);
        Alert.alert('완료', '영상이 만들어졌어요! 추억 극장에서 확인해보세요.');
        navigation.navigate('Home');
      }, 3000);
    } else {
      navigation.navigate('Home');
    }
  };
 
  const currentPhoto = relatedPhotos[currentPhotoIndex] || { url: photoUrl };
 
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
 
      {/* 대화 내역 */}
      <ScrollView style={styles.chatArea} contentContainerStyle={styles.chatContent}>
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
      </ScrollView>
 
      {/* 하단 컨트롤 영역 */}
      <View style={styles.controlArea}>
        <TouchableOpacity
          style={[styles.micButton, isRecording && styles.micButtonActive]}
          onPressIn={startRecording}
          onPressOut={stopRecording}
        >
          <Text style={styles.micIcon}>🎤</Text>
          <Text style={styles.micButtonText}>
            {isRecording ? '말하는 중...' : '눌러서 말하기'}
          </Text>
        </TouchableOpacity>
 
        {turnCount >= 3 && (
          <TouchableOpacity style={styles.endButton} onPress={handleEndChat}>
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
    backgroundColor: '#FFF8DC',
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
    backgroundColor: '#FFD700',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  senderName: {
    fontSize: 12,
    color: '#888',
    marginBottom: 5,
  },
  messageText: {
    fontSize: 18,
   color: '#333',
    lineHeight: 26,
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
});
 
export default ChatScreen;