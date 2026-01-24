"""
Coqui XTTS v2 음성 프리셋
MVP에서 사용할 기본 목소리 설정
"""

# Coqui XTTS v2 기본 제공 음성 샘플 경로
# (실제 경로는 XTTS 모델 다운로드 후 확인 필요)
VOICE_PRESETS = {
    "warm_female": {
        "speaker_wav": None,  # XTTS 기본 음성 사용 (None이면 기본값)
        "language": "ko",
        "emotion": "warm",  # 따뜻한 톤
        "description": "따뜻한 여성 (손녀 느낌)"
    },
    "soft_male": {
        "speaker_wav": None,
        "language": "ko",
        "emotion": "soft",  # 부드러운 톤
        "description": "부드러운 남성 (손자 느낌)"
    },
    "bright_female": {
        "speaker_wav": None,
        "language": "ko",
        "emotion": "bright",  # 밝은 톤
        "description": "밝은 여성 (활기찬)"
    },
}


def get_voice_preset(voice_id: str = "warm_female"):
    """
    음성 프리셋 조회
    
    Args:
        voice_id: 음성 ID (warm_female, soft_male, bright_female)
    
    Returns:
        dict: 음성 설정 정보
    """
    return VOICE_PRESETS.get(voice_id, VOICE_PRESETS["warm_female"])
