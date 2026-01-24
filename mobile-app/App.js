/**
 * SilverTalk Mobile App
 * 반려견 AI와 함께하는 회상 치료 서비스
 */
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

// 화면 컴포넌트 (추후 구현)
// TODO: 화면 컴포넌트 추가
import HomeScreen from './src/screens/HomeScreen';
import GalleryScreen from './src/screens/GalleryScreen';
import ChatScreen from './src/screens/ChatScreen';
import VideoGalleryScreen from './src/screens/VideoGalleryScreen';

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
            fontSize: 24, // 어르신을 위한 큰 글씨
          },
        }}
      >
        <Stack.Screen 
          name="Home" 
          component={HomeScreen} 
          options={{ title: '복실이' }}
        />
        <Stack.Screen 
          name="Gallery" 
          component={GalleryScreen} 
          options={{ title: '사진 선택' }}
        />
        <Stack.Screen 
          name="Chat" 
          component={ChatScreen} 
          options={{ title: '대화하기' }}
        />
        <Stack.Screen 
          name="VideoGallery" 
          component={VideoGalleryScreen} 
          options={{ title: '추억 극장' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
