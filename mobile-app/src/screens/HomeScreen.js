/**
 * 메인 화면 (강아지 홈)
 * 강아지가 먼저 말을 거는 화면
 */
import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Image,
  Animated 
} from 'react-native';

const HomeScreen = ({ navigation }) => {
  const [greeting, setGreeting] = useState('');
  const [dogAnimation] = useState(new Animated.Value(0));

  useEffect(() => {
    // 강아지 애니메이션 (꼬리 흔들기)
    Animated.loop(
      Animated.sequence([
        Animated.timing(dogAnimation, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(dogAnimation, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // 강아지 인사 메시지 불러오기
    fetchGreeting();
  }, []);

  const fetchGreeting = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/home/greeting?kakao_id=test');
      // setGreeting(response.data.message);
      
      // 임시 메시지
      setGreeting('할머니, 오셨어요? 복실이가 심심했어요! 놀아주세요~');
    } catch (error) {
      console.error('인사 메시지 불러오기 실패:', error);
      setGreeting('멍멍! 반가워요!');
    }
  };

  const tailRotate = dogAnimation.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '30deg'],
  });

  return (
    <View style={styles.container}>
      {/* 강아지 캐릭터 */}
      <View style={styles.dogContainer}>
        <Animated.Image
          source={require('../../assets/dog-character.png')} // 추후 이미지 추가
          style={[
            styles.dogImage,
            { transform: [{ rotate: tailRotate }] }
          ]}
          resizeMode="contain"
        />
      </View>

      {/* 말풍선 */}
      <View style={styles.speechBubble}>
        <Text style={styles.greetingText}>{greeting}</Text>
      </View>

      {/* 큰 버튼 (어르신용 UI) */}
      <TouchableOpacity
        style={styles.bigButton}
        onPress={() => navigation.navigate('Gallery')}
      >
        <Text style={styles.buttonText}>사진 보러 가기</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.bigButton, styles.secondaryButton]}
        onPress={() => navigation.navigate('VideoGallery')}
      >
        <Text style={styles.buttonText}>추억 극장</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8DC',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  dogContainer: {
    width: 200,
    height: 200,
    marginBottom: 40,
  },
  dogImage: {
    width: '100%',
    height: '100%',
  },
  speechBubble: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 25,
    marginBottom: 50,
    maxWidth: '90%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  greetingText: {
    fontSize: 22, // 큰 글씨
    textAlign: 'center',
    color: '#333',
    lineHeight: 32,
  },
  bigButton: {
    backgroundColor: '#FFD700',
    borderRadius: 15,
    paddingVertical: 25,
    paddingHorizontal: 50,
    marginVertical: 10,
    width: '80%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3.84,
    elevation: 5,
  },
  secondaryButton: {
    backgroundColor: '#FFA500',
  },
  buttonText: {
    fontSize: 26, // 매우 큰 글씨
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
  },
});

export default HomeScreen;
