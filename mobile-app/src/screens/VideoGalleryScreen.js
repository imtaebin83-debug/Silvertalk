/**
 * 추억 극장 화면
 * 설계도 2번: 만들었던 영상들 나열, 아래로 스크롤 가능
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
  Dimensions,
} from 'react-native';
import { colors, fonts } from '../theme';

const { width } = Dimensions.get('window');

const { width } = Dimensions.get('window');

const VideoGalleryScreen = ({ navigation }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/videos/?kakao_id=test');
      // setVideos(response.data);

      // 임시 데이터
      setVideos([
        {
          id: '1',
          thumbnail_url: 'https://via.placeholder.com/400x250',
          created_at: '2024-01-15',
          title: '가족 여행 추억',
          status: 'completed',
        },
        {
          id: '2',
          thumbnail_url: 'https://via.placeholder.com/400x250',
          created_at: '2024-01-10',
          title: '손자와 함께한 날',
          status: 'completed',
        },
        {
          id: '3',
          thumbnail_url: 'https://via.placeholder.com/400x250',
          created_at: '2024-01-05',
          title: '생신 파티',
          status: 'completed',
        },
      ]);
    } catch (error) {
      console.error('영상 목록 불러오기 실패:', error);
      Alert.alert('오류', '영상을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
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
      <TouchableOpacity
        onPress={() => handleVideoPress(item)}
        activeOpacity={0.8}
      >
        <Image source={{ uri: item.thumbnail_url }} style={styles.thumbnail} />
        <View style={styles.playIconOverlay}>
          <View style={styles.playButton}>
            <Text style={styles.playIcon}>▶</Text>
          </View>
        </View>
      </TouchableOpacity>

      <View style={styles.videoInfo}>
        <View style={styles.videoTextInfo}>
          <Text style={styles.videoTitle}>{item.title}</Text>
          <Text style={styles.videoDate}>{item.created_at}</Text>
        </View>
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
      {videos.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🎬</Text>
          <Text style={styles.emptyText}>아직 만들어진 영상이 없어요.</Text>
          <Text style={styles.emptySubText}>복실이와 대화를 시작해보세요!</Text>
        </View>
      ) : (
        <FlatList
          data={videos}
          renderItem={renderVideoItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.videoList}
          showsVerticalScrollIndicator={false}
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
  videoList: {
    padding: 15,
    paddingBottom: 30,
  },
  videoCard: {
    backgroundColor: colors.white,
    borderRadius: 15,
    marginBottom: 20,
    overflow: 'hidden',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 5,
  },
  thumbnail: {
    width: '100%',
    height: 200,
    backgroundColor: '#E0E0E0',
  },
  playIconOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.25)',
  },
  playButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playIcon: {
    fontSize: 30,
    color: colors.primary,
    marginLeft: 5,
  },
  videoInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
  },
  videoTextInfo: {
    flex: 1,
  },
  videoTitle: {
    fontSize: fonts.sizes.xlarge,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 5,
  },
  videoDate: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.regular,
    color: colors.textLight,
  },
  shareButton: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 10,
    marginLeft: 10,
  },
  shareButtonText: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.textWhite,
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
    fontSize: fonts.sizes.xlarge,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.textLight,
    textAlign: 'center',
    marginBottom: 10,
  },
  emptySubText: {
    fontSize: fonts.sizes.large,
    fontFamily: fonts.regular,
    color: '#999',
    textAlign: 'center',
  },
});

export default VideoGalleryScreen;
