"""
CampusAgent 환경 설정 모듈
- dotenv 기반 환경변수 로딩
- LLM / DB / ChromaDB 등 전역 상수 관리
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────
# LLM 설정
# ──────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))

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
# 앱 메타데이터
# ──────────────────────────────────────
APP_NAME: str = "CampusAgent"
APP_VERSION: str = "0.3.0"
APP_DESCRIPTION: str = "대학생 특화 LLM+MCP 로컬 AI 어시스턴트 (Task + Calendar + RAG)"


def is_llm_available() -> bool:
    """OpenAI API 키가 설정되어 있는지 확인"""
    return bool(OPENAI_API_KEY)
