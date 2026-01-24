/**
 * 갤러리 화면 (사진 선택)
 * 랜덤 6장 사진 제공
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

const GalleryScreen = ({ navigation }) => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRandomPhotos();
  }, []);

  const fetchRandomPhotos = async () => {
    try {
      setLoading(true);
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/photos/random?kakao_id=test&limit=6');
      // setPhotos(response.data);
      
      // 임시 데이터
      setPhotos([
        { id: '1', s3_url: 'https://via.placeholder.com/300', taken_at: '2010-05-15' },
        { id: '2', s3_url: 'https://via.placeholder.com/300', taken_at: '2012-08-20' },
        { id: '3', s3_url: 'https://via.placeholder.com/300', taken_at: '2015-03-10' },
        { id: '4', s3_url: 'https://via.placeholder.com/300', taken_at: '2018-11-05' },
        { id: '5', s3_url: 'https://via.placeholder.com/300', taken_at: '2020-07-18' },
        { id: '6', s3_url: 'https://via.placeholder.com/300', taken_at: '2022-01-22' },
      ]);
    } catch (error) {
      console.error('사진 불러오기 실패:', error);
      Alert.alert('오류', '사진을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoSelect = (photo) => {
    Alert.alert(
      '이 사진으로 대화할까요?',
      '선택하신 사진으로 복실이와 대화를 시작합니다.',
      [
        { text: '다시 선택', style: 'cancel' },
        { 
          text: '네, 좋아요!', 
          onPress: () => navigation.navigate('Chat', { photoId: photo.id })
        },
      ]
    );
  };

  const renderPhotoItem = ({ item }) => (
    <TouchableOpacity
      style={styles.photoCard}
      onPress={() => handlePhotoSelect(item)}
    >
      <Image 
        source={{ uri: item.s3_url }} 
        style={styles.photoImage} 
      />
      <Text style={styles.photoDate}>{item.taken_at}</Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>어떤 사진으로 이야기할까요?</Text>
      
      <FlatList
        data={photos}
        renderItem={renderPhotoItem}
        keyExtractor={(item) => item.id}
        numColumns={2}
        contentContainerStyle={styles.photoGrid}
      />

      <TouchableOpacity
        style={styles.refreshButton}
        onPress={fetchRandomPhotos}
      >
        <Text style={styles.refreshButtonText}>다른 사진 보기</Text>
      </TouchableOpacity>
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
    fontSize: 26,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 20,
    color: '#333',
  },
  photoGrid: {
    paddingBottom: 100,
  },
  photoCard: {
    flex: 1,
    margin: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 15,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  photoImage: {
    width: '100%',
    height: 150,
  },
  photoDate: {
    fontSize: 16,
    padding: 10,
    textAlign: 'center',
    color: '#666',
  },
  refreshButton: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    backgroundColor: '#FFA500',
    borderRadius: 15,
    paddingVertical: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3.84,
    elevation: 5,
  },
  refreshButtonText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
  },
});

export default GalleryScreen;
