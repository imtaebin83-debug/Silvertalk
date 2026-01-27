// EC2 서버 주소 (HTTPS)
export const API_BASE_URL = 'http://54.180.28.75:8000';

// 메모리에 토큰 저장 (앱 재시작 시 초기화됨)
let accessToken = null;

export const setToken = (token) => {
  accessToken = token;
};

export const getToken = () => {
  return accessToken;
};

export const clearToken = () => {
  accessToken = null;
};

// fetch 래퍼 함수
const api = {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    // 기본 헤더
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // JWT 토큰 추가
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    return response;
  },

  async get(endpoint) {
    const response = await this.request(endpoint, { method: 'GET' });
    return response.json();
  },

  async post(endpoint, data) {
    const response = await this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.json();
  },

  async put(endpoint, data) {
    const response = await this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return response.json();
  },

  async delete(endpoint) {
    const response = await this.request(endpoint, { method: 'DELETE' });
    return response.json();
  },
};

export default api;
