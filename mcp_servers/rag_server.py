"""
CampusAgent - RAG 검색 MCP 도구 (LangChain Tool)
- 실시간 크롤링 + 검색 (학과 홈페이지에서 바로 검색)
- 저장된 공지사항 삭제
- 공지사항 통계 조회
"""
from langchain_core.tools import tool
from typing import Optional

from rag.retriever import search_notices, get_notice_count
from rag.loader import load_notices_from_json
from rag.chunker import SimpleTextChunker
from rag.embedder import DocumentEmbedder


@tool
def search_university_notices(query: str, n_results: int = 5) -> str:
    """
    학과 공지사항을 검색합니다.
    ChromaDB에 관련 데이터가 있으면 즉시 반환하고,
    없으면 홈페이지 검색 기능으로 1페이지 전체를 크롤링하여 ChromaDB에 저장한 뒤 반환합니다.
    사용자가 '장학금 공지사항 찾아줘', '휴강 공지 있어?' 등을 요청하면 이 도구를 사용하세요.

    Args:
        query: 검색 키워드 (예: "장학금", "수강 변경", "졸업 요건", "휴강")
        n_results: 반환할 최대 결과 수 (기본값: 5)

    Returns:
        검색 결과 문자열
    """
    try:
        from rag.crawler import search_notices_live, _extract_keywords
        from datetime import datetime

        # ── 1단계: ChromaDB에 관련 데이터가 있는지 먼저 확인 ──
        RELEVANCE_THRESHOLD = 0.45  # 이 점수 이상이면 캐시 데이터로 답변

        cached = search_notices(query=query, n_results=n_results * 3)

        # 제목 기준 중복 제거 후 충분히 관련 있는 결과만 추출
        seen: set = set()
        relevant_cached = []
        for r in cached:
            if r["relevance"] >= RELEVANCE_THRESHOLD and r["title"] not in seen:
                seen.add(r["title"])
                relevant_cached.append(r)
            if len(relevant_cached) >= n_results:
                break

        if relevant_cached:
            # ChromaDB 캐시 결과 반환
            header = (
                f"🔍 **'{query}' 관련 공지사항** (저장된 데이터에서 검색)\n"
                f"{'─' * 40}\n\n"
            )
            items = []
            for i, r in enumerate(relevant_cached, 1):
                url = r.get("url", "")
                items.append(
                    f"📌 **{i}. {r['title']}**\n"
                    f"   📅 {r['date'] or '날짜 없음'} | "
                    f"📂 {r['category']} | "
                    f"관련도 {r['relevance']:.0%}\n"
                    f"   📄 {r['text'][:300]}"
                    f"{'...' if len(r['text']) > 300 else ''}\n"
                    + (f"   🔗 {url}" if url else "")
                )
            return header + "\n\n".join(items)

        # ── 2단계: 캐시 없음 → 홈페이지 검색 기능으로 크롤링 ──
        crawled = search_notices_live(
            query=query,
            department="cse",
            pages=1,
            max_results=None,  # 1페이지 전체
        )

        if not crawled:
            return (
                f"🔍 '{query}' 관련 공지사항을 찾을 수 없습니다.\n\n"
                "학교 홈페이지 접속에 문제가 있거나, "
                "해당 키워드와 일치하는 공지가 없을 수 있습니다."
            )

        # ── 3단계: 크롤링 결과 전체를 ChromaDB에 저장 ──
        keywords = _extract_keywords(query)
        main_keyword = keywords[0] if keywords else query
        timestamp = datetime.now().strftime("%Y%m%d%H%M")

        raw_docs = []
        for idx, r in enumerate(crawled):
            raw_docs.append({
                "id": f"live_{main_keyword}_{timestamp}_{idx}",
                "title": r["title"],
                "content": r["content"],
                "date": r["date"],
                "category": r["category"],
                "source": "인하공업전문대학 학과 홈페이지",
                "url": r.get("url", ""),
                "full_text": f"[{r['category']}] {r['title']}\n{r['content']}",
            })

        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(raw_docs)
        embedder = DocumentEmbedder()
        embedder.embed_and_store(chunked)

        # ── 4단계: 크롤링 결과 반환 (상위 n_results건) ──
        display = crawled[:n_results]

        header = (
            f"🔍 **'{query}' 관련 공지사항**\n"
            f"   홈페이지 검색 결과 **{len(crawled)}건** 수집 · ChromaDB 저장 완료 "
            f"(상위 {len(display)}건 표시)\n"
            f"{'─' * 40}\n\n"
        )

        items = []
        for i, r in enumerate(display, 1):
            attach_info = ""
            if r.get("attachments"):
                attach_names = [a["name"] for a in r["attachments"]]
                attach_info = f"\n   📎 첨부: {', '.join(attach_names)}"

            url = r.get("url", "")
            items.append(
                f"📌 **{i}. {r['title']}**\n"
                f"   📅 {r['date'] or '날짜 없음'} | "
                f"📂 {r['category']} | "
                f"👁️ 조회수 {r.get('views', '-')}\n"
                f"   📄 {r['content'][:300]}"
                f"{'...' if len(r['content']) > 300 else ''}"
                f"{attach_info}\n"
                + (f"   🔗 {url}" if url else "")
            )

        return header + "\n\n".join(items)

    except ImportError:
        return (
            "❌ 크롤링 모듈을 불러올 수 없습니다.\n"
            "`pip install requests beautifulsoup4` 를 실행해주세요."
        )
    except Exception as e:
        return f"❌ 공지사항 검색 실패: {e}"


@tool
def clear_notice_data() -> str:
    """
    저장된 공지사항 데이터를 모두 삭제합니다.
    ChromaDB에 저장된 모든 공지사항을 초기화합니다.

    Returns:
        삭제 결과 문자열
    """
    try:
        embedder = DocumentEmbedder()
        before_count = embedder.get_collection_count()

        if before_count == 0:
            return "📭 삭제할 공지사항이 없습니다. 이미 비어있습니다."

        embedder.clear_collection()

        return (
            f"🗑️ **공지사항 데이터 삭제 완료!**\n\n"
            f"   삭제된 문서(청크): {before_count}건\n"
            f"   현재 저장 문서: 0건\n\n"
            f"💡 새로운 공지를 검색하려면 '공지사항 검색해줘'라고 요청하세요."
        )
    except Exception as e:
        return f"❌ 공지사항 삭제 실패: {e}"


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
            return (
                "📊 현재 저장된 공지사항이 없습니다.\n\n"
                "💡 '장학금 공지 찾아줘'처럼 요청하면 "
                "학과 홈페이지에서 실시간으로 검색합니다!"
            )
        return f"📊 **공지사항 RAG 현황**\n   💾 저장된 문서(청크): {count}건"
    except Exception as e:
        return f"❌ 상태 조회 실패: {e}"


# 에이전트에 바인딩할 도구 리스트
RAG_TOOLS = [
    search_university_notices,
    clear_notice_data,
    load_notice_data,
    get_notice_stats,
]
