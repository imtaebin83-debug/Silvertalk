/**
 * 갤러리 동기화 유틸리티
 * MVP: 초기 1회 메타데이터 동기화
 */
import * as MediaLibrary from 'expo-media-library';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'http://localhost:8000';  // 환경별 설정 필요

/**
 * 갤러리 메타데이터 동기화 (초기 1회)
 * 
 * Flow:
 * 1. 권한 요청
 * 2. 로컬 갤러리 스캔 (EXIF 파싱)
 * 3. 메타데이터만 서버 전송 (사진 원본은 로컬 유지)
 * 4. 동기화 완료 표시 저장
 */
export const syncGalleryMetadata = async (kakaoId) => {
  try {
    // 이미 동기화 완료 확인
    const syncCompleted = await AsyncStorage.getItem('gallery_sync_completed');
    if (syncCompleted === 'true') {
      console.log('✅ 갤러리 이미 동기화됨');
      return { success: true, message: '이미 동기화됨' };
    }

    // 1. 권한 요청
    const { status } = await MediaLibrary.requestPermissionsAsync();
    if (status !== 'granted') {
      throw new Error('갤러리 접근 권한이 필요합니다.');
    }

    console.log('📷 갤러리 스캔 시작...');

    // 2. 갤러리 사진 조회 (최대 1000장, MVP)
    const photos = await MediaLibrary.getAssetsAsync({
      mediaType: 'photo',
      first: 1000,
      sortBy: MediaLibrary.SortBy.creationTime,
    });

    console.log(`📸 총 ${photos.assets.length}장 발견`);

    // 3. 메타데이터 추출
    const metadata = await Promise.all(
      photos.assets.map(async (photo) => {
        // EXIF 정보 가져오기
        const assetInfo = await MediaLibrary.getAssetInfoAsync(photo.id);

        return {
          local_uri: photo.uri,                 // 로컬 경로
          taken_at: photo.creationTime,         // EXIF 날짜
          location_name: assetInfo.location?.city || null,
          latitude: assetInfo.location?.latitude || null,
          longitude: assetInfo.location?.longitude || null,
        };
      })
    );

    console.log('🚀 서버로 메타데이터 전송 중...');

    // 4. 서버로 메타데이터 전송 (배치 처리)
    const response = await axios.post(
      `${API_BASE_URL}/photos/sync-metadata`,
      {
        kakao_id: kakaoId,
        metadata: metadata,
      },
      {
        timeout: 60000,  // 60초 타임아웃
      }
    );

    console.log('✅ 동기화 완료:', response.data);

    // 5. 동기화 완료 표시
    await AsyncStorage.setItem('gallery_sync_completed', 'true');
    await AsyncStorage.setItem('last_sync_time', new Date().toISOString());

    return {
      success: true,
      count: metadata.length,
      message: '갤러리가 동기화되었습니다.',
    };

  } catch (error) {
    console.error('❌ 갤러리 동기화 실패:', error);
    
    return {
      success: false,
      message: error.message || '동기화에 실패했습니다.',
    };
  }
};

/**
 * 동기화 재실행 (설정 화면에서 호출)
 */
export const resyncGallery = async (kakaoId) => {
  // 동기화 완료 플래그 제거
  await AsyncStorage.removeItem('gallery_sync_completed');
  return await syncGalleryMetadata(kakaoId);
};

/**
 * 동기화 상태 확인
 */
export const checkSyncStatus = async () => {
  const completed = await AsyncStorage.getItem('gallery_sync_completed');
  const lastSyncTime = await AsyncStorage.getItem('last_sync_time');

  return {
    completed: completed === 'true',
    lastSyncTime: lastSyncTime || null,
  };
};
