import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';
import { colors, fonts, commonStyles } from '../theme';
import { authService } from '../api/auth';

// 웹 브라우저 리다이렉트 완료 처리
WebBrowser.maybeCompleteAuthSession();

// 카카오 설정
const KAKAO_CLIENT_ID = '09f5e1996f1e5e77c78e9299e805bca5';
const KAKAO_CLIENT_SECRET = 'SxGpt6ZxHaMeR3HGsh2oGrCleBalLPf1';

const LoginScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(false);

  // 플랫폼별 Redirect URI 설정
  const redirectUri = 'http://54.180.28.75:8000/auth/kakao/callback';

  useEffect(() => {
    console.log('Redirect URI:', redirectUri);
    console.log('Platform:', Platform.OS);
  }, []);

  // 카카오 로그인 처리
  const handleKakaoLogin = async () => {
    try {
      setLoading(true);

      // 카카오 OAuth URL
      const authUrl =
        `https://kauth.kakao.com/oauth/authorize?` +
        `client_id=${KAKAO_CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&response_type=code`;

      console.log('Auth URL:', authUrl);

      // 웹 브라우저로 카카오 로그인 페이지 열기
      const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUri);

      console.log('Auth Result:', result);

      // ✅ 수정 포인트: success가 아니더라도 url이 있다면 처리하도록 변경
      if (result.url) {
        // URL에서 인가 코드 추출 (좀 더 확실한 정규식 방식 사용)
        const codeMatch = result.url.match(/[?&]code=([^&]+)/);
        const code = codeMatch ? codeMatch[1] : null;

        if (code) {
          console.log('✅ 가로챈 카카오 인가 코드:', code);

          // 여기서부터는 기존 토큰 교환 로직과 동일
          const tokenResponse = await fetch('https://kauth.kakao.com/oauth/token', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `grant_type=authorization_code&client_id=${KAKAO_CLIENT_ID}&client_secret=${KAKAO_CLIENT_SECRET}&redirect_uri=${encodeURIComponent(redirectUri)}&code=${code}`,
          });

          const tokenData = await tokenResponse.json();
          console.log('카카오 토큰 응답:', tokenData);

          if (tokenData.access_token) {
            console.log('EC2 서버로 토큰 전송 중...');
            const serverResponse = await authService.kakaoLogin(tokenData.access_token);
            console.log('서버 최종 응답:', serverResponse);

            Alert.alert('로그인 성공', `환영합니다!`);
            navigation.replace('Home');
          } else {
            console.error('토큰 에러:', tokenData);
            Alert.alert('로그인 실패', '카카오 토큰 발급에 실패했습니다.');
          }
        }
      } else if (result.type === 'dismiss') {
        // ✅ dismiss인데 url이 없는 경우에 대한 안내
        console.log('로그인 창이 그냥 닫혔습니다. (URL 없음)');
        Alert.alert('알림', '로그인 과정이 비정상적으로 종료되었습니다. 다시 시도해 주세요.');
      }
    } catch (error) {
      console.error('카카오 로그인 에러:', error);
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
          activeOpacity={0.8}
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
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 40,
  },
  logoImage: {
    width: 380,
    height: 380,
    marginTop: 30,
    alignSelf: 'center',
  },
  textContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: fonts.sizes.title,
    color: colors.text,
    marginBottom: 10,
  },
  subtitle: {
    fontFamily: fonts.regular,
    fontSize: fonts.sizes.large,
    color: colors.textLight,
  },
  footer: {
    paddingHorizontal: 30,
    paddingBottom: 60,
  },
  kakaoButton: {
    backgroundColor: colors.primary,
    height: 60,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  kakaoButtonText: {
    fontFamily: fonts.bold,
    fontSize: fonts.sizes.large,
    color: '#3C1E1E',
  },
});

export default LoginScreen;
