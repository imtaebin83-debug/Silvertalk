/**
 * SilverTalk 전역 테마 설정
 * "Warm Photo Album" 컨셉 - 어르신 친화적 UI
 */

// 색상 팔레트 - WCAG AA+ 접근성 준수
export const colors = {
  // 배경색 - Warm Cream (눈의 피로 감소)
  background: '#FFFDF5',

  // 주요 색상
  primary: '#FFB300',      // Amber (구분 가능한 시인성)
  secondary: '#FF8F00',    // Darker Amber

  // 텍스트 색상 - Espresso Dark Brown (고대비, 검정보다 부드러움)
  text: '#3E2723',
  textLight: '#5D4037',
  textWhite: '#FFFFFF',

  // UI 요소
  white: '#FFFFFF',
  card: '#FFFFFF',
  cardShadow: 'rgba(62, 39, 35, 0.12)',
  overlay: 'rgba(255, 253, 245, 0.9)',
  shadow: '#3E2723',

  // 상태 색상
  success: '#43A047',
  error: '#E53935',
  warning: '#FB8C00',

  // 감정 색상 (sentiment)
  sentiment: {
    happy: '#FFD54F',
    sad: '#90CAF9',
    curious: '#CE93D8',
    excited: '#FF8A65',
    nostalgic: '#A1887F',
    comforting: '#81C784',
    neutral: '#BDBDBD',
  },
};

// 폰트 설정 - 가독성 향상
export const fonts = {
  // 제목은 손글씨체 (감성), 본문은 시스템 고딕체 (가독성)
  title: 'KyoboHandwriting',
  body: 'System',  // 시스템 기본 산세리프 (고딕체)

  // 폰트 크기 - 어르신 접근성 고려 (18px+)
  sizes: {
    small: 16,
    medium: 18,
    large: 20,
    xlarge: 24,
    xxlarge: 28,
    title: 36,
  },

  // 줄 간격 - 가독성 향상
  lineHeights: {
    small: 24,
    medium: 28,
    large: 32,
    xlarge: 36,
  },
};

// 공통 스타일
export const commonStyles = {
  shadow: {
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 20,
    padding: 20,
    shadowColor: colors.cardShadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 12,
    elevation: 4,
  },
  // 큰 터치 영역 (어르신 접근성)
  touchableHitSlop: {
    top: 20,
    bottom: 20,
    left: 20,
    right: 20,
  },
};

// 감정 이모지 매핑
export const sentimentEmoji = {
  happy: '😄',
  sad: '🥺',
  curious: '🤔',
  excited: '🎉',
  nostalgic: '🧸',
  comforting: '🤗',
  neutral: '🐕',
  thinking: '💭',
};

// React Navigation 테마
export const navigationTheme = {
  dark: false,
  colors: {
    primary: colors.primary,
    background: colors.background,
    card: colors.white,
    text: colors.text,
    border: 'transparent',
    notification: colors.primary,
  },
};

export default {
  colors,
  fonts,
  commonStyles,
  navigationTheme,
  sentimentEmoji,
};
