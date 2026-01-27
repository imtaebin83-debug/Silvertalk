import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';
import { colors, fonts, commonStyles } from '../theme';
import { authService } from '../api/auth';

// 인증 세션 완료 처리
WebBrowser.maybeCompleteAuthSession();

const KAKAO_CLIENT_ID = '09f5e1996f1e5e77c78e9299e805bca5';
const KAKAO_CLIENT_SECRET = 'SxGpt6ZxHaMeR3HGsh2oGrCleBalLPf1';

const LoginScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(false);

  // 서버의 콜백 주소 (카카오 설정에 등록된 것과 동일해야 함)
  const redirectUri = 'http://54.180.28.75:8000/auth/kakao/callback';

  const handleKakaoLogin = async () => {
    try {
      setLoading(true);

      // 1. 카카오 로그인 페이지 주소
      const authUrl =
        `https://kauth.kakao.com/oauth/authorize?` +
        `client_id=${KAKAO_CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&response_type=code`;

      // 2. 앱이 다시 돌아와야 할 딥링크 주소 (app.json의 scheme 기반)
      const returnUrl = AuthSession.makeRedirectUri({
        scheme: 'silvertalk',
        path: 'auth',
      });

      console.log('🔗 인증 시도 URL:', authUrl);
      console.log('🎯 기다리는 리턴 URL:', returnUrl);

      // 3. 브라우저 세션 시작
      const result = await WebBrowser.openAuthSessionAsync(authUrl, returnUrl);

      console.log('📊 브라우저 결과:', result);

      if (result.type === 'success' && result.url) {
        // 4. 리다이렉트된 URL에서 인가 코드 추출
        const codeMatch = result.url.match(/[?&]code=([^&]+)/);
        const code = codeMatch ? codeMatch[1] : null;

        if (code) {
          console.log('✅ 인가 코드 획득:', code);

          // 5. 카카오 토큰 교환 (인가 코드 -> 액세스 토큰)
          const tokenResponse = await fetch('https://kauth.kakao.com/oauth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `grant_type=authorization_code&client_id=${KAKAO_CLIENT_ID}&client_secret=${KAKAO_CLIENT_SECRET}&redirect_uri=${encodeURIComponent(redirectUri)}&code=${code}`,
          });

          const tokenData = await tokenResponse.json();

          if (tokenData.access_token) {
            console.log('🚀 서버로 토큰 전송 중...');
            const serverResponse = await authService.kakaoLogin(tokenData.access_token);
            
            Alert.alert('로그인 성공', '반가워요! 복실이가 기다리고 있었어요.');
            navigation.replace('Home');
          } else {
            throw new Error('카카오 토큰 발급에 실패했습니다.');
          }
        }
      } else if (result.type === 'dismiss') {
        Alert.alert('알림', '로그인 창이 닫혔습니다.');
      }
    } catch (error) {
      console.error('❌ 로그인 에러:', error);
      Alert.alert('로그인 실패', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.textContainer}>
          <Text style={styles.title}>실버톡</Text>
          <Text style={styles.subtitle}>복실이가 할머니를 기다리고 있어요!</Text>
        </View>
        <Image
          source={require('../../assets/dog_nukki.png')}
          style={styles.logoImage}
          resizeMode="contain"
        />
      </View>
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.kakaoButton, commonStyles.shadow]}
          onPress={handleKakaoLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#3C1E1E" />
          ) : (
            <Text style={styles.kakaoButtonText}>카카오톡으로 시작하기</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 40 },
  logoImage: { width: 380, height: 380, marginTop: 30, alignSelf: 'center' },
  textContainer: { alignItems: 'center', marginBottom: 20 },
  title: { fontFamily: fonts.bold, fontSize: fonts.sizes.title, color: colors.text, marginBottom: 10 },
  subtitle: { fontFamily: fonts.regular, fontSize: fonts.sizes.large, color: colors.textLight },
  footer: { paddingHorizontal: 30, paddingBottom: 60 },
  kakaoButton: { backgroundColor: colors.primary, height: 60, borderRadius: 15, justifyContent: 'center', alignItems: 'center' },
  kakaoButtonText: { fontFamily: fonts.bold, fontSize: fonts.sizes.large, color: '#3C1E1E' },
});

export default LoginScreen;