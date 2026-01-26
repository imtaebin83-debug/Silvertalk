/**
 * 홈 화면
 * 설계도 1번: 좌상단 대화기록/추억극장 버튼, 우상단 프로필, 중앙 캐릭터+말풍선
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Animated,
  SafeAreaView,
  StatusBar,
} from 'react-native';

const HomeScreen = ({ navigation }) => {
  const [greeting, setGreeting] = useState('');
  const [dogAnimation] = useState(new Animated.Value(0));

  useEffect(() => {
    // 강아지 좌우 흔들리는 애니메이션
    Animated.loop(
      Animated.sequence([
        Animated.timing(dogAnimation, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(dogAnimation, {
          toValue: -1,
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

    fetchGreeting();
  }, []);

  const fetchGreeting = async () => {
    try {
      // API 호출 (추후 구현)
      // const response = await axios.get('http://localhost:8000/home/greeting?kakao_id=test');
      // setGreeting(response.data.message);
      setGreeting('할머니, 오셨어요? 복실이가 심심했어요! 놀아주세요~');
    } catch (error) {
      console.error('인사 메시지 불러오기 실패:', error);
      setGreeting('멍멍! 반가워요!');
    }
  };

  const wobble = dogAnimation.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-5deg', '0deg', '5deg'],
  });

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFF8DC" />

      {/* 상단 버튼 영역 */}
      <View style={styles.topBar}>
        {/* 좌상단: 대화기록 + 추억극장 버튼 */}
        <View style={styles.leftButtons}>
          <TouchableOpacity
            style={styles.topButton}
            onPress={() => navigation.navigate('ChatHistory')}
          >
            <Text style={styles.topButtonText}>대화{'\n'}기록</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.topButton}
            onPress={() => navigation.navigate('VideoGallery')}
          >
            <Text style={styles.topButtonText}>추억{'\n'}극장</Text>
          </TouchableOpacity>
        </View>

        {/* 우상단: 프로필 버튼 */}
        <TouchableOpacity
          style={styles.profileButton}
          onPress={() => navigation.navigate('Profile')}
        >
          <View style={styles.profileIcon}>
            <Text style={styles.profileIconText}>👤</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* 중앙 컨텐츠 영역 */}
      <View style={styles.centerContent}>
        {/* 말풍선 */}
        <View style={styles.speechBubble}>
          <Text style={styles.greetingText}>{greeting}</Text>
          <View style={styles.speechBubbleTail} />
        </View>

        {/* 강아지 캐릭터 (터치하면 Gallery로 이동) */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Gallery')}
          activeOpacity={0.8}
        >
          <Animated.Image
            source={require('../../assets/dog.png')}
            style={[
              styles.dogImage,
              { transform: [{ rotate: wobble }] }
            ]}
            resizeMode="contain"
          />
        </TouchableOpacity>

        {/* 캐릭터 설명 */}
        <View style={styles.characterLabel}>
          <Text style={styles.characterLabelText}>복실이</Text>
          <Text style={styles.characterSubLabel}>터치해서 대화 시작!</Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8DC',
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 15,
    paddingTop: 10,
  },
  leftButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  topButton: {
    backgroundColor: '#FFD700',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  topButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 20,
  },
  profileButton: {
    padding: 5,
  },
  profileIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  profileIconText: {
    fontSize: 28,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  speechBubble: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
    maxWidth: '85%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 3.84,
    elevation: 5,
    position: 'relative',
  },
  speechBubbleTail: {
    position: 'absolute',
    bottom: -10,
    left: '50%',
    marginLeft: -10,
    width: 0,
    height: 0,
    borderLeftWidth: 10,
    borderRightWidth: 10,
    borderTopWidth: 10,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
    borderTopColor: '#FFFFFF',
  },
  greetingText: {
    fontSize: 22,
    textAlign: 'center',
    color: '#333',
    lineHeight: 32,
  },
  dogImage: {
    width: 250,
    height: 250,
  },
  characterLabel: {
    marginTop: 15,
    alignItems: 'center',
  },
  characterLabelText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  characterSubLabel: {
    fontSize: 16,
    color: '#888',
    marginTop: 5,
  },
});

export default HomeScreen;
