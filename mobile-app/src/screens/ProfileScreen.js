/**
 * 프로필 화면
 * 설계도 4번: 카카오톡 연동 프로필, 로그아웃 버튼만 존재
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Image,
} from 'react-native';
import { colors, fonts } from '../theme';
import authService from '../api/auth';

const ProfileScreen = ({ navigation }) => {
  const [userInfo, setUserInfo] = useState({
    name: '',
    profileImage: null,
  });

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      // ✅ 2. 서버(/auth/me)에서 내 정보 가져오기
      const data = await authService.getMe(); 
      
      setUserInfo({
        name: data.nickname,
        profileImage: data.profile_image, 
      });
    } catch (error) {
      console.error('내 정보 로드 실패:', error);
      navigation.replace('Login');
    }
  };

  const handleLogout = () => {
    Alert.alert(
      '로그아웃',
      '정말 로그아웃 하시겠어요?',
      [
        { text: '아니요', style: 'cancel' },
        {
          text: '네',
          onPress: async () => { // ✅ async 추가
            try {
              console.log('👋 로그아웃 시도 중...');
              await authService.logout(); // ✅ 토큰 삭제 완료까지 기다림
              
              Alert.alert('알림', '로그아웃 되었습니다.');
              
              // ✅ 네비게이션 스택을 초기화하며 로그인 화면으로 이동
              navigation.reset({
                index: 0,
                routes: [{ name: 'Login' }],
              });
            } catch (error) {
              console.error('로그아웃 에러:', error);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      {/* 프로필 영역 */}
      <View style={styles.profileSection}>
        {/* 프로필 이미지 */}
        <View style={styles.profileImageContainer}>
          {userInfo.profileImage ? (
            <Image
              source={{ uri: userInfo.profileImage }}
              style={styles.profileImage}
            />
          ) : (
            <View style={styles.defaultProfile}>
              <Text style={styles.defaultProfileIcon}>👤</Text>
            </View>
          )}
        </View>

        {/* 사용자 이름 */}
        <Text style={styles.userName}>{userInfo.name}</Text>
        <Text style={styles.userSubText}>카카오톡 계정으로 로그인됨</Text>
      </View>

      {/* 로그아웃 버튼 */}
      <TouchableOpacity
        style={styles.logoutButton}
        onPress={handleLogout}
        activeOpacity={0.8}
      >
        <Text style={styles.logoutButtonText}>로그아웃</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 30,
    paddingTop: 60,
  },
  profileSection: {
    alignItems: 'center',
    marginBottom: 60,
  },
  profileImageContainer: {
    marginBottom: 20,
  },
  profileImage: {
    width: 150,
    height: 150,
    borderRadius: 75,
  },
  defaultProfile: {
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: colors.white,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  defaultProfileIcon: {
    fontSize: 80,
  },
  userName: {
    fontSize: fonts.sizes.title,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  userSubText: {
    fontSize: fonts.sizes.medium,
    fontFamily: fonts.regular,
    color: colors.textLight,
  },
  logoutButton: {
    backgroundColor: '#FF6B6B',
    borderRadius: 15,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  logoutButtonText: {
    fontSize: fonts.sizes.xlarge,
    fontFamily: fonts.bold,
    fontWeight: 'bold',
    color: colors.textWhite,
  },
});

export default ProfileScreen;
