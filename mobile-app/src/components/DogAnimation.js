/**
 * 강아지(복실이) 애니메이션 컴포넌트
 * 감정 상태에 따른 이모지/텍스트 애니메이션
 */
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
} from 'react-native';
import { colors, fonts } from '../theme';

/**
 * 감정별 설정
 */
const EMOTION_CONFIG = {
  neutral: {
    emoji: '🐕',
    message: '복실이가 듣고 있어요',
    color: colors.primary || '#FFD700',
  },
  happy: {
    emoji: '🐕‍🦺',
    message: '복실이가 기뻐해요!',
    color: '#4CAF50',
  },
  sad: {
    emoji: '🐶',
    message: '복실이가 공감해요',
    color: '#5C6BC0',
  },
  excited: {
    emoji: '🦮',
    message: '복실이가 신나해요!',
    color: '#FF9800',
  },
  thinking: {
    emoji: '🐕',
    message: '복실이가 생각 중...',
    color: '#9E9E9E',
  },
  listening: {
    emoji: '🐕',
    message: '복실이가 듣고 있어요...',
    color: '#2196F3',
  },
};

/**
 * DogAnimation 컴포넌트
 * @param {Object} props
 * @param {string} props.emotion - 감정 상태 (neutral, happy, sad, excited, thinking, listening)
 * @param {boolean} props.isAnimating - 애니메이션 활성화 여부
 * @param {string} props.customMessage - 커스텀 메시지 (선택)
 */
const DogAnimation = ({ 
  emotion = 'neutral', 
  isAnimating = false,
  customMessage = null,
}) => {
  const config = EMOTION_CONFIG[emotion] || EMOTION_CONFIG.neutral;
  const [bounceAnim] = React.useState(new Animated.Value(0));

  React.useEffect(() => {
    if (isAnimating) {
      // 바운스 애니메이션
      Animated.loop(
        Animated.sequence([
          Animated.timing(bounceAnim, {
            toValue: -10,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(bounceAnim, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      bounceAnim.setValue(0);
    }
  }, [isAnimating, bounceAnim]);

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.emojiContainer,
          {
            backgroundColor: config.color,
            transform: [{ translateY: bounceAnim }],
          },
        ]}
      >
        <Text style={styles.emoji}>{config.emoji}</Text>
      </Animated.View>
      <Text style={styles.message}>
        {customMessage || config.message}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    padding: 20,
  },
  emojiContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  emoji: {
    fontSize: 40,
  },
  message: {
    marginTop: 12,
    fontSize: fonts?.sizes?.medium || 16,
    fontFamily: fonts?.regular || undefined,
    color: colors?.text || '#333',
    textAlign: 'center',
  },
});

export default DogAnimation;
