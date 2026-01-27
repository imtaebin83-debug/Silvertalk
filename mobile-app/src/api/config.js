// EC2 서버 주소
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

// ============================================================
// FormData 업로드 (음성 파일 전송용)
// ============================================================
export const uploadFormData = async (endpoint, formData) => {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {};
  
  // JWT 토큰 추가
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Content-Type은 자동 설정 (multipart/form-data)
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });
  
  return response.json();
};

// ============================================================
// Task Polling (1초 간격, 60초 타임아웃)
// ============================================================
export const pollTaskResult = async (taskId, options = {}) => {
  const {
    interval = 1000,      // 1초 간격
    timeout = 60000,      // 60초 타임아웃
    onProgress = null,    // 진행 콜백
  } = options;
  
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const result = await api.get(`/api/task/${taskId}`);
      
      // 진행 콜백 호출
      if (onProgress) {
        onProgress(result);
      }
      
      // 완료 또는 실패 시 반환
      if (result.status === 'SUCCESS') {
        return { success: true, data: result };
      }
      
      if (result.status === 'FAILURE') {
        return { success: false, error: result.error || '처리 실패' };
      }
      
      // 아직 처리 중이면 대기
      await new Promise(resolve => setTimeout(resolve, interval));
      
    } catch (error) {
      console.error('Polling error:', error);
      return { success: false, error: error.message };
    }
  }
  
  // 타임아웃
  return { success: false, error: '처리 시간이 초과되었습니다.' };
};
