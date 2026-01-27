import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_BASE_URL = 'http://54.180.28.75:8000';

// ✅ 비동기 방식으로 토큰 저장
export const setToken = async (token) => {
  await AsyncStorage.setItem('userToken', token);
};

// ✅ 비동기 방식으로 토큰 가져오기
export const getToken = async () => {
  return await AsyncStorage.getItem('userToken');
};

// ✅ 비동기 방식으로 토큰 삭제
export const clearToken = async () => {
  await AsyncStorage.removeItem('userToken');
};

const api = {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // ✅ 저장소에서 실시간으로 토큰 확인
    const token = await getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // 401 에러(토큰 만료) 처리 로직을 여기에 추가할 수 있습니다.
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
