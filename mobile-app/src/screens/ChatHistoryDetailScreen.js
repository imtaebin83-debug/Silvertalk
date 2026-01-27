/**
 * 대화 기록 상세 화면
 * 설계도 5번: 대표 사진 크게 표시, 질문 띄움, 대화 기록 스크롤 가능
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Dimensions,
} from 'react-native';

const { width } = Dimensions.get('window');

const ChatHistoryDetailScreen = ({ route, navigation }) => {
  const { historyId, history } = route.params;
  const [chatMessages, setChatMessages] = useState([]);
  const [questionPrompt, setQuestionPrompt] = useState('');

  useEffect(() => {
    fetchChatDetail();
  }, []);

  const fetchChatDetail = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.get(`http://localhost:8000/chat/histories/${historyId}`);
      // setChatMessages(response.data.messages);
      // setQuestionPrompt(response.data.question);

      // 임시 데이터
      setQuestionPrompt('할머니, 이 사진을 보니 어떤 생각이 나세요?');
      setChatMessages([
        { role: 'assistant', content: '우와! 할머니, 이 사진은 어디서 찍은 거예요?' },
        { role: 'user', content: '아, 이거 제주도 가서 찍은 거야. 작년에 가족들이랑 갔었어.' },
        { role: 'assistant', content: '제주도요! 가족들이랑 같이 가셨군요! 재밌으셨어요?' },
        { role: 'user', content: '응, 정말 좋았어. 손자도 같이 갔는데 바다 보고 좋아하더라고.' },
        { role: 'assistant', content: '손자분이랑 바다를 보셨군요! 어떤 바다였어요? 모래사장도 있었어요?' },
        { role: 'user', content: '응, 협재 해수욕장이었어. 물이 맑고 예뻤어.' },
      ]);
    } catch (error) {
      console.error('대화 상세 불러오기 실패:', error);
    }
  };

  const renderMessage = (message, index) => {
    const isUser = message.role === 'user';
    return (
      <View
        key={index}
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        {!isUser && <Text style={styles.senderName}>복실이</Text>}
        <Text style={styles.messageText}>{message.content}</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* 상단 고정: 대표 사진 */}
      <View style={styles.photoSection}>
        <Image
          source={{ uri: history?.photo_url || 'https://via.placeholder.com/400' }}
          style={styles.mainPhoto}
          resizeMode="cover"
        />
      </View>

      {/* 질문 프롬프트 */}
      <View style={styles.questionSection}>
        <Text style={styles.questionText}>{questionPrompt}</Text>
      </View>

      {/* 대화 기록 스크롤 영역 */}
      <ScrollView
        style={styles.chatSection}
        contentContainerStyle={styles.chatContent}
        showsVerticalScrollIndicator={false}
      >
        {chatMessages.map((message, index) => renderMessage(message, index))}
      </ScrollView>
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
    height: width * 0.65,
    backgroundColor: '#E0E0E0',
  },
  mainPhoto: {
    width: '100%',
    height: '100%',
  },
  questionSection: {
    backgroundColor: '#FFD700',
    paddingVertical: 15,
    paddingHorizontal: 20,
  },
  questionText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  chatSection: {
    flex: 1,
  },
  chatContent: {
    padding: 15,
    paddingBottom: 30,
  },
  messageBubble: {
    maxWidth: '85%',
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
});

export default ChatHistoryDetailScreen;
