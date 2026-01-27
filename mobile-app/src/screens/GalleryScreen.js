import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Alert,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage'; // ✅ AsyncStorage 임포트 필수
import { colors, fonts } from '../theme';
import * as MediaLibrary from 'expo-media-library';
import api from '../api/config';

const { width } = Dimensions.get('window');
const PHOTO_SIZE = (width - 60) / 2;

const GalleryScreen = ({ navigation }) => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dogMessage, setDogMessage] = useState('');
  const [userId, setUserId] = useState(null);
  const [allPhotos, setAllPhotos] = useState([]); // 전체 사진 보관용

  useEffect(() => {
    const initializeGallery = async () => {
      try {
        setLoading(true);
        setDogMessage('갤러리에서 사진을 불러오고 있어요...');

        // 1. 갤러리 권한 요청
        const { status } = await MediaLibrary.requestPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert('권한 필요', '사진을 불러오려면 갤러리 접근 권한이 필요해요.');
          setLoading(false);
          return;
        }

        // 2. AsyncStorage에서 카카오 ID 가져오기
        const savedId = await AsyncStorage.getItem('kakaoId');
        setUserId(savedId);
        const targetId = savedId || '4719864509';

        // 3. 갤러리에서 사진 가져오기 (최대 100장)
        const mediaResult = await MediaLibrary.getAssetsAsync({
          mediaType: 'photo',
          first: 100,
          sortBy: [MediaLibrary.SortBy.creationTime],
        });

        if (mediaResult.assets.length === 0) {
          setDogMessage('갤러리에 사진이 없어요!');
          setLoading(false);
          return;
        }

        // 4. 사진 메타데이터 변환
        const photoMetadata = mediaResult.assets.map((asset) => ({
          local_uri: asset.uri,
          taken_at: asset.creationTime ? new Date(asset.creationTime).toISOString() : null,
          location_name: null,
          latitude: null,
          longitude: null,
        }));

        // 5. 서버에 메타데이터 동기화
        try {
          await api.post(`/photos/sync-metadata?kakao_id=${targetId}`, {
            photos: photoMetadata,
          });
          console.log('✅ 메타데이터 동기화 완료:', photoMetadata.length, '장');
        } catch (syncError) {
          console.error('메타데이터 동기화 실패:', syncError);
        }

        // 6. 전체 사진 저장 (로컬에서 사용)
        const localPhotos = mediaResult.assets.map((asset, index) => ({
          id: asset.id,
          local_uri: asset.uri,
          s3_url: null,
          taken_at: asset.creationTime ? new Date(asset.creationTime).toISOString() : null,
          index: index, // 원본 인덱스 저장 (앞뒤 사진 찾기용)
        }));
        setAllPhotos(localPhotos);

        // 7. 랜덤 4장 선택
        const shuffled = [...localPhotos].sort(() => Math.random() - 0.5);
        setPhotos(shuffled.slice(0, 4));
        setDogMessage('제일 대화 나누고 싶은 사진을 골라주세요!');

      } catch (e) {
        console.error('갤러리 초기화 실패:', e);
        setDogMessage('사진을 불러오는데 실패했어요.');
      } finally {
        setLoading(false);
      }
    };

    initializeGallery();
  }, []);

  // 사진 선택 시 로직 - 선택된 사진 + 앞뒤 3장 (총 7장) S3 업로드
  const handlePhotoSelect = async (photo) => {
    try {
      setLoading(true);
      setDogMessage('복실이가 사진들을 챙기고 있어요! 잠시만요...');

      // 1. 선택된 사진의 인덱스 찾기
      const selectedIndex = allPhotos.findIndex((p) => p.id === photo.id);
      if (selectedIndex === -1) {
        throw new Error('선택된 사진을 찾을 수 없습니다.');
      }

      // 2. 앞뒤 3장씩 가져오기 (총 7장)
      const startIdx = Math.max(0, selectedIndex - 3);
      const endIdx = Math.min(allPhotos.length, selectedIndex + 4);
      const photosToUpload = allPhotos.slice(startIdx, endIdx);

      // 선택된 사진이 배열 내에서 몇 번째인지 계산 (메인 사진 표시용)
      const mainPhotoIndex = selectedIndex - startIdx;

      console.log(`📸 업로드할 사진: ${photosToUpload.length}장 (인덱스 ${startIdx}~${endIdx - 1})`);

      // 3. 채팅 세션 생성 (kakao_id 포함)
      const kakaoId = userId || await AsyncStorage.getItem('kakaoId') || '4719864509';
      const sessionResponse = await api.post('/chat/sessions', {
        kakao_id: kakaoId,
        photo_id: photo.id,
      });
      const sid = sessionResponse.id || sessionResponse.session_id;

      if (!sid) {
        throw new Error('세션 ID를 생성하지 못했습니다.');
      }

      // 4. FormData 구성 - 7장의 사진 추가
      const formData = new FormData();
      photosToUpload.forEach((p, idx) => {
        formData.append('files', {
          uri: p.local_uri,
          type: 'image/jpeg',
          name: `photo_${idx}.jpg`,
        });
      });

      // 5. S3 배치 업로드 실행
      const uploadRes = await fetch(
        `http://54.180.28.75:8000/photos/batch-upload?session_id=${sid}`,
        {
          method: 'POST',
          body: formData,
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      const uploadResult = await uploadRes.json();
      console.log('✅ S3 업로드 결과:', uploadResult);

      // 6. 업로드된 사진 URL 목록 추출
      const uploadedPhotoUrls = uploadResult.photos
        ? uploadResult.photos.map((p) => p.url)
        : [];

      // 7. 성공 시 ChatScreen으로 이동 (업로드된 사진 정보 전달)
      navigation.navigate('Chat', {
        sessionId: sid,
        photoUrl: uploadedPhotoUrls[mainPhotoIndex] || photo.local_uri, // 메인 사진 URL
        photoDate: photo.taken_at,
        allPhotoUrls: uploadedPhotoUrls, // 전체 업로드된 사진 URL
        mainPhotoIndex: mainPhotoIndex, // 메인 사진 인덱스
      });

    } catch (error) {
      console.error('세션 생성 및 업로드 실패:', error);
      Alert.alert('오류', '대화를 시작하지 못했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  // 새로고침 - 로컬 사진에서 다시 랜덤 선택
  const handleRefresh = () => {
    if (allPhotos.length === 0) {
      setDogMessage('갤러리에 사진이 없어요!');
      return;
    }
    const shuffled = [...allPhotos].sort(() => Math.random() - 0.5);
    setPhotos(shuffled.slice(0, 4));
    setDogMessage('새로운 사진들을 가져왔어요!');
  };

  const handleMicPress = () => {
    Alert.alert('음성 인식', '제일 마음에 드는 사진을 손가락으로 눌러주세요!');
  };

  return (
    <View style={styles.container}>
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{dogMessage}</Text>
        </View>
      )}

      <View style={styles.topSection}>
        <View style={styles.characterContainer}>
          <Image
            source={require('../../assets/dog_nukki.png')}
            style={styles.smallDog}
            resizeMode="contain"
          />
        </View>
        <View style={styles.speechBubble}>
          <Text style={styles.speechText}>{dogMessage}</Text>
        </View>
      </View>

      <View style={styles.photoGrid}>
        {photos.map((photo) => (
          <TouchableOpacity
            key={photo.id}
            style={styles.photoCard}
            onPress={() => handlePhotoSelect(photo)}
            activeOpacity={0.8}
            disabled={loading}
          >
            <Image 
              source={{ uri: photo.s3_url || photo.local_uri }} 
              style={styles.photoImage} 
            />
            <View style={styles.photoDateBadge}>
              <Text style={styles.photoDateText}>
                {photo.taken_at ? new Date(photo.taken_at).toLocaleDateString() : '날짜 없음'}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.bottomSection}>
        <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh}>
          <Text style={styles.refreshIcon}>🔄</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.micButton} onPress={handleMicPress}>
          <Text style={styles.micIcon}>🎤</Text>
          <Text style={styles.micText}>말하기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 15 },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    zIndex: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: { marginTop: 15, fontFamily: fonts.bold, color: colors.primary },
  topSection: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  characterContainer: { width: 60, height: 60 },
  smallDog: { width: '130%', height: '130%' },
  speechBubble: {
    flex: 1, backgroundColor: colors.white, borderRadius: 15,
    padding: 12, marginLeft: 10, elevation: 2,
  },
  speechText: { fontSize: fonts.sizes.medium, fontFamily: fonts.regular, color: colors.text },
  photoGrid: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  photoCard: {
    width: PHOTO_SIZE, height: PHOTO_SIZE, marginBottom: 15,
    borderRadius: 15, overflow: 'hidden', backgroundColor: colors.white, elevation: 4,
  },
  photoImage: { width: '100%', height: '100%', backgroundColor: '#E0E0E0' },
  photoDateBadge: {
    position: 'absolute', bottom: 8, right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.6)', borderRadius: 8, padding: 4,
  },
  photoDateText: { fontSize: fonts.sizes.small, color: colors.textWhite },
  bottomSection: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 20 },
  refreshButton: {
    width: 60, height: 60, borderRadius: 30, backgroundColor: colors.white,
    justifyContent: 'center', alignItems: 'center', elevation: 4,
  },
  refreshIcon: { fontSize: 28 },
  micButton: {
    width: 100, height: 100, borderRadius: 50, backgroundColor: colors.primary,
    justifyContent: 'center', alignItems: 'center', elevation: 6,
  },
  micIcon: { fontSize: 36 },
  micText: { fontSize: fonts.sizes.small, fontFamily: fonts.bold, color: colors.textWhite },
});

export default GalleryScreen;