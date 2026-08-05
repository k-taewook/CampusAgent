"""
CampusAgent - 대학생 정보 검색 도구 (LangChain Tool)
- 편입학/전공심화, 국가제도/장학, 공모전/대외활동 검색
- 정적 샘플 검색 + 학교 공지 실시간 크롤링(combBbs) 결합
"""
import json
import os
import re
import time
from datetime import datetime
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

# 카테고리별 학교 공지 검색 키워드 (combBbs 서버 사이드 검색용)
# 인하공전 공지사항에서 해당 키워드로 검색되는 글은 대학생 정보로 분류
STUDENT_INFO_KEYWORDS = {
    "transfer": ["편입", "전공심화"],
    "policy": ["국가장학금", "장학금", "국가근로"],
    "contest": ["공모전", "현장실습", "인턴십"],
}

PERSONALIZED_INTEREST_ALIASES = {
    "transfer": "편입학/전공심화",
    "policy": "장학금/청년정책",
    "contest": "공모전/대외활동",
    "intern": "현장실습/인턴십",
}

POLICY_PERSONALIZED_TRIGGERS = [
    "내가 받을 수 있는",
    "나한테 맞는",
    "신청 가능한",
    "받을 수 있는",
    "지원 가능한",
    "내 조건",
]

POLICY_REGION_KEYWORDS = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

POLICY_STUDENT_KEYWORDS = ["대학생", "재학생", "휴학생", "졸업예정", "졸업생"]
POLICY_EMPLOYMENT_KEYWORDS = [
    "미취업", "취업준비", "구직", "재직", "직장인", "취업", "창업", "사업자",
]

# 실시간 크롤링 결과를 단기 캐싱하여 같은 쿼리 반복 시 서버 부담 완화 (TTL 5분)
_LIVE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_LIVE_CACHE_TTL = 300.0


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


def _is_personalized_policy_query(query: str) -> bool:
    """청년정책 신청 가능 여부를 묻는 개인화 질의인지 확인합니다."""
    return any(trigger in query for trigger in POLICY_PERSONALIZED_TRIGGERS)


def _extract_policy_context(
    query: str,
    region: str = "",
    age: str = "",
    employment_status: str = "",
    student_status: str = "",
) -> dict:
    """청년정책 후보 필터링에 쓸 사용자 조건을 간단히 추출합니다."""
    text = query.strip()
    inferred_region = region.strip()
    if not inferred_region:
        inferred_region = next((kw for kw in POLICY_REGION_KEYWORDS if kw in text), "")

    inferred_age = age.strip()
    if not inferred_age:
        match = re.search(r"(\d{2})\s*(세|살)", text)
        inferred_age = match.group(0).replace(" ", "") if match else ""

    inferred_student = student_status.strip()
    if not inferred_student:
        inferred_student = next((kw for kw in POLICY_STUDENT_KEYWORDS if kw in text), "")

    inferred_employment = employment_status.strip()
    if not inferred_employment:
        if "취업 안" in text or "취업하지" in text:
            inferred_employment = "미취업"
        else:
            inferred_employment = next((kw for kw in POLICY_EMPLOYMENT_KEYWORDS if kw in text), "")

    return {
        "region": inferred_region,
        "age": inferred_age,
        "student_status": inferred_student,
        "employment_status": inferred_employment,
    }


def _missing_policy_context(context: dict) -> list[str]:
    """개인화 청년정책 검색 전 추가 확인이 필요한 조건을 반환합니다."""
    missing = []
    if not context["region"]:
        missing.append("거주 지역")
    if not context["age"]:
        missing.append("나이")
    if not context["student_status"]:
        missing.append("재학 상태")
    if not context["employment_status"]:
        missing.append("취업 상태")
    return missing


def _policy_context_question(query: str, missing: list[str]) -> str:
    """조건 부족 시 바로 검색하지 않고 확인 질문을 반환합니다."""
    missing_text = ", ".join(missing)
    return (
        f"🔎 '{query}'에 대해 실제 신청 가능성을 보려면 추가 조건이 필요합니다.\n\n"
        "청년정책은 나이, 거주 지역, 재학 상태, 취업 상태, 소득 조건에 따라 "
        "신청 가능 여부가 달라집니다. 현재 정보만으로는 확정 추천을 하면 오해가 생길 수 있습니다.\n\n"
        f"먼저 **{missing_text}**를 알려주세요.\n\n"
        "예시: `나는 인천에 사는 24세 대학생이고 아직 취업 안 했어. 받을 수 있는 청년 정책 찾아줘.`"
    )


def _rank_policy_candidates(results: list[dict], context: dict) -> list[dict]:
    """사용자 조건 키워드가 포함된 후보를 위로 올립니다."""
    terms = [value for value in context.values() if value]
    if not terms:
        return results

    ranked = []
    for idx, item in enumerate(results):
        haystack = " ".join(
            [
                item.get("title", ""),
                item.get("content", ""),
                item.get("source", ""),
            ]
        )
        score = sum(1 for term in terms if term and term in haystack)
        copied = dict(item)
        copied["_condition_score"] = score
        copied["_eligibility_note"] = (
            "입력한 조건 일부가 정책명/요약/기관 정보에 포함되어 있습니다."
            if score
            else "입력한 조건과 직접 일치하는 단서는 결과 요약에서 확인되지 않았습니다."
        )
        ranked.append((score, idx, copied))

    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked]


def _normalize_interests(interests: str) -> list[str]:
    """설정 문자열을 개인화 관심 영역 키 목록으로 정리합니다."""
    if not interests:
        return ["policy", "contest", "intern"]

    tokens = [
        token.strip().lower()
        for token in interests.replace("/", ",").replace("|", ",").split(",")
        if token.strip()
    ]
    selected: list[str] = []
    for token in tokens:
        if token in PERSONALIZED_INTEREST_ALIASES:
            selected.append(token)
            continue
        if any(keyword in token for keyword in ["편입", "전공심화", "transfer"]):
            selected.append("transfer")
        elif any(keyword in token for keyword in ["장학", "정책", "국가", "policy"]):
            selected.append("policy")
        elif any(keyword in token for keyword in ["공모", "대외", "contest"]):
            selected.append("contest")
        elif any(keyword in token for keyword in ["인턴", "현장실습", "취업", "intern", "job"]):
            selected.append("intern")

    deduped = []
    for item in selected:
        if item not in deduped:
            deduped.append(item)
    return deduped or ["policy", "contest", "intern"]


def _build_personalized_queries(
    major: str = "",
    grade: str = "",
    interests: str = "",
    preferred_school: str = "",
    career_goal: str = "",
) -> list[dict]:
    """사용자 프로필을 기반으로 검색할 대학 정보 쿼리를 생성합니다."""
    major_text = major.strip() or "전공 미설정"
    grade_text = grade.strip() or "학년 미설정"
    school_text = preferred_school.strip()
    career_text = career_goal.strip()
    interest_keys = _normalize_interests(interests)

    query_context = " ".join(
        part for part in [major_text, grade_text, career_text] if part and "미설정" not in part
    )
    queries: list[dict] = []
    for key in interest_keys:
        if key == "transfer":
            query = f"{school_text or major_text} 편입학 전공심화 모집요강 {grade_text}".strip()
            queries.append({"category": "transfer", "query": query, "label": PERSONALIZED_INTEREST_ALIASES[key]})
        elif key == "policy":
            query = f"{query_context} 국가장학금 장학금 청년정책".strip()
            queries.append({"category": "policy", "query": query, "label": PERSONALIZED_INTEREST_ALIASES[key]})
        elif key == "contest":
            query = f"{query_context} 공모전 대외활동".strip()
            queries.append({"category": "contest", "query": query, "label": PERSONALIZED_INTEREST_ALIASES[key]})
        elif key == "intern":
            query = f"{query_context} 현장실습 인턴십 취업".strip()
            queries.append({"category": "contest", "query": query, "label": PERSONALIZED_INTEREST_ALIASES[key]})
    return queries


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


@tool
def search_personalized_student_info(
    major: str = "",
    grade: str = "",
    interests: str = "",
    preferred_school: str = "",
    career_goal: str = "",
    n_results: int = 5,
) -> str:
    """
    설정 탭에 저장된 개인정보를 바탕으로 맞춤형 대학생 정보를 추천합니다.
    사용자가 "내 정보에 맞는 정보", "나한테 맞는 장학금/공모전/편입 정보"처럼
    개인화 추천을 요청하면 사용하세요.

    Args:
        major: 사용자 전공
        grade: 사용자 학년
        interests: 관심 영역. transfer, policy, contest, intern 또는 한글 설명을 쉼표로 구분
        preferred_school: 관심 학교/희망 편입 학교
        career_goal: 희망 진로/관심 직무
        n_results: 전체 반환 최대 결과 수

    Returns:
        개인화 추천 결과 문자열
    """
    try:
        queries = _build_personalized_queries(
            major=major,
            grade=grade,
            interests=interests,
            preferred_school=preferred_school,
            career_goal=career_goal,
        )
        per_query = max(2, min(5, n_results))
        merged_results = []
        seen_titles: set[str] = set()

        for plan in queries:
            for result in search_notices(
                query=plan["query"],
                n_results=per_query,
                category=plan["category"],
            ):
                title = result.get("title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                result["_personalized_label"] = plan["label"]
                merged_results.append(result)

        merged_results.sort(key=lambda item: item.get("relevance", 0), reverse=True)
        display = merged_results[:n_results]
        interest_labels = ", ".join(plan["label"] for plan in queries)
        profile_lines = [
            f"- 전공: {major or '미설정'}",
            f"- 학년: {grade or '미설정'}",
            f"- 관심 영역: {interest_labels}",
        ]
        if preferred_school:
            profile_lines.append(f"- 관심 학교: {preferred_school}")
        if career_goal:
            profile_lines.append(f"- 희망 진로: {career_goal}")

        header = (
            "🎯 **개인화 대학 정보 추천**\n"
            + "\n".join(profile_lines)
            + f"\n{'─' * 40}\n\n"
        )

        if not display:
            fallback_queries = "\n".join(
                f"- {plan['label']}: `{plan['query']}`"
                for plan in queries
            )
            return (
                header
                + "아직 저장된 대학생 정보 데이터에서 맞춤 결과를 찾지 못했습니다.\n\n"
                + "💡 **다음 추천 행동**\n"
                + "- `load_student_info_data`로 샘플 데이터를 먼저 로드해보세요.\n"
                + "- 최신 정보가 필요하면 '내 정보에 맞는 최신 정보 찾아줘'라고 요청해 실시간 검색을 시도하세요.\n"
                + "- 생성된 개인화 검색어는 다음과 같습니다.\n"
                + fallback_queries
            )

        items = []
        for index, result in enumerate(display, 1):
            label = result.get("_personalized_label", "맞춤 정보")
            items.append(f"🏷️ 추천 이유: {label}\n" + _format_result_item(index, result))

        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 마음에 드는 항목의 마감일은 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 조건이 중요한 정보는 반드시 공식 출처에서 지원 자격을 다시 확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 개인화 대학 정보 추천 실패: {e}"


def _crawl_student_info_live(
    category: str,
    keyword_override: str = "",
    pages: int = 1,
    max_per_keyword: int = 5,
) -> list[dict]:
    """
    학교 공지(combBbs)를 카테고리 키워드로 실시간 크롤링하여 대학생 정보로 변환.
    robots.txt 준수, User-Agent 명시, 요청 간 1초 딜레이는 rag.crawler 측에서 처리.
    """
    from rag.crawler import search_school_notices_live

    cache_key = f"{category}|{keyword_override}|{pages}|{max_per_keyword}"
    now = time.time()
    cached = _LIVE_CACHE.get(cache_key)
    if cached and now - cached[0] < _LIVE_CACHE_TTL:
        return cached[1]

    keywords = (
        [keyword_override]
        if keyword_override
        else STUDENT_INFO_KEYWORDS.get(category, [])
    )
    if not keywords:
        return []

    seen_urls: set[str] = set()
    merged: list[dict] = []
    for kw in keywords:
        try:
            crawled = search_school_notices_live(
                query=kw,
                pages=pages,
                max_results=max_per_keyword,
            )
        except Exception as e:
            print(f"⚠️ '{kw}' 크롤링 실패: {e}")
            continue

        for item in crawled:
            url = item.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            item["category"] = category
            item["source"] = "인하공업전문대학 대표 홈페이지"
            merged.append(item)

    _LIVE_CACHE[cache_key] = (now, merged)
    return merged


@tool
def search_student_info_live(
    query: str,
    category: str = "",
    n_results: int = 5,
) -> str:
    """
    학교 대표 홈페이지 공지를 **실시간 크롤링**하여 대학생 정보를 검색합니다.
    편입/장학/공모전 같은 카테고리 키워드로 학교 공지 게시판을 직접 검색하므로
    최신 정보가 필요할 때 사용하세요. 결과는 ChromaDB에도 자동 저장되어
    이후 `search_student_info`로도 재검색할 수 있습니다.

    Args:
        query: 사용자 질의 (예: "편입 모집요강 알려줘", "공모전 새로 나온 거")
        category: transfer/policy/contest 중 하나. 비워두면 자동 추정
        n_results: 반환할 최대 결과 수

    Returns:
        검색 결과 문자열 (공식 출처 URL 포함)
    """
    try:
        selected = category.strip() or _guess_student_info_category(query)
        target_categories = (
            [selected]
            if selected in STUDENT_INFO_CATEGORIES
            else list(STUDENT_INFO_CATEGORIES)
        )

        all_crawled: list[dict] = []
        for cat in target_categories:
            all_crawled.extend(_crawl_student_info_live(category=cat))

        if not all_crawled:
            return (
                f"🔍 '{query}' 관련 실시간 대학생 정보를 찾지 못했습니다.\n\n"
                "학교 홈페이지 접속 문제이거나 해당 키워드와 일치하는 공지가 없을 수 있습니다."
            )

        # ChromaDB에 저장하여 다음 검색부터 캐시 활용 가능
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        raw_docs = []
        for idx, item in enumerate(all_crawled):
            cat = item.get("category", "general")
            title = item.get("title", "제목 없음")
            content = item.get("content", "")
            raw_docs.append({
                "id": f"live_student_{cat}_{timestamp}_{idx}",
                "title": title,
                "content": content,
                "date": item.get("date", ""),
                "category": cat,
                "source": item.get("source", "인하공업전문대학 대표 홈페이지"),
                "url": item.get("url", ""),
                "deadline": "",
                "target": "대학생",
                "full_text": (
                    f"[{STUDENT_INFO_CATEGORIES.get(cat, cat)}] {title}\n{content}"
                ),
            })

        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(raw_docs)
        embedder = DocumentEmbedder()
        embedder.embed_and_store(chunked)

        # 의미 기반 검색으로 query에 가장 가까운 결과 선별
        merged_results = []
        seen_titles: set[str] = set()
        for cat in target_categories:
            for result in search_notices(query=query, n_results=n_results * 2, category=cat):
                title = result.get("title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                merged_results.append(result)

        merged_results.sort(key=lambda item: item.get("relevance", 0), reverse=True)
        display = merged_results[:n_results]

        if not display:
            # 검색 점수가 낮을 때는 크롤링 원문을 그대로 노출
            display = [
                {
                    "title": d.get("title", ""),
                    "text": d.get("content", "")[:500],
                    "category": d.get("category", ""),
                    "source": d.get("source", ""),
                    "url": d.get("url", ""),
                    "deadline": "",
                    "target": "대학생",
                    "relevance": 0.0,
                }
                for d in raw_docs[:n_results]
            ]

        category_text = (
            STUDENT_INFO_CATEGORIES.get(selected, "전체")
            if selected
            else "전체"
        )
        header = (
            f"🌐 **'{query}' 관련 대학생 정보 (실시간 크롤링)**\n"
            f"   학교 공지 수집 {len(all_crawled)}건 · 검색 범위 {category_text} · 표시 {len(display)}건\n"
            f"{'─' * 40}\n\n"
        )
        items = [
            _format_result_item(i, result)
            for i, result in enumerate(display, 1)
        ]
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 마감일이 있는 항목은 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 위 정보는 학교 공지에서 자동 추출된 것이므로 반드시 원문 URL에서 재확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except ImportError:
        return (
            "❌ 크롤링 모듈을 불러올 수 없습니다.\n"
            "`pip install requests beautifulsoup4` 를 실행해주세요."
        )
    except Exception as e:
        return f"❌ 대학생 정보 실시간 검색 실패: {e}"


def _store_external_results(results: list[dict], label: str) -> None:
    """외부 소스 크롤링 결과를 ChromaDB에 upsert."""
    if not results:
        return
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    raw_docs = []
    for idx, item in enumerate(results):
        cat = item.get("category", "general")
        title = item.get("title", "제목 없음")
        content = item.get("content", "")
        raw_docs.append({
            "id": f"ext_{label}_{timestamp}_{idx}",
            "title": title,
            "content": content,
            "date": item.get("date", ""),
            "category": cat,
            "source": item.get("source", "외부 공공기관"),
            "url": item.get("url", ""),
            "deadline": item.get("date", ""),
            "target": "대학생",
            "source_type": item.get("source_type", "public_api"),
            "provider": item.get("provider", label),
            "eligibility_checked": item.get("eligibility_checked", "false"),
            "query_context": item.get("query_context", ""),
            "full_text": f"[{STUDENT_INFO_CATEGORIES.get(cat, cat)}] {title}\n{content}",
        })
    chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
    chunked = chunker.split_documents(raw_docs)
    embedder = DocumentEmbedder()
    embedder.embed_and_store(chunked)


def _format_external_items(results: list[dict], n_results: int) -> list[str]:
    """외부 소스 결과를 포맷 문자열 리스트로 변환."""
    lines = []
    for i, item in enumerate(results[:n_results], 1):
        url = item.get("url", "")
        content = item.get("content", "")
        summary = content[:280] + ("..." if len(content) > 280 else "")
        cat = item.get("category", "")
        cat_label = STUDENT_INFO_CATEGORIES.get(cat, cat or "분류 없음")
        source = item.get("source", "")
        deadline = item.get("date", "마감일 정보 없음") or "마감일 정보 없음"
        eligibility_note = item.get("_eligibility_note", "")
        eligibility_line = (
            f"   ⚠️ 확인 필요 조건: {eligibility_note}\n"
            if eligibility_note
            else ""
        )
        lines.append(
            f"📌 **{i}. {item.get('title', '제목 없음')}**\n"
            f"   📂 분류: {cat_label}\n"
            f"   📅 마감/기간: {deadline}\n"
            f"   🏛️ 출처: {source}\n"
            f"{eligibility_line}"
            f"   📝 요약: {summary}\n"
            + (f"   🔗 {url}" if url else "")
        )
    return lines


@tool
def search_transfer_by_school(school_name: str, n_results: int = 5) -> str:
    """
    특정 학교의 편입학 모집요강 확인 경로를 검색합니다.
    사용자가 "○○대 편입학 정보 찾아줘", "○○대 모집요강" 같이 학교명을 직접 언급하면 사용하세요.

    Args:
        school_name: 검색할 학교 이름 (예: "연세대", "한양대")
        n_results: 반환할 최대 결과 수

    Returns:
        편입학 정보 문자열
    """
    try:
        from rag.external_crawler import crawl_transfer_by_school as _crawl
        results = _crawl(school_name=school_name, max_results=n_results)
        if not results:
            return (
                f"🔍 '{school_name}' 편입학 정보를 찾지 못했습니다.\n\n"
                "해당 학교 입학처 홈페이지에서 직접 검색해보세요."
            )
        _store_external_results(results, "transfer")
        items = _format_external_items(results, n_results)
        header = (
            f"🎓 **'{school_name}' 편입학 정보 확인 경로**\n"
            f"   수집 {len(results)}건\n"
            f"{'─' * 40}\n\n"
        )
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 지원 마감일을 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 편입학 모집요강은 어디가보다 학교 입학처 공식 사이트 원문을 우선 확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 편입학 정보 검색 실패: {e}"


@tool
def search_scholarship_policy(
    query: str,
    n_results: int = 5,
    region: str = "",
    age: str = "",
    employment_status: str = "",
    student_status: str = "",
) -> str:
    """
    온통청년 API로 국가장학금·청년지원 정책을 검색합니다.
    사용자가 "최신 장학금 알려줘", "청년 정책 뭐 있어?" 처럼 외부 장학/정책 정보를 요청할 때 사용하세요.
    API 키가 설정되지 않으면 설정 방법을 안내합니다.

    Args:
        query: 검색 키워드 (예: "국가장학금", "청년 주거 지원", "학자금대출")
        n_results: 반환할 최대 결과 수
        region: 거주 지역 (선택)
        age: 나이 또는 연령대 (선택)
        employment_status: 취업 상태 (선택)
        student_status: 재학 상태 (선택)

    Returns:
        청년정책 검색 결과 문자열
    """
    try:
        from config.settings import YOUTH_CENTER_API_KEY
        from rag.external_crawler import fetch_youth_policy

        context = _extract_policy_context(
            query=query,
            region=region,
            age=age,
            employment_status=employment_status,
            student_status=student_status,
        )
        if _is_personalized_policy_query(query):
            missing = _missing_policy_context(context)
            if len(missing) >= 2:
                return _policy_context_question(query, missing)

        if not YOUTH_CENTER_API_KEY:
            return (
                "⚠️ 온통청년 API 키가 설정되지 않았습니다.\n\n"
                "**API 키 발급 방법**\n"
                "1. https://www.youthcenter.go.kr 접속 후 회원가입\n"
                "2. 마이페이지 → 오픈(OPEN) API 메뉴에서 인증키 신청\n"
                "3. `.env` 파일에 `YOUTH_CENTER_API_KEY=발급받은키` 추가 후 앱 재시작\n\n"
                "💡 키 없이 검색하려면 `search_student_info`로 저장된 샘플 데이터를 조회하세요."
            )

        results = fetch_youth_policy(query=query, api_key=YOUTH_CENTER_API_KEY, display=n_results)
        if not results:
            return (
                f"🔍 '{query}' 관련 청년정책을 찾지 못했습니다.\n\n"
                "온통청년(https://www.youthcenter.go.kr)에서 직접 검색해보세요."
            )
        for item in results:
            item["source_type"] = "public_api"
            item["provider"] = "youthcenter"
            item["eligibility_checked"] = "false"
            item["query_context"] = query
        results = _rank_policy_candidates(results, context)
        _store_external_results(results, "policy")
        items = _format_external_items(results, n_results)
        context_parts = [
            f"{label}: {value}"
            for label, value in [
                ("지역", context["region"]),
                ("나이", context["age"]),
                ("재학 상태", context["student_status"]),
                ("취업 상태", context["employment_status"]),
            ]
            if value
        ]
        context_line = (
            f"   반영한 사용자 조건: {', '.join(context_parts)}\n"
            if context_parts
            else ""
        )
        header = (
            f"🏛️ **'{query}' 관련 청년정책/장학금 후보** (온통청년 기준)\n"
            f"   수집 {len(results)}건\n"
            f"{context_line}"
            f"{'─' * 40}\n\n"
            "이 결과는 실제 신청 가능 여부를 확정하지 않는 조건 확인용 후보입니다.\n"
            "나이, 거주 지역, 소득, 취업 상태, 재학 상태에 따라 실제 신청 가능 여부가 달라질 수 있습니다.\n\n"
        )
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 신청 기간이 있는 항목은 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 결과가 넓게 잡힐 수 있으므로 정확한 신청 조건은 반드시 온통청년 원문 URL에서 재확인하세요.\n"
            "- 소득 구간이나 세부 자격 조건이 필요한 정책은 원문 공고의 신청 자격을 우선 기준으로 판단하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 청년정책 검색 실패: {e}"


@tool
def search_job_intern(query: str, n_results: int = 5) -> str:
    """
    워크넷 공채속보 API로 채용공고를 검색합니다.
    사용자가 "인턴십 공고 찾아줘", "소프트웨어 채용 알려줘" 처럼 외부 취업 정보를 요청할 때 사용하세요.
    API 키가 설정되지 않으면 설정 방법을 안내합니다.

    Args:
        query: 검색 키워드 (예: "소프트웨어 인턴", "현장실습", "IT 채용")
        n_results: 반환할 최대 결과 수

    Returns:
        채용정보 검색 결과 문자열
    """
    try:
        from config.settings import WORKNET_API_KEY
        from rag.external_crawler import fetch_worknet_jobs

        if not WORKNET_API_KEY:
            return (
                "⚠️ 워크넷 API 키가 설정되지 않았습니다.\n\n"
                "**API 키 발급 방법**\n"
                "1. https://openapi.work.go.kr 접속 후 회원가입\n"
                "2. API 서비스 신청 → **공채속보 API** 선택 (개인회원 신청 가능)\n"
                "3. `.env` 파일에 `WORKNET_API_KEY=발급받은키` 추가 후 앱 재시작\n\n"
                "💡 키 없이 검색하려면 `search_student_info`로 저장된 샘플 데이터를 조회하세요."
            )

        results = fetch_worknet_jobs(query=query, api_key=WORKNET_API_KEY, display=n_results)
        if not results:
            return (
                f"🔍 '{query}' 관련 채용공고를 찾지 못했습니다.\n\n"
                "워크넷(https://www.work.go.kr)에서 직접 검색해보세요."
            )
        _store_external_results(results, "job")
        items = _format_external_items(results, n_results)
        header = (
            f"💼 **'{query}' 관련 채용/인턴십** (워크넷 기준)\n"
            f"   수집 {len(results)}건\n"
            f"{'─' * 40}\n\n"
        )
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 지원 마감일을 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 정확한 지원 조건은 반드시 워크넷 원문에서 재확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 채용정보 검색 실패: {e}"


@tool
def search_contest_external(query: str, n_results: int = 5) -> str:
    """
    K-스타트업(k-startup.go.kr)에서 창업지원·공모전 정보를 크롤링합니다.
    사용자가 "창업 공모전 찾아줘", "K-스타트업 지원사업 알려줘" 처럼 외부 공모전을 요청할 때 사용하세요.

    Args:
        query: 검색 키워드 (예: "창업", "공모전", "AI")
        n_results: 반환할 최대 결과 수

    Returns:
        공모전/창업지원 검색 결과 문자열
    """
    try:
        from rag.external_crawler import crawl_kstartup_contest
        results = crawl_kstartup_contest(query=query, max_results=n_results)
        if not results:
            return (
                f"🔍 '{query}' 관련 K-스타트업 공모전을 찾지 못했습니다.\n\n"
                "K-스타트업(https://www.k-startup.go.kr)에서 직접 확인해보세요."
            )
        _store_external_results(results, "contest")
        items = _format_external_items(results, n_results)
        header = (
            f"🚀 **'{query}' 관련 창업지원/공모전** (K-스타트업 기준)\n"
            f"   수집 {len(results)}건\n"
            f"{'─' * 40}\n\n"
        )
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 지원 마감일을 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 정확한 모집 조건은 반드시 K-스타트업 원문에서 재확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ K-스타트업 공모전 검색 실패: {e}"


@tool
def search_wevity_contest(query: str = "", n_results: int = 8) -> str:
    """
    위티(wevity.com)에서 대학생 공모전·대외활동을 실시간 크롤링합니다.
    사용자가 "공모전 추천해줘", "대외활동 찾아줘", "AI 공모전 알려줘", "SW 공모전" 처럼
    대학생 공모전·대외활동 정보를 요청하면 사용하세요.
    K-스타트업과 달리 일반 대학생 대상 공모전·해커톤·대외활동이 중심입니다.

    Args:
        query: 검색 키워드 (예: "AI", "소프트웨어", "해커톤", "" 전체 목록)
        n_results: 반환할 최대 결과 수

    Returns:
        공모전/대외활동 검색 결과 문자열
    """
    try:
        from rag.external_crawler import crawl_wevity_contest
        results = crawl_wevity_contest(query=query, max_results=n_results)
        if not results:
            return (
                "🔍 위티에서 공모전 정보를 가져오지 못했습니다.\n\n"
                "위티(https://www.wevity.com)에서 직접 검색해보세요.\n"
                "또는 저장된 공모전 샘플 데이터를 로드해서 검색할 수 있습니다."
            )
        _store_external_results(results, "contest")
        items = _format_external_items(results, n_results)
        label = f"'{query}' " if query else ""
        header = (
            f"🏆 **{label}대학생 공모전·대외활동** (위티 실시간)\n"
            f"   수집 {len(results)}건\n"
            f"{'─' * 40}\n\n"
        )
        footer = (
            "\n\n💡 **다음 추천 행동**\n"
            "- 마감일을 캘린더나 과제로 등록할 수 있습니다.\n"
            "- 정확한 지원 조건은 위티(wevity.com) 원문에서 확인하세요."
        )
        return header + "\n\n".join(items) + footer
    except Exception as e:
        return f"❌ 위티 공모전 검색 실패: {e}"


STUDENT_INFO_TOOLS = [
    search_student_info,
    search_personalized_student_info,
    search_student_info_live,
    search_transfer_by_school,
    search_scholarship_policy,
    search_job_intern,
    search_contest_external,
    search_wevity_contest,
    load_student_info_data,
    get_student_info_stats,
]
