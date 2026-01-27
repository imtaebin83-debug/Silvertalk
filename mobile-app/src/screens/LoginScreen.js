import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import { colors, fonts, commonStyles } from '../theme';

const LoginScreen = ({ navigation }) => {
    const handleLogin = () => {
      navigation.replace('Home'); 
    };
  
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          {/* 1. 텍스트를 위로 올림 */}
          <View style={styles.textContainer}>
            <Text style={styles.title}>실버톡</Text>
            <Text style={styles.subtitle}>복실이가 할머니를 기다리고 있어요!</Text>
          </View>
  
          {/* 2. 강아지 이미지를 아래로 내림 */}
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
          >
            <Text style={styles.kakaoButtonText}>카카오톡으로 시작하기</Text>
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
      // center에서 flex-start로 바꾸고 paddingTop을 주면 더 세밀하게 상단 위치 조절이 가능해요.
      justifyContent: 'center', 
      alignItems: 'center',
      paddingTop: 40, // 화면 상단에서부터의 여유 공간
    },
    logoImage: {
      width: 380, // 강아지를 조금 더 키워서 존재감을 줬어요.
      height: 380,
      marginTop: 30, // 👈 글씨와 강아지 사이의 간격
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