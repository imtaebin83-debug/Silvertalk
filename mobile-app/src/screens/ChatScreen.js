/**
 * 대화 화면 (무전기 방식)
 * 큰 마이크 버튼 + 강아지 애니메이션
 */
import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity,
  Image,
  ScrollView,
  Alert 
} from 'react-native';
import { Audio } from 'expo-av';

const ChatScreen = ({ route, navigation }) => {
  const { photoId } = route.params;
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState(null);
  const [turnCount, setTurnCount] = useState(0);

  useEffect(() => {
    // 대화 세션 시작
    startChatSession();
  }, []);

  const startChatSession = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.post('http://localhost:8000/chat/sessions', {
      //   kakao_id: 'test',
      //   photo_id: photoId
      // });
      // setSessionId(response.data.id);
      
      // 임시 세션 ID
      setSessionId('temp-session-id');
      
      // 강아지의 첫 질문
      addMessage('assistant', '우와, 할머니 여기 어디세요? 정말 멋진 곳이네요!');
    } catch (error) {
      console.error('세션 시작 실패:', error);
      Alert.alert('오류', '대화를 시작할 수 없습니다.');
    }
  };

  const addMessage = (role, content) => {
    setMessages(prev => [...prev, { role, content }]);
    if (role === 'user') {
      setTurnCount(prev => prev + 1);
    }
  };

  const startRecording = async () => {
    try {
      // 권한 요청
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
      
      // 사용자 메시지 추가
      addMessage('user', '[음성 메시지]');
      
      // API 전송 (추후 구현)
      // const formData = new FormData();
      // formData.append('audio_file', { uri, type: 'audio/x-m4a', name: 'recording.m4a' });
      // formData.append('session_id', sessionId);
      // const response = await axios.post('http://localhost:8000/chat/messages/voice', formData);
      
      // 임시 응답
      setTimeout(() => {
        addMessage('assistant', '아~ 정말 좋은 추억이네요! 더 들려주세요~');
      }, 2000);
      
      setRecording(null);
    } catch (error) {
      console.error('녹음 중지 실패:', error);
      Alert.alert('오류', '녹음을 처리할 수 없습니다.');
    }
  };

  const finishChat = () => {
    if (turnCount < 3) {
      Alert.alert('조금 더 이야기해요', '조금 더 대화한 후에 종료할 수 있어요.');
      return;
    }

    Alert.alert(
      '대화를 종료할까요?',
      '우리 이야기로 추억 영상을 만들까요?',
      [
        { text: '아니요', style: 'cancel' },
        { 
          text: '네, 만들어주세요!', 
          onPress: () => {
            // 영상 생성 요청
            navigation.navigate('Home');
            Alert.alert('영상 제작 중', '영상이 완성되면 알려드릴게요!');
          }
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      {/* 대화 내역 */}
      <ScrollView style={styles.chatArea}>
        {messages.map((msg, index) => (
          <View 
            key={index} 
            style={[
              styles.messageBubble,
              msg.role === 'user' ? styles.userBubble : styles.assistantBubble
            ]}
          >
            <Text style={styles.messageText}>{msg.content}</Text>
          </View>
        ))}
      </ScrollView>

      {/* 마이크 버튼 (큼직하게) */}
      <View style={styles.controlArea}>
        <TouchableOpacity
          style={[styles.micButton, isRecording && styles.micButtonActive]}
          onPressIn={startRecording}
          onPressOut={stopRecording}
        >
          <Text style={styles.micButtonText}>
            {isRecording ? '말하는 중...' : '눌러서 말하기'}
          </Text>
        </TouchableOpacity>

        {turnCount >= 3 && (
          <TouchableOpacity
            style={styles.finishButton}
            onPress={finishChat}
          >
            <Text style={styles.finishButtonText}>대화 종료</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8DC',
  },
  chatArea: {
    flex: 1,
    padding: 15,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 15,
    borderRadius: 15,
    marginVertical: 5,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#FFD700',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFF',
  },
  messageText: {
    fontSize: 20,
    color: '#333',
  },
  controlArea: {
    padding: 20,
    alignItems: 'center',
  },
  micButton: {
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: '#FFD700',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
    elevation: 8,
  },
  micButtonActive: {
    backgroundColor: '#FF6347',
  },
  micButtonText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  finishButton: {
    marginTop: 20,
    backgroundColor: '#32CD32',
    paddingVertical: 15,
    paddingHorizontal: 40,
    borderRadius: 15,
  },
  finishButtonText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
});

export default ChatScreen;
