"""
CampusAgent - RAG 검색 MCP 도구 (LangChain Tool)
- 공지사항 검색 / 공지사항 추가(인제스트) / 문서 수 확인
- 학과 공지사항 웹 크롤링 + RAG 인제스트
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
                "'학과 공지사항 크롤링해줘'라고 요청해보세요."
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
def crawl_department_notices(pages: int = 3, max_notices: int = 30) -> str:
    """
    학과 홈페이지에서 실제 공지사항을 크롤링하여 RAG 시스템에 저장합니다.
    인하공업전문대학 컴퓨터시스템공학과 공지사항을 웹에서 수집하고,
    자동으로 청킹 + 임베딩하여 검색 가능한 상태로 만듭니다.

    Args:
        pages: 크롤링할 목록 페이지 수 (기본값: 3, 한 페이지당 약 10건)
        max_notices: 상세 내용을 수집할 최대 공지 수 (기본값: 30)

    Returns:
        크롤링 및 저장 결과 문자열
    """
    try:
        from rag.crawler import crawl_full_notices

        # 1. 웹 크롤링 (목록 + 상세 내용)
        documents = crawl_full_notices(
            department="cse",
            pages=pages,
            max_detail=max_notices,
            save_json=True,
        )

        if not documents:
            return (
                "❌ 크롤링된 공지사항이 없습니다.\n\n"
                "학교 홈페이지 접속에 문제가 있을 수 있습니다.\n"
                "네트워크 연결을 확인해주세요."
            )

        # 2. 청킹
        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(documents)

        # 3. 임베딩 & ChromaDB 저장
        embedder = DocumentEmbedder()
        stored = embedder.embed_and_store(chunked)

        # 4. 카테고리별 통계
        category_counts = {}
        for doc in documents:
            cat = doc.get("category", "일반")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        cat_summary = " | ".join(f"{k}: {v}건" for k, v in sorted(category_counts.items()))

        return (
            f"✅ 학과 공지사항 크롤링 및 RAG 저장 완료!\n\n"
            f"🕷️ 크롤링 페이지: {pages}페이지\n"
            f"📄 수집된 공지: {len(documents)}건\n"
            f"✂️ 청크 분할: {len(chunked)}건\n"
            f"💾 ChromaDB 저장: {stored}건\n"
            f"📊 전체 저장 문서: {embedder.get_collection_count()}건\n\n"
            f"📂 카테고리 분포: {cat_summary}\n\n"
            f"💡 이제 '장학금 검색해줘', '졸업요건 알려줘' 등으로 검색할 수 있습니다!"
        )
    except ImportError:
        return (
            "❌ 크롤링 모듈을 불러올 수 없습니다.\n"
            "`pip install requests beautifulsoup4` 를 실행해주세요."
        )
    except Exception as e:
        return f"❌ 크롤링 실패: {e}"


@tool
def load_notice_data(filepath: str = "data/sample_notices.json") -> str:
    """
    공지사항 JSON 데이터를 RAG 시스템에 로드합니다.
    문서 로드 → 청킹 → 임베딩 → ChromaDB 저장 파이프라인을 실행합니다.
    크롤링된 데이터 파일(data/crawled_notices_cse.json)도 로드 가능합니다.

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
            return (
                "📊 현재 저장된 공지사항이 없습니다.\n\n"
                "💡 '학과 공지사항 크롤링해줘'라고 말하면 "
                "학과 홈페이지에서 실제 공지사항을 가져올 수 있습니다!"
            )
        return f"📊 **공지사항 RAG 현황**\n   💾 저장된 문서(청크): {count}건"
    except Exception as e:
        return f"❌ 상태 조회 실패: {e}"


# 에이전트에 바인딩할 도구 리스트
RAG_TOOLS = [
    search_university_notices,
    crawl_department_notices,
    load_notice_data,
    get_notice_stats,
]
