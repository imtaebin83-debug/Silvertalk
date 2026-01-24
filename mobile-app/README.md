# SilverTalk Mobile App

React Native Expo 기반 모바일 애플리케이션

## 🚀 시작하기

### 1. 의존성 설치

```bash
cd mobile-app
npm install
```

### 2. 앱 실행

```bash
# Expo 개발 서버 시작
npm start

# Android 실행
npm run android

# iOS 실행 (Mac만 가능)
npm run ios
```

### 3. 백엔드 API 연결

`src/config/api.js` 파일을 생성하고 백엔드 URL을 설정하세요:

```javascript
export const API_BASE_URL = 'http://localhost:8000';
// 또는 실제 서버 주소
// export const API_BASE_URL = 'https://api.silvertalk.com';
```

## 📱 주요 화면

1. **HomeScreen**: 강아지 메인 화면
2. **GalleryScreen**: 사진 선택 화면 (랜덤 6장)
3. **ChatScreen**: 무전기 방식 대화 화면
4. **VideoGalleryScreen**: 추억 극장 (생성된 영상 목록)

## 🎨 디자인 원칙

### 어르신 친화적 UI
- **큰 글씨**: 최소 20px 이상
- **큰 버튼**: 터치 영역 최소 60x60px
- **고대비 색상**: 가독성 향상
- **단순한 네비게이션**: 최대 2depth

### 색상 팔레트
- 주요 색상: `#FFD700` (골드)
- 보조 색상: `#FFA500` (오렌지)
- 배경: `#FFF8DC` (따뜻한 크림색)
- 텍스트: `#333333` (진한 회색)

## 📦 주요 라이브러리

- `expo-av`: 음성 녹음/재생
- `expo-media-library`: 갤러리 접근
- `expo-calendar`: 캘린더 접근
- `@react-navigation`: 화면 네비게이션
- `axios`: HTTP 요청

## 🔧 개발 팁

### API 호출 예제

```javascript
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

// 강아지 인사 메시지 받기
const fetchGreeting = async (kakaoId) => {
  const response = await axios.get(`${API_BASE_URL}/home/greeting`, {
    params: { kakao_id: kakaoId }
  });
  return response.data;
};
```

### 음성 녹음 권한 요청

```javascript
import { Audio } from 'expo-av';

const requestAudioPermission = async () => {
  const { status } = await Audio.requestPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('권한 필요', '마이크 권한이 필요합니다.');
    return false;
  }
  return true;
};
```

## 🐛 트러블슈팅

### 권한 오류
Android: `android/app/src/main/AndroidManifest.xml`에 권한 추가
iOS: `Info.plist`에 권한 설명 추가

### Metro Bundler 오류
```bash
npx expo start --clear
```

## 📝 TODO
- [ ] 카카오 로그인 SDK 연동
- [ ] 갤러리 EXIF 파싱 구현
- [ ] 캘린더 동기화 구현
- [ ] 음성 녹음 및 전송 구현
- [ ] 영상 플레이어 구현
- [ ] 카카오톡 공유 기능
- [ ] 강아지 애니메이션 에셋 추가
