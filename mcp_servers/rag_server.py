"""
CampusAgent - RAG 검색 MCP 도구 (LangChain Tool)
- 공지사항 검색 / 공지사항 추가(인제스트) / 문서 수 확인
"""
from langchain_core.tools import tool
from typing import Optional

from rag.retriever import search_notices, get_notice_count
from rag.loader import load_notices_from_json
from rag.chunker import SimpleTextChunker
from rag.embedder import DocumentEmbedder


@tool
def search_university_notices(query: str, n_results: int = 5, category: str = "") -> str:
    """
    대학 공지사항을 검색합니다. RAG 기반 유사도 검색을 수행합니다.

    Args:
        query: 검색 내용 (예: "장학금 신청", "수강 변경", "졸업 요건")
        n_results: 반환할 결과 수 (기본값: 5)
        category: 카테고리 필터 (학사/장학/취업/일반 등, 선택)

    Returns:
        검색 결과 문자열
    """
    try:
        total = get_notice_count()
        if total == 0:
            return (
                "📭 저장된 공지사항이 없습니다.\n\n"
                "공지사항 데이터를 먼저 로드해야 합니다.\n"
                "'공지사항 데이터 로드해줘'라고 요청해보세요."
            )

        results = search_notices(
            query=query,
            n_results=n_results,
            category=category if category else None,
        )

        if not results:
            return f"🔍 '{query}'에 대한 검색 결과가 없습니다."

        header = f"🔍 **'{query}' 검색 결과** (총 {len(results)}건 / 저장 공지 {total}건)\n{'─' * 30}\n\n"
        items = []
        for i, r in enumerate(results, 1):
            relevance_bar = "🟢" if r["relevance"] > 0.7 else "🟡" if r["relevance"] > 0.4 else "🔴"
            items.append(
                f"{relevance_bar} **{i}. {r['title']}**\n"
                f"   📂 카테고리: {r['category']} | 📅 날짜: {r['date']}\n"
                f"   📄 {r['text'][:200]}{'...' if len(r['text']) > 200 else ''}\n"
                f"   관련도: {r['relevance']:.1%}"
            )

        return header + "\n\n".join(items)
    except Exception as e:
        return f"❌ 공지사항 검색 실패: {e}"


@tool
def load_notice_data(filepath: str = "data/sample_notices.json") -> str:
    """
    공지사항 JSON 데이터를 RAG 시스템에 로드합니다.
    문서 로드 → 청킹 → 임베딩 → ChromaDB 저장 파이프라인을 실행합니다.

    Args:
        filepath: 공지사항 JSON 파일 경로 (기본값: "data/sample_notices.json")

    Returns:
        로드 결과 문자열
    """
    try:
        # 1. 문서 로드
        documents = load_notices_from_json(filepath)
        if not documents:
            return f"❌ '{filepath}'에서 문서를 로드할 수 없습니다."

        # 2. 청킹
        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(documents)

        # 3. 임베딩 & 저장
        embedder = DocumentEmbedder()
        stored = embedder.embed_and_store(chunked)

        return (
            f"✅ 공지사항 데이터 로드 완료!\n\n"
            f"📄 원본 문서: {len(documents)}건\n"
            f"✂️ 청크 분할: {len(chunked)}건\n"
            f"💾 ChromaDB 저장: {stored}건\n"
            f"📊 전체 저장 문서: {embedder.get_collection_count()}건"
        )
    except Exception as e:
        return f"❌ 데이터 로드 실패: {e}"


@tool
def get_notice_stats() -> str:
    """
    공지사항 RAG 시스템의 현재 상태를 확인합니다.

    Returns:
        저장된 공지사항 통계 문자열
    """
    try:
        count = get_notice_count()
        if count == 0:
            return "📊 현재 저장된 공지사항이 없습니다. 데이터를 로드해주세요."
        return f"📊 **공지사항 RAG 현황**\n   💾 저장된 문서(청크): {count}건"
    except Exception as e:
        return f"❌ 상태 조회 실패: {e}"


# 에이전트에 바인딩할 도구 리스트
RAG_TOOLS = [
    search_university_notices,
    load_notice_data,
    get_notice_stats,
]
