/**
 * 추억 극장 화면
 * S3에서 영상 목록을 불러와 표시
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
  Dimensions,
  ActivityIndicator,
  RefreshControl,
  Modal,
} from 'react-native';
import { Video } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, fonts } from '../theme';
import api from '../api/config';

const { width, height } = Dimensions.get('window');

const VideoGalleryScreen = ({ navigation }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      setLoading(true);

      // AsyncStorage에서 kakao_id 가져오기
      const kakaoId = await AsyncStorage.getItem('kakaoId');

      if (!kakaoId) {
        console.warn('kakaoId가 없습니다.');
        setVideos([]);
        return;
      }

      // 백엔드 API 호출 (S3 URL 포함된 영상 목록)
      const response = await api.get(`/videos/?kakao_id=${kakaoId}`);

      if (Array.isArray(response)) {
        // COMPLETED 상태인 영상만 필터링
        const completedVideos = response.filter(
          (video) => video.status === 'COMPLETED' || video.status === 'completed'
        );

        // 최신순 정렬
        completedVideos.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        setVideos(completedVideos);
        console.log(`✅ 영상 ${completedVideos.length}개 로드 완료`);
      } else {
        console.warn('영상 목록 응답 형식 오류:', response);
        setVideos([]);
      }
    } catch (error) {
      console.error('영상 목록 불러오기 실패:', error);
      Alert.alert('오류', '영상을 불러올 수 없습니다.');
      setVideos([]);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchVideos();
    setRefreshing(false);
  }, []);

  const handleVideoPress = (video) => {
    if (!video.video_url) {
      Alert.alert('알림', '영상이 아직 준비되지 않았어요.');
      return;
    }
    setSelectedVideo(video);
    setIsPlaying(true);
  };

  const closeVideoPlayer = () => {
    setSelectedVideo(null);
    setIsPlaying(false);
  };

  const handleSharePress = async (video) => {
    try {
      // 백엔드에서 공유 메타데이터 가져오기
      const shareData = await api.post(`/videos/${video.id}/share`);

      // 카카오톡 공유 (추후 SDK 연동)
      Alert.alert(
        '카카오톡 공유',
        `"${shareData.title}" 영상을 공유할 준비가 되었어요!`,
        [{ text: '확인' }]
      );
    } catch (error) {
      console.error('공유 실패:', error);
      Alert.alert('오류', '공유 정보를 불러올 수 없습니다.');
    }
  };

  const handleDeletePress = (video) => {
    Alert.alert(
      '영상 삭제',
      '이 추억 영상을 삭제하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/videos/${video.id}`);
              setVideos((prev) => prev.filter((v) => v.id !== video.id));
              Alert.alert('삭제 완료', '영상이 삭제되었어요.');
            } catch (error) {
              console.error('삭제 실패:', error);
              Alert.alert('오류', '영상을 삭제할 수 없습니다.');
            }
          },
        },
      ]
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  const renderVideoItem = ({ item }) => (
    <View style={styles.videoCard}>
      <TouchableOpacity
        onPress={() => handleVideoPress(item)}
        activeOpacity={0.8}
      >
        {/* 썸네일 */}
        <View style={styles.thumbnailContainer}>
          {item.thumbnail_url ? (
            <Image source={{ uri: item.thumbnail_url }} style={styles.thumbnail} />
          ) : (
            <View style={styles.thumbnailPlaceholder}>
              <Text style={styles.thumbnailPlaceholderText}>🎬</Text>
            </View>
          )}
          <View style={styles.playIconOverlay}>
            <View style={styles.playButton}>
              <Text style={styles.playIcon}>▶</Text>
            </View>
          </View>
          {/* 영상 길이 */}
          {item.duration_seconds && (
            <View style={styles.durationBadge}>
              <Text style={styles.durationText}>{formatDuration(item.duration_seconds)}</Text>
            </View>
          )}
        </View>
      </TouchableOpacity>

      {/* 영상 정보 */}
      <View style={styles.videoInfo}>
        <View style={styles.videoTextInfo}>
          <Text style={styles.videoTitle}>
            {item.title || `추억 영상 ${formatDate(item.created_at)}`}
          </Text>
          <Text style={styles.videoDate}>{formatDate(item.created_at)}</Text>
          {item.video_type && (
            <Text style={styles.videoType}>
              {item.video_type === 'slideshow' ? '📷 슬라이드쇼' : '✨ AI 애니메이션'}
            </Text>
          )}
        </View>
        <View style={styles.buttonGroup}>
          <TouchableOpacity
            style={styles.shareButton}
            onPress={() => handleSharePress(item)}
          >
            <Text style={styles.shareButtonText}>공유</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.deleteButton}
            onPress={() => handleDeletePress(item)}
          >
            <Text style={styles.deleteButtonText}>삭제</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>영상을 불러오고 있어요...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {videos.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🎬</Text>
          <Text style={styles.emptyText}>아직 만들어진 영상이 없어요.</Text>
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
          data={videos}
          renderItem={renderVideoItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.videoList}
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

      {/* 비디오 플레이어 모달 */}
      <Modal
        visible={selectedVideo !== null}
        transparent={true}
        animationType="fade"
        onRequestClose={closeVideoPlayer}
      >
        <View style={styles.videoPlayerOverlay}>
          <TouchableOpacity
            style={styles.closeButton}
            onPress={closeVideoPlayer}
          >
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>

          {selectedVideo && (
            <Video
              source={{ uri: selectedVideo.video_url }}
              style={styles.videoPlayer}
              useNativeControls
              resizeMode="contain"
              shouldPlay={isPlaying}
              isLooping={false}
              onPlaybackStatusUpdate={(status) => {
                if (status.didJustFinish) {
                  setIsPlaying(false);
                }
              }}
            />
          )}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  loadingText: {
    marginTop: 15,
    fontSize: 16,
    color: colors.textLight,
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
  thumbnailContainer: {
    position: 'relative',
  },
  thumbnail: {
    width: '100%',
    height: 200,
    backgroundColor: '#E0E0E0',
  },
  thumbnailPlaceholder: {
    width: '100%',
    height: 200,
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  thumbnailPlaceholderText: {
    fontSize: 60,
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
  durationBadge: {
    position: 'absolute',
    bottom: 10,
    right: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  durationText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
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
  videoType: {
    fontSize: fonts.sizes.small,
    color: colors.textLight,
    marginTop: 4,
  },
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
  },
  shareButton: {
    backgroundColor: colors.primary,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
  },
  shareButtonText: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.textWhite,
  },
  deleteButton: {
    backgroundColor: '#EEE',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
  },
  deleteButtonText: {
    fontSize: fonts.sizes.medium,
    fontWeight: 'bold',
    color: '#999',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 80,
    marginBottom: 20,
  },
  emptyText: {
    fontSize: fonts.sizes.xlarge,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
    marginBottom: 10,
  },
  emptySubText: {
    fontSize: fonts.sizes.large,
    fontFamily: fonts.regular,
    color: colors.textLight,
    textAlign: 'center',
    marginBottom: 30,
  },
  startButton: {
    backgroundColor: colors.primary,
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 12,
  },
  startButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.textWhite,
  },

  // 비디오 플레이어 모달
  videoPlayerOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: 50,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  closeButtonText: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: 'bold',
  },
  videoPlayer: {
    width: width,
    height: height * 0.7,
  },
});

export default VideoGalleryScreen;
