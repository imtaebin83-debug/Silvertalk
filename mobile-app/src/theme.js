/**
 * SilverTalk 전역 테마 설정
 * 색상, 폰트 등을 여기서 한번에 관리합니다.
 */

// 색상 팔레트
export const colors = {
  // 기본 배경색
  background: '#EAEAEA',

  // 주요 색상
  primary: '#FFD700',      // 골드 (버튼, 헤더 등)
  secondary: '#FFA500',    // 오렌지

  // 텍스트 색상
  text: '#333333',
  textLight: '#666666',
  textWhite: '#FFFFFF',

  // UI 요소
  white: '#FFFFFF',
  card: 'rgba(255, 255, 255, 0.95)',
  overlay: 'rgba(255, 255, 255, 0.8)',
  shadow: '#000000',
};

// 폰트 설정
export const fonts = {
  // 폰트 패밀리 (App.js에서 로드한 이름과 동일해야 함)
  regular: 'KyoboHandwriting',
  bold: 'KyoboHandwriting',

  // 폰트 크기
  sizes: {
    small: 14,
    medium: 16,
    large: 18,
    xlarge: 22,
    xxlarge: 24,
    title: 32,
  },

  // 줄 간격
  lineHeights: {
    small: 18,
    medium: 22,
    large: 28,
    xlarge: 32,
  },
};

// 공통 스타일
export const commonStyles = {
  shadow: {
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 20,
    padding: 20,
  },
};

// React Navigation 테마
export const navigationTheme = {
  dark: false,
  colors: {
    primary: colors.primary,
    background: colors.background,
    card: colors.white,
    text: colors.text,
    border: colors.background,
    notification: colors.primary,
  },
};

export default {
  colors,
  fonts,
  commonStyles,
  navigationTheme,
};
