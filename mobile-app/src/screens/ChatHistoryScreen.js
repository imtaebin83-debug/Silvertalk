/**
 * 대화 기록 목록 화면
 * 설계도 3번: 대화 기록들 나열, 스크롤 가능
 * 각 카드: 왼쪽 위 대화내용 요약(타이틀), 오른쪽 아래 날짜, 대표 사진
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  Alert,
} from 'react-native';

const ChatHistoryScreen = ({ navigation }) => {
  const [chatHistories, setChatHistories] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchChatHistories();
  }, []);

  const fetchChatHistories = async () => {
    try {
      setLoading(true);
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/chat/histories?kakao_id=test');
      // setChatHistories(response.data);

      // 임시 데이터
      setChatHistories([
        {
          id: '1',
          title: '가족 여행 이야기',
          summary: '제주도 여행 갔을 때 이야기를 나눴어요',
          photo_url: 'https://via.placeholder.com/150',
          date: '2024-01-15',
        },
        {
          id: '2',
          title: '손자 돌잔치 추억',
          summary: '손자 돌잔치 때의 행복한 기억',
          photo_url: 'https://via.placeholder.com/150',
          date: '2024-01-10',
        },
        {
          id: '3',
          title: '오래된 친구와의 만남',
          summary: '50년 지기 친구와의 추억',
          photo_url: 'https://via.placeholder.com/150',
          date: '2024-01-05',
        },
        {
          id: '4',
          title: '고향 방문 이야기',
          summary: '어린 시절 살던 고향에 대한 추억',
          photo_url: 'https://via.placeholder.com/150',
          date: '2024-01-01',
        },
      ]);
    } catch (error) {
      console.error('대화 기록 불러오기 실패:', error);
      Alert.alert('오류', '대화 기록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleHistoryPress = (history) => {
    navigation.navigate('ChatHistoryDetail', { historyId: history.id, history });
  };

  const renderHistoryItem = ({ item }) => (
    <TouchableOpacity
      style={styles.historyCard}
      onPress={() => handleHistoryPress(item)}
      activeOpacity={0.8}
    >
      {/* 대표 사진 */}
      <Image source={{ uri: item.photo_url }} style={styles.thumbnail} />

      {/* 텍스트 정보 영역 */}
      <View style={styles.cardContent}>
        {/* 상단: 타이틀(대화 내용 요약) */}
        <View style={styles.titleContainer}>
          <Text style={styles.titleText} numberOfLines={1}>
            {item.title}
          </Text>
        </View>

        {/* 하단: 날짜 */}
        <View style={styles.dateContainer}>
          <Text style={styles.dateText}>{item.date}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      {chatHistories.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>💬</Text>
          <Text style={styles.emptyText}>아직 대화 기록이 없어요.</Text>
          <Text style={styles.emptySubText}>복실이와 대화를 시작해보세요!</Text>
        </View>
      ) : (
        <FlatList
          data={chatHistories}
          renderItem={renderHistoryItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContainer}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8DC',
  },
  listContainer: {
    padding: 15,
    paddingBottom: 30,
  },
  historyCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 15,
    marginBottom: 15,
    flexDirection: 'row',
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  thumbnail: {
    width: 120,
    height: 100,
    backgroundColor: '#E0E0E0',
  },
  cardContent: {
    flex: 1,
    padding: 12,
    justifyContent: 'space-between',
  },
  titleContainer: {
    flex: 1,
  },
  titleText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  dateContainer: {
    alignItems: 'flex-end',
  },
  dateText: {
    fontSize: 14,
    color: '#888',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 60,
    marginBottom: 20,
  },
  emptyText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#666',
    textAlign: 'center',
    marginBottom: 10,
  },
  emptySubText: {
    fontSize: 18,
    color: '#999',
    textAlign: 'center',
  },
});

export default ChatHistoryScreen;
