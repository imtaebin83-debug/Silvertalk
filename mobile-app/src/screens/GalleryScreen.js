/**
 * 갤러리 화면 (사진 선택)
 * 설계도 6번: 왼쪽 위 작은 캐릭터 + 말풍선, 2x2 사진 4장, 하단 마이크 + 새로고침
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Alert,
  Dimensions,
} from 'react-native';
import { colors, fonts } from '../theme';

const { width } = Dimensions.get('window');
const PHOTO_SIZE = (width - 60) / 2; // 2열, 좌우 패딩 고려

const GalleryScreen = ({ navigation }) => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dogMessage, setDogMessage] = useState('');

  useEffect(() => {
    fetchRandomPhotos();
    setDogMessage('제일 대화 나누고 싶은 사진을 골라주세요!');
  }, []);

  const fetchRandomPhotos = async () => {
    try {
      setLoading(true);
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/photos/random?kakao_id=test&limit=4');
      // setPhotos(response.data);

      // 임시 데이터 - 4장
      setPhotos([
        { id: '1', s3_url: 'https://via.placeholder.com/300', taken_at: '2010-05-15' },
        { id: '2', s3_url: 'https://via.placeholder.com/300', taken_at: '2012-08-20' },
        { id: '3', s3_url: 'https://via.placeholder.com/300', taken_at: '2015-03-10' },
        { id: '4', s3_url: 'https://via.placeholder.com/300', taken_at: '2018-11-05' },
      ]);
    } catch (error) {
      console.error('사진 불러오기 실패:', error);
      Alert.alert('오류', '사진을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoSelect = (photo) => {
    // 선택한 사진으로 대화 화면으로 이동
    navigation.navigate('Chat', {
      photoId: photo.id,
      photoUrl: photo.s3_url,
      photoDate: photo.taken_at,
    });
  };

  const handleRefresh = () => {
    setDogMessage('새로운 사진들을 가져왔어요!');
    fetchRandomPhotos();
  };

  const handleMicPress = () => {
    // 마이크 기능 (추후 STT 구현)
    Alert.alert('음성 인식', '말씀해주세요! (음성 인식 기능 추후 구현)');
  };

  return (
    <View style={styles.container}>
      {/* 상단: 캐릭터 + 말풍선 */}
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

      {/* 중앙: 사진 2x2 그리드 */}
      <View style={styles.photoGrid}>
        {photos.map((photo) => (
          <TouchableOpacity
            key={photo.id}
            style={styles.photoCard}
            onPress={() => handlePhotoSelect(photo)}
            activeOpacity={0.8}
          >
            <Image source={{ uri: photo.s3_url }} style={styles.photoImage} />
            <View style={styles.photoDateBadge}>
              <Text style={styles.photoDateText}>{photo.taken_at}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* 하단: 마이크 + 새로고침 버튼 */}
      <View style={styles.bottomSection}>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={handleRefresh}
          activeOpacity={0.8}
        >
          <Text style={styles.refreshIcon}>🔄</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.micButton}
          onPress={handleMicPress}
          activeOpacity={0.8}
        >
          <Text style={styles.micIcon}>🎤</Text>
          <Text style={styles.micText}>말하기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: 15,
  },
  topSection: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  characterContainer: {
    width: 60,
    height: 60,
  },
  smallDog: {
    width: '130%',
    height: '130%',
  },
  speechBubble: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 15,
    padding: 12,
    marginLeft: 10,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  speechText: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.regular,
    color: colors.text,
  },
  photoGrid: {
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    alignContent: 'center',
  },
  photoCard: {
    width: PHOTO_SIZE,
    height: PHOTO_SIZE,
    marginBottom: 15,
    borderRadius: 15,
    overflow: 'hidden',
    backgroundColor: colors.white,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  photoImage: {
    width: '100%',
    height: '100%',
    backgroundColor: '#E0E0E0',
  },
  photoDateBadge: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  photoDateText: {
    fontSize: fonts.sizes.small,
    fontFamily: fonts.regular,
    color: colors.textWhite,
  },
  bottomSection: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 15,
    gap: 20,
  },
  refreshButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: colors.white,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  refreshIcon: {
    fontSize: 28,
  },
  micButton: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 6,
  },
  micIcon: {
    fontSize: 36,
  },
  micText: {
    fontSize: fonts.sizes.small,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.textWhite,
    marginTop: 4,
  },
});

export default GalleryScreen;
