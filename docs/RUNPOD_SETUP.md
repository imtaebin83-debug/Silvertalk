# RunPod Pods 생성 가이드 (RTX 3090)

## 1. Pods 메뉴 선택
```
RunPod Dashboard > Pods > Deploy
```

## 2. GPU 선택
```
Filter:
- GPU Type: RTX 3090
- vRAM: 24GB
- Region: Any (가용성 있는 곳)
- Price: Community Cloud 선택 (저렴)

정렬: Price (낮은 순)

선택: RTX 3090 24GB @ $0.34-0.44/hr
```

## 3. Container 설정

### Base Docker Image
```
Template: PyTorch (추천)
또는
Custom Image: pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime

이유:
- PyTorch 2.1.2 사전 설치
- CUDA 11.8 호환
- 우리 Dockerfile과 동일
```

### Container Disk (로컬 스토리지)
```
Disk Size: 50GB (권장)

저장 내용:
- AI 모델 (Whisper: 3GB, XTTS: 1.8GB)
- 코드
- 임시 파일
```

### Volume (영구 스토리지) - 선택
```
Network Volume: 생성 안 함
(4일만 사용이므로 불필요)
```

### Ports (중요!)
```
Expose HTTP Ports:
- Port: 6379 (Redis용, 사실상 불필요)
- Port: 5555 (Flower 모니터링)

Expose TCP Ports:
- 추가 안 함
```

### Environment Variables
```
나중에 SSH 접속 후 .env 파일로 설정
지금은 비워둠
```

## 4. Deploy 클릭

```
Status: Starting...
→ Provisioning...
→ Running ✅

시간: 2-5분 소요
```

## 5. SSH 접속 정보 확인

```
Pod 상세 페이지:

SSH Access:
ssh root@<pod-id>.proxy.runpod.net -p 12345 -i ~/.ssh/id_rsa

또는

Password Access:
ssh root@<pod-id>.proxy.runpod.net -p 12345
Password: (자동 생성)
```

## 6. 비용 체크
```
Hourly: $0.34-0.44
Daily (24시간): $8-10
4일 총: $32-40

필요 시 시작/종료:
- Stop Pod: 비용 중단
- Start Pod: 재시작 (데이터 유지)
- 모델은 재다운로드 필요 (5-10분)
```

## 7. Pod 관리 팁

### 중지 (비용 절감)
```
Pod 우측 > Stop
→ 시간당 비용 중단
→ 디스크 데이터 유지 (24시간)
→ 24시간 후 자동 삭제
```

### 재시작
```
Pod 우측 > Start
→ 몇 분 소요
→ 모델 재다운로드 필요
```

### 삭제
```
Pod 우측 > Terminate
→ 모든 데이터 삭제
→ 비용 완전 중단
```

## 8. 모니터링

```
Pod 대시보드:
- GPU 사용률: 0-100%
- VRAM 사용량: /24GB
- CPU 사용률
- Network I/O

알림:
- GPU 100% 유지 → AI 작업 진행 중
- GPU 0% → 대기 상태 (비용 낭비)
```

## 9. 보안 설정

### SSH Key 등록 (선택)
```
Profile > SSH Keys > Add Key

공개키 등록 시:
- 비밀번호 불필요
- 더 안전
```

### Firewall (기본 설정)
```
RunPod이 자동으로 보호
- SSH: 22/tcp 허용
- HTTP: 80/tcp 허용
- Custom Ports: 수동 허용
```

## 10. 문제 해결

### Q: Pod이 바로 중지됨
```
A: 가용성 부족
→ 다른 리전 선택
→ Community Cloud 대신 Secure Cloud 시도
```

### Q: SSH 접속 안 됨
```
A: 몇 분 대기 (Provisioning)
A: 비밀번호 복사 정확히
```

### Q: GPU 인식 안 됨
```
A: nvidia-smi 실행 확인
A: CUDA_VISIBLE_DEVICES 환경 변수 확인
```

## 다음 단계
```
1. SSH 접속
2. 코드 클론
3. 환경 변수 설정
4. Docker 컨테이너 실행
5. Celery Worker 시작
```