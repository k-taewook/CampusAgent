"""
CampusAgent - 대학생 정보 검색 도구 (LangChain Tool)
- 편입학/전공심화, 국가제도/장학, 공모전/대외활동 검색
- 기존 인하공전 공지사항 크롤러와 분리된 확장 도구
"""
import json
import os
from typing import Optional

from langchain_core.tools import tool

from rag.chunker import SimpleTextChunker
from rag.embedder import DocumentEmbedder
from rag.retriever import search_notices


STUDENT_INFO_CATEGORIES = {
    "transfer": "편입학/전공심화",
    "policy": "국가제도/장학/청년정책",
    "contest": "공모전/대외활동/현장실습/인턴십",
}


def _load_student_info_from_json(filepath: str) -> list[dict]:
    """대학생 정보 JSON을 RAG 문서 형식으로 변환"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    documents = []
    for idx, item in enumerate(raw_data):
        category = item.get("category", "general")
        deadline = item.get("deadline", "")
        target = item.get("target", "")
        title = item.get("title", "제목 없음")
        content = item.get("content", "")
        source = item.get("source", "알 수 없음")

        full_text = (
            f"[{STUDENT_INFO_CATEGORIES.get(category, category)}] {title}\n"
            f"대상: {target or '대상 정보 없음'}\n"
            f"마감일: {deadline or '마감일 정보 없음'}\n"
            f"출처: {source}\n"
            f"{content}"
        )

        documents.append({
            "id": item.get("id", f"student_info_{idx}"),
            "title": title,
            "content": content,
            "date": item.get("date", ""),
            "category": category,
            "source": source,
            "url": item.get("url", ""),
            "deadline": deadline,
            "target": target,
            "full_text": full_text,
        })

    return documents


def _guess_student_info_category(query: str) -> str:
    """질문 키워드로 대학생 정보 카테고리 추정"""
    q = query.lower()
    if any(k in q for k in ["편입", "전공심화", "모집요강", "입학"]):
        return "transfer"
    if any(k in q for k in ["국가장학", "국가근로", "학자금", "청년정책", "장학", "제도"]):
        return "policy"
    if any(k in q for k in ["공모전", "대외활동", "현장실습", "인턴", "인턴십"]):
        return "contest"
    return ""


def _format_result_item(index: int, result: dict) -> str:
    """검색 결과 한 건을 사용자 응답 문자열로 변환"""
    category = result.get("category", "")
    category_label = STUDENT_INFO_CATEGORIES.get(category, category or "분류 없음")
    deadline = result.get("deadline") or "마감일 정보 없음"
    target = result.get("target") or "대상 정보 없음"
    source = result.get("source") or "출처 정보 없음"
    url = result.get("url") or ""
    text = result.get("text", "")
    summary = text[:280] + ("..." if len(text) > 280 else "")

    return (
        f"📌 **{index}. {result.get('title', '제목 없음')}**\n"
        f"   📂 분류: {category_label} | 관련도 {result.get('relevance', 0):.0%}\n"
        f"   👤 대상: {target}\n"
        f"   📅 마감일: {deadline}\n"
        f"   🏛️ 출처: {source}\n"
        f"   📝 요약: {summary}\n"
        + (f"   🔗 {url}" if url else "")
    )


@tool
def load_student_info_data(filepath: str = "data/student_info_samples.json") -> str:
    """
    대학생 정보 JSON 데이터를 검색 시스템에 로드합니다.

    Args:
        filepath: 대학생 정보 JSON 파일 경로

    Returns:
        로드 결과 문자열
    """
    try:
        documents = _load_student_info_from_json(filepath)
        if not documents:
            return f"❌ '{filepath}'에서 대학생 정보 데이터를 로드할 수 없습니다."

        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(documents)
        embedder = DocumentEmbedder()
        stored = embedder.embed_and_store(chunked)
        categories = sorted({doc.get("category", "general") for doc in documents})
        category_labels = ", ".join(
            STUDENT_INFO_CATEGORIES.get(c, c) for c in categories
        )

        return (
            "✅ 대학생 정보 데이터 로드 완료!\n\n"
            f"📄 원본 문서: {len(documents)}건\n"
            f"✂️ 청크 분할: {len(chunked)}건\n"
            f"💾 ChromaDB 저장: {stored}건\n"
            f"📚 카테고리: {category_labels}"
        )
    except Exception as e:
        return f"❌ 대학생 정보 데이터 로드 실패: {e}"


@tool
def search_student_info(
    query: str,
    category: str = "",
    n_results: int = 5,
) -> str:
    """
    편입학, 국가제도, 공모전/대외활동 등 대학생 생활 정보를 검색합니다.

    Args:
        query: 검색 키워드 또는 질문
        category: transfer/policy/contest 중 하나. 비워두면 자동 추정 또는 전체 검색
        n_results: 반환할 최대 결과 수

    Returns:
        검색 결과 문자열
    """
    try:
        selected_category = category.strip() or _guess_student_info_category(query)
        categories = (
            [selected_category]
            if selected_category in STUDENT_INFO_CATEGORIES
            else list(STUDENT_INFO_CATEGORIES)
        )

        merged_results = []
        seen_titles = set()
        for cat in categories:
            for result in search_notices(query=query, n_results=n_results, category=cat):
                title = result.get("title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                merged_results.append(result)

        merged_results.sort(key=lambda item: item.get("relevance", 0), reverse=True)
        display = merged_results[:n_results]

        if not display:
            return (
                f"🔍 '{query}' 관련 대학생 정보를 찾지 못했습니다.\n\n"
                "먼저 `load_student_info_data`로 샘플 데이터를 로드한 뒤 다시 검색해보세요."
            )

        category_text = (
            STUDENT_INFO_CATEGORIES.get(selected_category, "전체")
            if selected_category
            else "전체"
        )
        header = (
            f"🌐 **'{query}' 관련 대학생 정보 검색 결과**\n"
            f"   검색 범위: {category_text} | 결과 {len(display)}건\n"
            f"{'─' * 40}\n\n"
        )
        items = [
            _format_result_item(i, result)
            for i, result in enumerate(display, 1)
        ]
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 마감일이 있는 항목은 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 정확한 지원 조건은 반드시 표시된 공식 출처에서 다시 확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 대학생 정보 검색 실패: {e}"


@tool
def get_student_info_stats() -> str:
    """
    대학생 정보 검색 데이터 상태를 확인합니다.

    Returns:
        저장 상태 문자열
    """
    try:
        counts = {}
        for category, label in STUDENT_INFO_CATEGORIES.items():
            results = search_notices(
                query=label,
                n_results=20,
                category=category,
            )
            counts[label] = len(results)

        if not any(counts.values()):
            return (
                "📊 현재 검색 가능한 대학생 정보 데이터가 없습니다.\n\n"
                "💡 `load_student_info_data`를 실행해 샘플 데이터를 먼저 로드하세요."
            )

        lines = ["📊 **대학생 정보 검색 데이터 현황**"]
        for label, count in counts.items():
            lines.append(f"- {label}: 검색 가능 문서 {count}건")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 대학생 정보 상태 조회 실패: {e}"


STUDENT_INFO_TOOLS = [
    search_student_info,
    load_student_info_data,
    get_student_info_stats,
]
