/**
 * SilverTalk Mobile App
 * 반려견 AI와 함께하는 회상 치료 서비스
 */
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

// 화면 컴포넌트
import HomeScreen from './src/screens/HomeScreen';
import GalleryScreen from './src/screens/GalleryScreen';
import ChatScreen from './src/screens/ChatScreen';
import VideoGalleryScreen from './src/screens/VideoGalleryScreen';
import ChatHistoryScreen from './src/screens/ChatHistoryScreen';
import ChatHistoryDetailScreen from './src/screens/ChatHistoryDetailScreen';
import ProfileScreen from './src/screens/ProfileScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerStyle: {
            backgroundColor: '#FFD700',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
            fontSize: 24,
          },
          headerTitleAlign: 'center',
        }}
      >
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
