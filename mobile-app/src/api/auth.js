import api, { setToken, getToken, clearToken } from './config';

export const authService = {
  // 카카오 로그인
  async kakaoLogin(kakaoAccessToken) {
    const data = await api.post('/auth/kakao', {
      kakao_access_token: kakaoAccessToken,
    });

    // JWT 토큰 저장 (메모리)
    await setToken(data.access_token);

    return data;
  },

  // 현재 사용자 정보 조회
  async getMe() {
    return await api.get('/auth/me');
  },

  // 저장된 토큰 확인
  async getToken() { // ✅ 여기에 async 추가
    return await getToken(); // ✅ 호출할 때도 await 권장
  },

  // 로그아웃
  async logout() {
    try {
      console.log('🧹 AsyncStorage 토큰 삭제 중...');
      
      // ✅ 서버에도 로그아웃 알림 보내기 (선택 사항)
      // 이 요청을 보내면 EC2 로그에 "POST /auth/logout"이 찍힙니다.
      await api.post('/auth/logout'); 
      
      await clearToken(); 
    } catch (error) {
      console.error('서버 로그아웃 요청 실패:', error);
      // 서버 요청이 실패하더라도 클라이언트 토큰은 지워야 합니다.
      await clearToken();
    }
  },

  // 토큰 갱신
  async refreshToken() {
    const data = await api.post('/auth/refresh', {});
    setToken(data.access_token);
    return data;
  },
};

export default authService;
