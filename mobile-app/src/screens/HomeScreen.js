/**
 * 홈 화면
 * 설계도 1번: 좌상단 대화기록/추억극장 버튼, 우상단 프로필, 중앙 캐릭터+말풍선
 * Rive 애니메이션을 배경으로 사용
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import Rive, { Fit, Alignment } from 'rive-react-native';

const HomeScreen = ({ navigation }) => {
  const [greeting, setGreeting] = useState('');
  const riveRef = useRef(null);

  useEffect(() => {
    fetchGreeting();
  }, []);

  const fetchGreeting = async () => {
    try {
      setGreeting('할머니, 오셨어요? 복실이가 심심했어요! 놀아주세요~');
    } catch (error) {
      console.error('인사 메시지 불러오기 실패:', error);
      setGreeting('멍멍! 반가워요!');
    }
  };

  return (
    <View style={styles.container}>
      {/* Rive 배경 - 전체 화면에 움직이는 강아지 (터치 이벤트 통과) */}
      <View style={StyleSheet.absoluteFillObject} pointerEvents="none">
        <Rive
          ref={riveRef}
          resourceName="dog2"
          autoplay={true}
          fit={Fit.Cover}
          alignment={Alignment.Center}
          style={StyleSheet.absoluteFillObject}
        />
      </View>

      {/* 강아지 터치 영역 - 화면 중앙 하단 */}
      <TouchableOpacity
        style={styles.dogTouchArea}
        onPress={() => navigation.navigate('Gallery')}
        activeOpacity={0.8}
      />

      {/* 그 위에 UI 컴포넌트들 */}
      <SafeAreaView style={styles.overlay} pointerEvents="box-none">
        <StatusBar barStyle="dark-content" translucent backgroundColor="transparent" />

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
        <View style={styles.centerContent} pointerEvents="box-none">
          {/* 말풍선 */}
          <TouchableOpacity
            onPress={() => navigation.navigate('Gallery')}
            activeOpacity={0.8}
          >
            <View style={styles.speechBubble}>
              <Text style={styles.greetingText}>{greeting}</Text>
              <View style={styles.speechBubbleTail} />
            </View>
          </TouchableOpacity>
        </View>

        {/* 하단 캐릭터 설명 */}
        <View style={styles.bottomContent} pointerEvents="box-none">
          <View style={styles.characterLabel}>
            <Text style={styles.characterLabelText}>복실이</Text>
            <Text style={styles.characterSubLabel}>터치해서 대화 시작!</Text>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  dogTouchArea: {
    position: 'absolute',
    bottom: 100,
    left: '15%',
    right: '15%',
    height: '40%',
    // 디버깅용 (확인 후 제거)
    // backgroundColor: 'rgba(255, 0, 0, 0.2)',
  },
  overlay: {
    flex: 1,
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
    backgroundColor: 'rgba(255, 215, 0, 0.9)',
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
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
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
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 40,
  },
  speechBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 20,
    padding: 20,
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
    borderTopColor: 'rgba(255, 255, 255, 0.95)',
  },
  greetingText: {
    fontSize: 22,
    textAlign: 'center',
    color: '#333',
    lineHeight: 32,
  },
  bottomContent: {
    paddingBottom: 30,
    alignItems: 'center',
  },
  characterLabel: {
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 15,
  },
  characterLabelText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  characterSubLabel: {
    fontSize: 16,
    color: '#666',
    marginTop: 5,
  },
});

export default HomeScreen;
