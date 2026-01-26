# 🔍 PyAV 문제 해결 과정 전체 정리

## 📋 타임라인 및 시도 내역

### ❌ 시도 1: PyAV 11.0.0 직접 설치
**문제**: `AV_CODEC_CAP_OTHER_THREADS undeclared` 컴파일 에러
**원인**: PyAV 11.0.0은 FFmpeg 5.0+ API 사용, EC2는 FFmpeg 4.2.7
**결론**: FFmpeg 버전 불일치

### ❌ 시도 2: PyAV 9.2.0 다운그레이드
**문제**: Cython 빌드 실패, 다른 컴파일 에러
**원인**: 구버전 PyAV도 Cython 3.x와 호환 문제
**결론**: 버전 다운그레이드로 해결 불가

### ❌ 시도 3: FFmpeg 업그레이드 시도
**문제**: 논리적 모순 (사용자가 지적)
**원인**: Ubuntu 20.04 기본 저장소는 FFmpeg 4.2.7까지만 제공
**결론**: 시스템 FFmpeg 업그레이드는 리스크 높음

### ❌ 시도 4: PyAV 완전 제거
**문제**: 여전히 빌드 실패 (Conda 경로 발견)
**원인**: `/opt/conda` 경로로 인한 Conda/venv 환경 충돌
**결론**: 환경 충돌이 근본 원인 중 하나

### ❌ 시도 5: PyAV 10.0.0 (FFmpeg 4.x 호환)
**문제**: Cython 컴파일 에러 (`noexcept` 문법)
**원인**: Conda의 Cython 3.x + PyAV 오래된 코드
**결론**: Cython 버전 호환 문제

### ❌ 시도 6: TTS 버전 다운그레이드 (0.14.3)
**문제**: RunPod과 버전 불일치 (0.21.3 → 0.14.3)
**원인**: 잘못된 가정 (PyPI만 확인)
**결론**: RunPod은 GitHub에서 설치했음

---

## ✅ 최종 해결: 근본 원인 파악

### 🔍 핵심 발견
1. **RunPod은 Docker 환경** (`/app/` 경로)
2. **EC2는 베어메탈 Ubuntu** (`/home/ubuntu/` 경로)
3. **Worker 코드가 Docker 전용 경로 하드코딩**
4. **Conda와 venv 동시 활성화** (컴파일 충돌)

### 🎯 해결 방법
1. **경로 동적 설정**: `settings.models_root` 추가 (환경별 자동 선택)
2. **Conda 완전 제거**: PATH에서 Conda 제거, python3-venv 사용
3. **PyAV 제외**: EC2는 soundfile 사용 (TTS가 자동 선택)
4. **TTS GitHub 설치**: RunPod과 동일하게 v0.21.3
5. **환경변수 추가**: `MODELS_ROOT` 설정

---

## 🧠 배운 교훈

### 1. 환경 차이의 중요성
- **Docker vs 베어메탈**: 경로, 의존성, 패키지 관리 방식 모두 다름
- **하드코딩 금지**: 환경변수로 동적 설정 필수

### 2. 의존성 계층 이해
- **필수 vs 선택적**: TTS는 PyAV 없이도 작동 (soundfile, librosa 우선)
- **백엔드 자동 선택**: TTS가 환경에 맞게 오디오 백엔드 자동 선택

### 3. 컴파일 환경 충돌
- **Conda + venv 혼재**: 헤더 파일 경로 충돌, 라이브러리 버전 충돌
- **PATH 관리**: 환경 분리가 핵심

### 4. 버전 관리
- **PyPI vs GitHub**: 최신 버전이 GitHub에만 있을 수 있음
- **환경 일관성**: RunPod 설치 방법 확인 필수

---

## 📈 진보 과정

### Phase 1: 증상 치료 (실패)
- PyAV 버전 변경
- FFmpeg 업그레이드 시도
- 단순 제거 시도

### Phase 2: 근본 원인 탐색
- Conda 경로 발견
- Docker vs 베어메탈 환경 차이 인식
- Worker 코드 분석

### Phase 3: 시스템적 해결
- 경로 동적 설정
- 환경 분리 (Conda 제거)
- 의존성 최적화 (PyAV 제외)
- RunPod 호환성 유지

---

## ✅ 최종 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Upstash Redis                        │
│              (rediss://...?ssl_cert_reqs)               │
└────────────┬─────────────────────────┬──────────────────┘
             │                         │
        ┌────▼────┐              ┌────▼────┐
        │   EC2   │              │ RunPod  │
        │ FastAPI │              │ Celery  │
        │         │              │ Worker  │
        ├─────────┤              ├─────────┤
        │Ubuntu20 │              │ Docker  │
        │Python310│              │CUDA+GPU │
        │FFmpeg4.2│              │FFmpeg최신│
        │soundfile│              │PyAV 11.0│
        │TTS 0.21 │              │TTS 0.21 │
        │PyAV ❌  │              │PyAV ✅  │
        └─────────┘              └─────────┘
     /home/ubuntu/                /app/
```

---

## 🎓 핵심 원칙

1. **환경 특성 파악 먼저**: Docker vs 베어메탈, GPU vs CPU
2. **하드코딩 금지**: 모든 경로/설정 환경변수화
3. **의존성 최소화**: 필수가 아니면 제거 (PyAV)
4. **환경 일관성**: 한 환경에서 작동하면, 다른 환경도 동일 방식으로
5. **환경 분리**: Conda와 venv 절대 혼용 금지

---

## 📚 참고 자료

- **TTS 백엔드 우선순위**: soundfile > librosa > PyAV > audioread
- **PyAV 호환성**: FFmpeg 버전에 따라 PyAV 버전 다름
- **Cython 버전**: PyAV < 11.0은 Cython 3.x 비호환
- **Conda 경로 충돌**: `/opt/conda` vs `/usr/` 경로 우선순위

---

## 🚀 다음 단계

1. ✅ EC2 환경 설정 완료
2. ✅ RunPod과 호환성 유지
3. ⏳ FastAPI 서버 실행 테스트
4. ⏳ Celery 태스크 연동 테스트
5. ⏳ 전체 플로우 검증 (STT → Brain → TTS)
