"""
CampusAgent 환경 설정 모듈
- dotenv 기반 환경변수 로딩
- LLM / DB / ChromaDB 등 전역 상수 관리
- OpenAI / Gemini 양쪽 지원
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────
# LLM 설정 (OpenAI 또는 Gemini 자동 감지)
# ──────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# LLM_PROVIDER: "gemini" | "openai" | "none" (자동 감지)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")

# 모델명 (기본값은 provider에 따라 다름)
LLM_MODEL: str = os.getenv("LLM_MODEL", "")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))


def _detect_provider() -> str:
    """사용 가능한 LLM provider 자동 감지"""
    if LLM_PROVIDER != "auto":
        return LLM_PROVIDER
    if GOOGLE_API_KEY:
        return "gemini"
    if OPENAI_API_KEY:
        return "openai"
    return "none"


def get_llm_provider() -> str:
    """현재 LLM provider 반환"""
    return _detect_provider()


def get_llm_model() -> str:
    """현재 LLM 모델명 반환 (기본값 자동 설정)"""
    if LLM_MODEL:
        return LLM_MODEL
    provider = _detect_provider()
    if provider == "gemini":
        return "gemini-2.5-flash"
    elif provider == "openai":
        return "gpt-3.5-turbo"
    return ""


def is_llm_available() -> bool:
    """LLM API 키가 설정되어 있는지 확인"""
    return _detect_provider() != "none"


# ──────────────────────────────────────
# SQLite 설정
# ──────────────────────────────────────
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "campus_tasks.db")

# ──────────────────────────────────────
# ChromaDB (벡터 스토어) 설정
# ──────────────────────────────────────
CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "chroma_db_storage")
CHROMA_COLLECTION_NAME: str = "university_notices"

# ──────────────────────────────────────
# 외부 공공 API 키
# 발급: youthcenter.go.kr 마이페이지 → 오픈API / openapi.work.go.kr 회원가입 후 신청
# ──────────────────────────────────────
YOUTH_CENTER_API_KEY: str = os.getenv("YOUTH_CENTER_API_KEY", "")
WORKNET_API_KEY: str = os.getenv("WORKNET_API_KEY", "")

# ──────────────────────────────────────
# 앱 메타데이터
# ──────────────────────────────────────
APP_NAME: str = "CampusAgent"
APP_VERSION: str = "0.9.0"
APP_DESCRIPTION: str = "대학생 특화 LLM+MCP 로컬 AI 어시스턴트 (Task + Calendar + 실시간 크롤링 검색)"
