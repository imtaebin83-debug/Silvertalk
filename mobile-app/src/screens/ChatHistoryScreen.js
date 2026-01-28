/**
 * 대화 기록 목록 화면
 * 설계도 3번: 대화 기록들 나열, 스크롤 가능
 * 각 카드: 왼쪽 위 대화내용 요약(타이틀), 오른쪽 아래 날짜, 대표 사진
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, fonts, commonStyles } from '../theme';
import api from '../api/config';

const ChatHistoryScreen = ({ navigation }) => {
  const [chatHistories, setChatHistories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchChatHistories();
  }, []);

  const fetchChatHistories = async () => {
    try {
      setLoading(true);

      // AsyncStorage에서 kakao_id 가져오기
      const kakaoId = await AsyncStorage.getItem('kakaoId');

      if (!kakaoId) {
        console.warn('⚠️ kakaoId가 없습니다. 로그인이 필요합니다.');
        setChatHistories([]);
        setLoading(false);
        return;
      }

      // 백엔드 API 호출: GET /chat/sessions?kakao_id=xxx
      const response = await api.get(`/chat/sessions?kakao_id=${kakaoId}`);

      if (Array.isArray(response)) {
        // 완료된 세션만 필터링 (대화가 있는 것)
        const completedSessions = response.filter(
          (session) => session.turn_count > 0
        );

        // 최신순 정렬 (이미 백엔드에서 정렬되어 옴)
        setChatHistories(completedSessions);
        console.log(`✅ 대화 기록 ${completedSessions.length}개 로드 완료`);
      } else {
        console.warn('대화 기록 응답 형식 오류:', response);
        setChatHistories([]);
      }
    } catch (error) {
      console.error('❌ 대화 기록 불러오기 실패:', error);
      // 사용자 친화적 에러 메시지
      Alert.alert(
        '연결 오류',
        '대화 기록을 불러올 수 없어요.\n인터넷 연결을 확인해주세요.',
        [{ text: '확인' }]
      );
      setChatHistories([]);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchChatHistories();
    setRefreshing(false);
  }, []);

  const handleHistoryPress = (session) => {
    navigation.navigate('ChatHistoryDetail', {
      sessionId: session.id,
      mainPhotoId: session.main_photo_id,
      summary: session.summary,
      createdAt: session.created_at,
    });
  };

  const handleDeletePress = (session) => {
    Alert.alert(
      '대화 기록 삭제',
      '이 대화 기록을 삭제하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/chat/sessions/${session.id}`);
              setChatHistories((prev) =>
                prev.filter((s) => s.id !== session.id)
              );
              Alert.alert('삭제 완료', '대화 기록이 삭제되었어요.');
            } catch (error) {
              console.error('삭제 실패:', error);
              Alert.alert('오류', '삭제할 수 없습니다.');
            }
          },
        },
      ]
    );
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;

    return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
  };

  // 세션 제목 생성 (summary 또는 fallback)
  const getSessionTitle = (session) => {
    if (session.summary && session.summary.length > 0) {
      return session.summary.length > 30
        ? session.summary.substring(0, 30) + '...'
        : session.summary;
    }
    return `대화 ${session.turn_count}턴`;
  };

  const renderHistoryItem = ({ item }) => (
    <TouchableOpacity
      style={styles.historyCard}
      onPress={() => handleHistoryPress(item)}
      onLongPress={() => handleDeletePress(item)}
      activeOpacity={0.8}
    >
      {/* 대표 사진 */}
      <View style={styles.thumbnailContainer}>
        {item.main_photo_url ? (
          <Image source={{ uri: item.main_photo_url }} style={styles.thumbnail} />
        ) : (
          <View style={styles.thumbnailPlaceholder}>
            <Text style={styles.thumbnailPlaceholderText}>🐕</Text>
          </View>
        )}
      </View>

      {/* 텍스트 정보 영역 */}
      <View style={styles.cardContent}>
        {/* 상단: 타이틀(대화 내용 요약) */}
        <View style={styles.titleContainer}>
          <Text style={styles.titleText} numberOfLines={2}>
            {getSessionTitle(item)}
          </Text>
        </View>

        {/* 하단: 메타 정보 */}
        <View style={styles.metaContainer}>
          <Text style={styles.turnCountText}>💬 {item.turn_count}턴</Text>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>대화 기록을 불러오고 있어요...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {chatHistories.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>💬</Text>
          <Text style={styles.emptyText}>아직 대화 기록이 없어요.</Text>
          <Text style={styles.emptySubText}>복실이와 대화를 시작해보세요!</Text>
          <TouchableOpacity
            style={styles.startButton}
            onPress={() => navigation.navigate('Gallery')}
          >
            <Text style={styles.startButtonText}>대화 시작하기</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={chatHistories}
          renderItem={renderHistoryItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContainer}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.primary}
            />
          }
        />
      )}
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
  listContainer: {
    padding: 15,
    paddingBottom: 30,
  },
  historyCard: {
    backgroundColor: colors.card,
    borderRadius: 16,
    marginBottom: 15,
    flexDirection: 'row',
    overflow: 'hidden',
    ...commonStyles.shadow,
  },
  thumbnailContainer: {
    width: 110,
    height: 100,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
    backgroundColor: '#E0E0E0',
  },
  thumbnailPlaceholder: {
    width: '100%',
    height: '100%',
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  thumbnailPlaceholderText: {
    fontSize: 36,
  },
  cardContent: {
    flex: 1,
    padding: 14,
    justifyContent: 'space-between',
  },
  titleContainer: {
    flex: 1,
  },
  titleText: {
    fontSize: fonts.sizes.large,
    fontWeight: 'bold',
    color: colors.text,
    lineHeight: fonts.lineHeights.medium,
  },
  metaContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  turnCountText: {
    fontSize: fonts.sizes.small,
    color: colors.textLight,
  },
  dateText: {
    fontSize: fonts.sizes.small,
    color: colors.textLight,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 70,
    marginBottom: 20,
  },
  emptyText: {
    fontSize: fonts.sizes.xlarge,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
    marginBottom: 10,
  },
  emptySubText: {
    fontSize: fonts.sizes.large,
    color: colors.textLight,
    textAlign: 'center',
    marginBottom: 30,
  },
  startButton: {
    backgroundColor: colors.primary,
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    ...commonStyles.shadow,
  },
  startButtonText: {
    fontSize: fonts.sizes.large,
    fontWeight: 'bold',
    color: colors.textWhite,
  },
});

export default ChatHistoryScreen;
