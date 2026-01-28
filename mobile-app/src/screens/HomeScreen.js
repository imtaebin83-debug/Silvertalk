/**
 * 홈 화면
 * 수정 사항: 강아지 크기 확대, 위치 상향 조정, 꼬리 밀착 및 레이어 순서 조정
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Image,
  Animated,
  Easing,
} from 'react-native';
import { colors, fonts } from '../theme';

const HomeScreen = ({ navigation }) => {
  const [greeting, setGreeting] = useState('');
  const tailAnimation = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    fetchGreeting();
    startTailWagging();
  }, []);

  const startTailWagging = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(tailAnimation, {
          toValue: 1,
          duration: 400,
          easing: Easing.sinInOut,
          useNativeDriver: true,
        }),
        Animated.timing(tailAnimation, {
          toValue: -1,
          duration: 800,
          easing: Easing.sinInOut,
          useNativeDriver: true,
        }),
        Animated.timing(tailAnimation, {
          toValue: 0,
          duration: 400,
          easing: Easing.sinInOut,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const tailRotation = tailAnimation.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-10deg', '0deg', '10deg'],
  });

  const fetchGreeting = async () => {
    try {
      setGreeting('할머니, 오셨어요? 복실이가 심심했어요! 놀아주세요~');
    } catch (error) {
      setGreeting('멍멍! 반가워요!');
    }
  };

  return (
    <View style={styles.container}>
      {/* 1. 강아지 캐릭터 영역 (중앙으로 올림) */}
      <View style={styles.dogContainer}>
        {/* 꼬리: 몸통 왼쪽(엉덩이) 위치에 배치 */}
        <Animated.Image
          source={require('../../assets/dog_tail.png')}
          style={[
            styles.dogTail,
            {
              transform: [
                { translateX: 40 }, // 회전 중심 조절 (이미지 크기에 맞춤)
                { translateY: 40 },
                { rotate: tailRotation },
                { translateX: -40 },
                { translateY: -40 },
              ],
            },
          ]}
          resizeMode="contain"
        />
        {/* 몸통: 크기를 대폭 키움 */}
        <Image
          source={require('../../assets/dog_body.png')}
          style={styles.dogBody}
          resizeMode="contain"
        />
      </View>

      {/* 2. 터치 레이어 (강아지 클릭 시 대화 시작) */}
      <TouchableOpacity
        style={styles.dogTouchArea}
        onPress={() => navigation.navigate('Gallery')}
        activeOpacity={0.6}
      />

      {/* 3. 상단 및 중앙 UI 레이어 (강아지 위에 덮임) */}
      <SafeAreaView style={styles.overlay} pointerEvents="box-none">
        <StatusBar barStyle="dark-content" translucent backgroundColor="transparent" />

        {/* 상단 버튼들 */}
        <View style={styles.topBar}>
          <View style={styles.leftButtons}>
            <TouchableOpacity style={styles.topButton} onPress={() => navigation.navigate('ChatHistory')}>
              <Text style={styles.topButtonIcon}>💬</Text>
              <Text style={styles.topButtonText}>대화기록</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.topButton} onPress={() => navigation.navigate('VideoGallery')}>
              <Text style={styles.topButtonIcon}>🎬</Text>
              <Text style={styles.topButtonText}>추억극장</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.profileButton} onPress={() => navigation.navigate('Profile')}>
            <View style={styles.profileIcon}><Text style={{fontSize: 28}}>👤</Text></View>
          </TouchableOpacity>
        </View>

        {/* 말풍선 (강아지 이미지 패딩 위로 겹침) */}
        <View style={styles.centerContent} pointerEvents="box-none">
          <TouchableOpacity onPress={() => navigation.navigate('Gallery')} activeOpacity={0.8}>
            <View style={styles.speechBubble}>
              <Text style={styles.greetingText}>{greeting}</Text>
              <View style={styles.speechBubbleTail} />
            </View>
          </TouchableOpacity>
        </View>
      </SafeAreaView>

      {/* 하단 라벨 (강아지 위에 고정) */}
      <View style={styles.bottomContent} pointerEvents="box-none">
        <View style={styles.characterLabel}>
          <Text style={styles.characterLabelText}>복실이</Text>
          <Text style={styles.characterSubLabel}>터치해서 대화 시작!</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background || '#EAEAEA',
    // 화면 전체 콘텐츠를 아래로 밀어내기 위해 상단 패딩 추가
    paddingTop: 60, 
  },
  dogContainer: {
    position: 'absolute',
    bottom: 110,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  dogBody: {
    width: 500,
    height: 580,
  },
  dogTail: {
    position: 'absolute',
    width: 80,
    height: 100,
    left: '14%',
    bottom: '42%',
    zIndex: 0,
  },
  dogTouchArea: {
    position: 'absolute',
    bottom: 60,
    alignSelf: 'center',
    width: '80%',
    height: '50%',
    zIndex: 3,
  },
  overlay: {
    flex: 1,
    zIndex: 2,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 10,
  },
  leftButtons: { flexDirection: 'row', gap: 12 },
  topButton: {
    backgroundColor: colors.primary,
    borderRadius: 18,
    paddingVertical: 14,
    paddingHorizontal: 18,
    alignItems: 'center',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
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
  topButtonIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  topButtonText: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.regular,
    fontWeight: 'bold',
    color: colors.textBlack,
    textAlign: 'center',
  },
  profileButton: {
    padding: 5,
  },
  profileIcon: {
    width: 55,
    height: 55,
    borderRadius: 27.5,
    backgroundColor: '#FFF',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
  },
  centerContent: {
    alignItems: 'center',
    paddingTop: 100,
    paddingHorizontal: 20,
  },
  speechBubble: {
    backgroundColor: '#FFF',
    borderRadius: 25,
    padding: 20,
    maxWidth: '90%',
    elevation: 5,
    position: 'relative',
  },
  speechBubbleTail: {
    position: 'absolute',
    bottom: -12,
    left: '50%',
    marginLeft: -12,
    borderTopWidth: 15,
    borderTopColor: '#FFF',
    borderLeftWidth: 12,
    borderLeftColor: 'transparent',
    borderRightWidth: 12,
    borderRightColor: 'transparent',
  },
  greetingText: {
    fontSize: fonts.sizes.xlarge,
    fontFamily: fonts.regular,
    textAlign: 'center',
    color: colors.text,
    lineHeight: fonts.lineHeights.xlarge,
  },
  bottomContent: {
    position: 'absolute',
    bottom: 200,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 4,
  },
  characterLabel: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    paddingHorizontal: 30,
    paddingVertical: 10,
    borderRadius: 20,
    alignItems: 'center',
  },
  characterLabelText: {
    fontSize: fonts.sizes.xxlarge,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
  },
  characterSubLabel: {
    fontSize: fonts.sizes.small,
    fontFamily: fonts.regular,
    color: colors.textLight,
    marginTop: 4,
    textAlign: 'center',
  },
});

export default HomeScreen;