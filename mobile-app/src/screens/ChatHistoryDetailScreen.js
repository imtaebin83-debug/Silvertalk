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
  ActivityIndicator,
  Alert,
} from 'react-native';
import { colors, fonts, commonStyles, sentimentEmoji } from '../theme';
import api from '../api/config';

const { width } = Dimensions.get('window');

const ChatHistoryDetailScreen = ({ route, navigation }) => {
  const { sessionId, mainPhotoId, summary, createdAt } = route.params;
  const [chatMessages, setChatMessages] = useState([]);
  const [photoUrl, setPhotoUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChatDetail();
  }, []);

  const fetchChatDetail = async () => {
    try {
      setLoading(true);

      // 1. 대화 로그 조회: GET /chat/sessions/{session_id}
      const logsResponse = await api.get(`/chat/sessions/${sessionId}`);

      if (Array.isArray(logsResponse)) {
        setChatMessages(logsResponse);
        console.log(`✅ 대화 로그 ${logsResponse.length}개 로드 완료`);
      } else {
        setChatMessages([]);
      }

      // 2. 세션 사진 목록 조회 (대표 사진 URL 가져오기)
      try {
        const photosResponse = await api.get(`/chat/sessions/${sessionId}/photos`);
        if (photosResponse.photos && photosResponse.photos.length > 0) {
          // display_order가 1인 메인 사진 또는 첫 번째 사진
          const mainPhoto = photosResponse.photos.find(p => p.display_order === 1) || photosResponse.photos[0];
          setPhotoUrl(mainPhoto.s3_url);
        }
      } catch (photoError) {
        console.warn('사진 로드 실패:', photoError);
      }

    } catch (error) {
      console.error('❌ 대화 상세 불러오기 실패:', error);
      Alert.alert(
        '연결 오류',
        '대화 기록을 불러올 수 없어요.',
        [{ text: '확인', onPress: () => navigation.goBack() }]
      );
    } finally {
      setLoading(false);
    }
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`;
  };

  const renderMessage = (message, index) => {
    const isUser = message.role === 'user';
    const emoji = message.sentiment ? (sentimentEmoji?.[message.sentiment] || '🐕') : null;

    return (
      <View
        key={message.id || index}
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        {!isUser && (
          <View style={styles.assistantHeader}>
            <Text style={styles.senderName}>복실이</Text>
            {emoji && <Text style={styles.sentimentEmoji}>{emoji}</Text>}
          </View>
        )}
        <Text style={[styles.messageText, isUser && styles.userMessageText]}>
          {message.content}
        </Text>
        <Text style={styles.messageTime}>
          {new Date(message.created_at).toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </Text>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>대화를 불러오고 있어요...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 상단 고정: 대표 사진 */}
      <View style={styles.photoSection}>
        {photoUrl ? (
          <Image
            source={{ uri: photoUrl }}
            style={styles.mainPhoto}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.photoPlaceholder}>
            <Text style={styles.photoPlaceholderIcon}>🐕</Text>
            <Text style={styles.photoPlaceholderText}>복실이와의 대화</Text>
          </View>
        )}
      </View>

      {/* 요약 배너 */}
      <View style={styles.summarySection}>
        <Text style={styles.summaryText} numberOfLines={2}>
          {summary || formatDate(createdAt)}
        </Text>
      </View>

      {/* 대화 기록 스크롤 영역 */}
      <ScrollView
        style={styles.chatSection}
        contentContainerStyle={styles.chatContent}
        showsVerticalScrollIndicator={false}
      >
        {chatMessages.length === 0 ? (
          <View style={styles.emptyMessages}>
            <Text style={styles.emptyMessagesText}>대화 내용이 없어요.</Text>
          </View>
        ) : (
          chatMessages.map((message, index) => renderMessage(message, index))
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  loadingText: {
    marginTop: 15,
    fontSize: fonts.sizes.medium,
    color: colors.textLight,
  },
  photoSection: {
    width: '100%',
    height: width * 0.55,
    backgroundColor: '#E0E0E0',
  },
  mainPhoto: {
    width: '100%',
    height: '100%',
  },
  photoPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.primary,
  },
  photoPlaceholderIcon: {
    fontSize: 60,
    marginBottom: 10,
  },
  photoPlaceholderText: {
    fontSize: fonts.sizes.large,
    color: colors.textWhite,
    fontWeight: 'bold',
  },
  summarySection: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  summaryText: {
    fontSize: fonts.sizes.medium,
    fontWeight: 'bold',
    color: colors.textWhite,
    textAlign: 'center',
    lineHeight: fonts.lineHeights.medium,
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
    padding: 14,
    borderRadius: 16,
    marginVertical: 6,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: colors.primary,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: colors.card,
    ...commonStyles.shadow,
  },
  assistantHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  senderName: {
    fontSize: fonts.sizes.small,
    color: colors.textLight,
    marginRight: 6,
  },
  sentimentEmoji: {
    fontSize: 16,
  },
  messageText: {
    fontSize: fonts.sizes.large,
    color: colors.text,
    lineHeight: fonts.lineHeights.large,
  },
  userMessageText: {
    color: colors.textWhite,
  },
  messageTime: {
    fontSize: 11,
    color: colors.textLight,
    marginTop: 6,
    alignSelf: 'flex-end',
  },
  emptyMessages: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyMessagesText: {
    fontSize: fonts.sizes.large,
    color: colors.textLight,
  },
});

export default ChatHistoryDetailScreen;
