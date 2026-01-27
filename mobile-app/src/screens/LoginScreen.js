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
import { colors, fonts, commonStyles } from '../theme';
import { authService } from '../api/auth';
import { API_BASE_URL } from '../api/config';

const LoginScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    try {
      setLoading(true);

      // 테스트용: 서버 연결 확인 후 바로 홈으로 이동
      // 실제 카카오 로그인은 expo-auth-session 또는 WebBrowser 사용
      const response = await fetch(`${API_BASE_URL}/`);

      if (response.ok) {
        console.log('서버 연결 성공');
        // TODO: 실제 카카오 로그인 구현
        // 지금은 테스트를 위해 바로 홈으로 이동
        navigation.replace('Home');
      } else {
        Alert.alert('연결 실패', '서버에 연결할 수 없습니다.');
      }
    } catch (error) {
      console.error('로그인 실패:', error);
      Alert.alert('연결 실패', '서버에 연결할 수 없습니다.\n' + error.message);
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
          onPress={handleLogin}
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
