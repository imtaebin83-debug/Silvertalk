/**
 * SilverTalk Mobile App
 * 반려견 AI와 함께하는 회상 치료 서비스
 */
import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { useFonts } from 'expo-font';
import { getToken } from './src/api/config';


// 전역 테마
import { colors, fonts, navigationTheme } from './src/theme';

// 화면 컴포넌트
import LoginScreen from './src/screens/LoginScreen'; // 1. 로그인 화면 추가
import HomeScreen from './src/screens/HomeScreen';
import GalleryScreen from './src/screens/GalleryScreen';
import ChatScreen from './src/screens/ChatScreen';
import VideoGalleryScreen from './src/screens/VideoGalleryScreen';
import ChatHistoryScreen from './src/screens/ChatHistoryScreen';
import ChatHistoryDetailScreen from './src/screens/ChatHistoryDetailScreen';
import ProfileScreen from './src/screens/ProfileScreen';

const Stack = createStackNavigator();

export default function App() {
  // 커스텀 폰트 로드
  const [fontsLoaded] = useFonts({
    'KyoboHandwriting': require('./assets/KyoboHandwriting2019.otf'),
  });

  const [isAutoLoginCheck, setIsAutoLoginCheck] = useState(true); // ✅ 자동 로그인 체크 상태
  const [initialRoute, setInitialRoute] = useState('Login'); // ✅ 시작 화면 상태

  useEffect(() => {
    const checkLoginStatus = async () => {
      try {
        const token = await getToken(); // ✅ 저장된 토큰이 있는지 확인
        if (token) {
          setInitialRoute('Home'); // ✅ 토큰이 있으면 시작 화면을 Home으로 설정
        }
      } catch (e) {
        console.error('자동 로그인 체크 에러:', e);
      } finally {
        setIsAutoLoginCheck(false); // ✅ 체크 완료
      }
    };

    checkLoginStatus();
  }, []);

  // 폰트 로딩 중이면 로딩 화면 표시 (이게 Splash 역할을 합니다)
  if (!fontsLoaded || isAutoLoginCheck) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer theme={navigationTheme}>
      <Stack.Navigator
        initialRouteName={initialRoute} // ✅ 확인된 시작 화면 적용
        screenOptions={{
          headerStyle: {
            backgroundColor: '#EAEAEA',
          },
          headerTintColor: colors.text,
          headerTitleStyle: {
            fontFamily: fonts.bold,
            fontSize: fonts.sizes.xxlarge,
          },
          headerTitleAlign: 'center',
          cardStyle: {
            backgroundColor: colors.background,
          },
          headerTitleAlign: 'center',
        }}
      >
        {/* 3. 로그인 화면 등록 (헤더 숨김) */}
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Gallery"
          component={GalleryScreen}
          options={{
            title: '사진 선택',
            headerBackTitle: '뒤로',
          }}
        />
        <Stack.Screen
          name="Chat"
          component={ChatScreen}
          options={{
            title: '대화하기',
            headerBackTitle: '뒤로',
          }}
        />
        <Stack.Screen
          name="VideoGallery"
          component={VideoGalleryScreen}
          options={{
            title: '추억 극장',
            headerBackTitle: '뒤로',
          }}
        />
        <Stack.Screen
          name="ChatHistory"
          component={ChatHistoryScreen}
          options={{
            title: '대화 기록',
            headerBackTitle: '뒤로',
          }}
        />
        <Stack.Screen
          name="ChatHistoryDetail"
          component={ChatHistoryDetailScreen}
          options={{
            title: '대화 상세',
            headerBackTitle: '뒤로',
          }}
        />
        <Stack.Screen
          name="Profile"
          component={ProfileScreen}
          options={{
            title: '프로필',
            headerBackTitle: '뒤로',
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}