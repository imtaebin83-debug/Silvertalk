/**
 * 추억 극장 화면
 * 생성된 영상 목록
 */
import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList, 
  TouchableOpacity,
  Image,
  Alert 
} from 'react-native';

const VideoGalleryScreen = ({ navigation }) => {
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/videos/?kakao_id=test');
      // setVideos(response.data);
      
      // 임시 데이터
      setVideos([
        { 
          id: '1', 
          thumbnail_url: 'https://via.placeholder.com/300', 
          created_at: '2024-01-15',
          status: 'completed'
        },
        { 
          id: '2', 
          thumbnail_url: 'https://via.placeholder.com/300', 
          created_at: '2024-01-10',
          status: 'completed'
        },
      ]);
    } catch (error) {
      console.error('영상 목록 불러오기 실패:', error);
      Alert.alert('오류', '영상을 불러올 수 없습니다.');
    }
  };

  const handleVideoPress = (video) => {
    Alert.alert('영상 재생', '영상 플레이어를 여기에 구현합니다.');
    // 추후: 비디오 플레이어 모달 또는 전체화면 재생
  };

  const handleSharePress = (video) => {
    Alert.alert('카카오톡 공유', '카카오톡으로 영상을 공유합니다.');
    // 추후: 카카오톡 공유 SDK 연동
  };

  const renderVideoItem = ({ item }) => (
    <View style={styles.videoCard}>
      <TouchableOpacity onPress={() => handleVideoPress(item)}>
        <Image 
          source={{ uri: item.thumbnail_url }} 
          style={styles.thumbnail} 
        />
        <View style={styles.playIconOverlay}>
          <Text style={styles.playIcon}>▶</Text>
        </View>
      </TouchableOpacity>
      
      <View style={styles.videoInfo}>
        <Text style={styles.videoDate}>{item.created_at}</Text>
        <TouchableOpacity
          style={styles.shareButton}
          onPress={() => handleSharePress(item)}
        >
          <Text style={styles.shareButtonText}>카톡 공유</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>추억 극장</Text>
      
      {videos.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>아직 만들어진 영상이 없어요.</Text>
          <Text style={styles.emptyText}>복실이와 대화를 시작해보세요!</Text>
        </View>
      ) : (
        <FlatList
          data={videos}
          renderItem={renderVideoItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.videoList}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8DC',
    padding: 15,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 20,
    color: '#333',
  },
  videoList: {
    paddingBottom: 20,
  },
  videoCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 15,
    marginBottom: 20,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  thumbnail: {
    width: '100%',
    height: 200,
  },
  playIconOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  playIcon: {
    fontSize: 60,
    color: '#FFFFFF',
  },
  videoInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
  },
  videoDate: {
    fontSize: 18,
    color: '#666',
  },
  shareButton: {
    backgroundColor: '#FFD700',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 10,
  },
  shareButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 22,
    color: '#999',
    textAlign: 'center',
    marginVertical: 5,
  },
});

export default VideoGalleryScreen;
