import api, { setToken, getToken, clearToken } from './config';

export const authService = {
  // 카카오 로그인
  async kakaoLogin(kakaoAccessToken) {
    const data = await api.post('/auth/kakao', {
      kakao_access_token: kakaoAccessToken,
    });

    // JWT 토큰 저장 (메모리)
    setToken(data.access_token);

    return data;
  },

  // 현재 사용자 정보 조회
  async getMe() {
    return await api.get('/auth/me');
  },

  // 저장된 토큰 확인
  getToken() {
    return getToken();
  },

  // 로그아웃
  logout() {
    clearToken();
  },

  // 토큰 갱신
  async refreshToken() {
    const data = await api.post('/auth/refresh', {});
    setToken(data.access_token);
    return data;
  },
};

export default authService;
