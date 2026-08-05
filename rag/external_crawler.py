# 외부 공공기관 소스 크롤러 (편입학/장학/취업/공모전)
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

REQUEST_DELAY = 1.0

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

ADIGA_BASE = "https://www.adiga.kr"
KSTARTUP_BASE = "https://www.k-startup.go.kr"
WEVITY_BASE = "https://www.wevity.com"


# ──────────────────────────────────────────────────
# 1. 대학 편입학 정보
# ──────────────────────────────────────────────────

ADIGA_ADMISSION_INFO_URL = (
    f"{ADIGA_BASE}/ucp/prc/uni/admssUnivView.do?menuId=PCPRCINF2000"
)

KNOWN_UNIVERSITY_ADMISSION_URLS = {
    "인하대": ("인하대학교", "https://admission.inha.ac.kr"),
    "인하대학교": ("인하대학교", "https://admission.inha.ac.kr"),
    "인하공전": ("인하공업전문대학", "https://www.inhatc.ac.kr/ipsi"),
    "인하공업전문대학": ("인하공업전문대학", "https://www.inhatc.ac.kr/ipsi"),
}


def _known_admission_site(school_name: str) -> tuple[str, str]:
    """학교명 별칭을 공식 입학처 URL로 변환합니다."""
    normalized = school_name.replace(" ", "")
    for alias, info in KNOWN_UNIVERSITY_ADMISSION_URLS.items():
        if alias.replace(" ", "") in normalized or normalized in alias.replace(" ", ""):
            return info
    return school_name, ""


def crawl_transfer_by_school(school_name: str, max_results: int = 5) -> list[dict]:
    """
    특정 학교의 편입학 확인 경로를 반환합니다.

    현재 어디가 공개 메뉴는 수시/정시 전형정보 중심이라 편입학 전용 목록을
    안정적으로 제공하지 않습니다. 편입학은 대학별 입학처 공식 페이지 확인을
    우선 안내하고, 어디가의 일반 전형정보 페이지는 보조 확인 경로로 제공합니다.
    """
    results = []

    official_name, admission_url = _known_admission_site(school_name)
    if admission_url:
        results.append({
            "title": f"{official_name} 입학처 편입학 확인",
            "content": (
                f"{official_name} 편입학 모집요강은 대학 입학처 공식 홈페이지에서 "
                "최신 공지와 PDF 모집요강을 확인하는 것이 가장 정확합니다. "
                "현재 어디가 공개 메뉴에서는 편입학 전용 목록을 확인하지 못했습니다."
            ),
            "date": "",
            "url": admission_url,
            "source": f"{official_name} 입학처",
            "category": "transfer",
        })

    query = quote_plus(f"{school_name} 편입학 모집요강 입학처")
    results.append({
        "title": f"{school_name} 어디가 전형정보 확인",
        "content": (
            "어디가(adiga.kr)는 현재 공개 메뉴 기준으로 수시/정시 전형정보와 "
            "대학별 입시정보를 제공합니다. 편입학 모집요강은 대학 입학처 "
            f"또는 검색어 '{school_name} 편입학 모집요강 입학처'로 재확인하세요."
        ),
        "date": "",
        "url": ADIGA_ADMISSION_INFO_URL,
        "source": "어디가(adiga.kr) 전형정보",
        "category": "transfer",
    })
    results.append({
        "title": f"{school_name} 편입학 공식 모집요강 검색어",
        "content": (
            "학교별 편입학 일정과 지원 자격은 매년 바뀌므로 대학 입학처의 "
            "최신 모집요강 원문을 우선 확인해야 합니다."
        ),
        "date": "",
        "url": f"https://www.google.com/search?q={query}",
        "source": "공식 입학처 검색 안내",
        "category": "transfer",
    })

    return results[:max_results]


# ──────────────────────────────────────────────────
# 2. 온통청년(youthcenter.go.kr) — 청년정책/장학 API
# 엔드포인트: /go/ythip/getPlcy, 파라미터: apiKeyNm
# ──────────────────────────────────────────────────

YOUTH_API_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"


def fetch_youth_policy(
    query: str,
    api_key: str,
    page: int = 1,
    display: int = 5,
) -> list[dict]:
    """
    온통청년 청년정책 API로 장학금·청년지원 정책을 검색합니다.
    API 키: youthcenter.go.kr 마이페이지 → OPEN API에서 확인.

    Returns: [{title, content, date, url, source, category}, ...]
    """
    if not api_key:
        return []

    params = {
        "apiKeyNm": api_key,
        "pageNum": page,
        "pageSize": display,
        "rtnType": "json",
        "plcyNm": query,
    }
    try:
        resp = requests.get(
            YOUTH_API_URL,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    policy_list = []
    try:
        items = data.get("result", {}).get("youthPolicyList", [])
    except (AttributeError, TypeError):
        items = []

    for item in items:
        title = item.get("plcyNm", "")
        content = item.get("plcyExplnCn", "") or item.get("plcySprtCn", "")
        institution = item.get("sprvsnInstCdNm", "") or item.get("operInstCdNm", "")
        category_large = item.get("lclsfNm", "")
        policy_no = item.get("plcyNo", "")
        url = f"https://www.youthcenter.go.kr/plcyInfo/getPlcyInfo.do?plcyNo={policy_no}" if policy_no else "https://www.youthcenter.go.kr"

        summary = content[:300] if content else "상세 내용은 출처 URL에서 확인하세요."
        if category_large:
            summary = f"분류: {category_large}\n{summary}"

        policy_list.append({
            "title": title,
            "content": summary,
            "date": "",
            "url": url,
            "source": f"온통청년 ({institution})" if institution else "온통청년(youthcenter.go.kr)",
            "category": "policy",
        })

    return policy_list


# ──────────────────────────────────────────────────
# 3. 워크넷(work24.go.kr) — 공채속보 API (210L21)
# 신입·인턴 채용공고 목록, XML 응답
# ──────────────────────────────────────────────────

WORKNET_JOB_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"


def _fmt_date(yyyymmdd: str) -> str:
    """YYYYMMDD → YYYY-MM-DD 변환"""
    if len(yyyymmdd) == 8:
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd


def fetch_worknet_jobs(
    query: str,
    api_key: str,
    page: int = 1,
    display: int = 5,
) -> list[dict]:
    """
    워크넷 공채속보 API(210L21)로 신입·인턴 채용공고를 검색합니다.
    API 키: www.work24.go.kr 포털에서 발급.
    XML 응답 전용.

    Returns: [{title, content, date, url, source, category}, ...]
    """
    if not api_key:
        return []

    params = {
        "authKey": api_key,
        "callTp": "L",
        "returnType": "XML",
        "startPage": page,
        "display": display,
        "empWantedCareerCd": "30|40",  # 신입|인턴
        "sortField": "regDt",
        "sortOrderBy": "desc",
    }
    if query:
        params["empWantedTitle"] = query

    try:
        resp = requests.get(
            WORKNET_JOB_URL,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []

    job_list = []
    for item in root.findall("dhsOpenEmpInfo"):
        title = (item.findtext("empWantedTitle") or "").strip()
        if not title:
            continue
        company = (item.findtext("empBusiNm") or "").strip()
        company_type = (item.findtext("coClcdNm") or "").strip()
        emp_type = (item.findtext("empWantedTypeNm") or "").strip()
        start_dt = _fmt_date(item.findtext("empWantedStdt") or "")
        end_dt = _fmt_date(item.findtext("empWantedEndt") or "")
        detail_url = (item.findtext("empWantedHomepgDetail") or "https://www.work24.go.kr").strip()

        content_parts = []
        if company:
            content_parts.append(f"기업: {company}")
        if company_type:
            content_parts.append(f"유형: {company_type}")
        if emp_type:
            content_parts.append(f"고용형태: {emp_type}")
        if end_dt:
            content_parts.append(f"마감: {end_dt}")

        job_list.append({
            "title": title,
            "content": "\n".join(content_parts) or "상세 내용은 출처 URL에서 확인하세요.",
            "date": end_dt,
            "url": detail_url,
            "source": f"워크넷 공채속보 ({company})" if company else "워크넷 공채속보(work24.go.kr)",
            "category": "contest",
        })

    return job_list


# ──────────────────────────────────────────────────
# 4. K-스타트업(k-startup.go.kr) — 공모전/창업지원 크롤링
# ──────────────────────────────────────────────────

# robots.txt: /bizpbanc-ongoing.do 는 Disallow에 없으므로 크롤링 가능
KSTARTUP_LIST_URL = (
    f"{KSTARTUP_BASE}/web/contents/bizpbanc-ongoing.do"
    "?schMenuNo=200130&bizPbancSe=NOTL&cclasCode=CCLAS9001"
)


def crawl_kstartup_contest(query: str = "", max_results: int = 5) -> list[dict]:
    """
    K-스타트업 창업지원포털의 모집중 사업공고를 크롤링합니다.
    query가 있으면 제목 포함 여부로 클라이언트 사이드 필터링합니다.

    robots.txt 기준 해당 경로는 허용됩니다.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        resp = session.get(KSTARTUP_LIST_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    items = soup.select("li.notice")

    for item in items:
        # 제목
        strong = item.select_one("strong.tit, strong, .tit")
        title = strong.get_text(strip=True) if strong else ""
        # scrap hidden input에도 제목이 있음
        if not title:
            hidden = item.select_one("input[name='scrap_list_bizPbancNm']")
            title = hidden.get("value", "") if hidden else ""
        if not title:
            continue

        # K-스타트업 공고 제목은 "모집", "공고" 등을 사용하므로
        # 제목 필터 없이 전체 반환 (이미 공모전/창업지원 특화 사이트)

        # 링크: javascript:go_view(ID) → 상세 URL 조립
        link_tag = item.select_one("a")
        href = link_tag.get("href", "") if link_tag else ""
        match = re.search(r"go_view\((\d+)\)", href)
        detail_url = (
            f"{KSTARTUP_BASE}/web/contents/bizpbanc-ongoing-view.do?bizPbancSn={match.group(1)}"
            if match
            else KSTARTUP_LIST_URL
        )

        # D-day, 기관, 분야
        spans = [s.get_text(strip=True) for s in item.select("span") if s.get_text(strip=True)]
        deadline = next((s for s in spans if re.match(r"D-\d+|D\+\d+|마감", s)), "")
        institution = next(
            (s for s in spans if s not in {deadline} and len(s) > 2 and not re.match(r"D[+-]", s)),
            "",
        )

        results.append({
            "title": title,
            "content": f"기관: {institution}\n마감: {deadline}\n상세 내용은 출처 URL에서 확인하세요.",
            "date": deadline,
            "url": detail_url,
            "source": f"K-스타트업 ({institution})" if institution else "K-스타트업(k-startup.go.kr)",
            "category": "contest",
        })

        if len(results) >= max_results:
            break

    return results


# ──────────────────────────────────────────────────
# 5. 위티(wevity.com) 대학생 공모전/대외활동
# ──────────────────────────────────────────────────

WEVITY_LIST_URL = f"{WEVITY_BASE}/?c=find&s=1&gub=1"


def crawl_wevity_contest(query: str = "", max_results: int = 8) -> list[dict]:
    """
    위티(wevity.com)에서 대학생 공모전·대외활동 목록을 크롤링합니다.
    query가 있으면 제목 포함 여부로 클라이언트 사이드 필터링합니다.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        resp = session.get(WEVITY_LIST_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # ul.list > li (top 헤더 행 제외)
    items = [li for li in soup.select("ul.list > li") if "top" not in li.get("class", [])]

    for item in items:
        # 제목: .tit > a
        link_tag = item.select_one(".tit a")
        if not link_tag:
            continue
        title = link_tag.get_text(separator=" ", strip=True)
        # 상태 스팬 텍스트 제거 (신규, SPECIAL 등)
        for span in link_tag.select("span.stat"):
            title = title.replace(span.get_text(strip=True), "").strip()

        if not title or len(title) < 4:
            continue
        if query and query.lower() not in title.lower():
            continue

        href = link_tag.get("href", "")
        url = href if href.startswith("http") else f"{WEVITY_BASE}/{href.lstrip('/?')}"
        if not href.startswith("http"):
            url = f"{WEVITY_BASE}/?{href.lstrip('?')}" if href.startswith("?") else f"{WEVITY_BASE}/{href}"

        # 분야
        sub_tit = item.select_one(".sub-tit")
        field = sub_tit.get_text(strip=True) if sub_tit else ""

        # 주최사
        organ = item.select_one(".organ")
        host = organ.get_text(strip=True) if organ else ""

        # 마감 (D-day)
        day_tag = item.select_one(".day")
        deadline = day_tag.get_text(separator=" ", strip=True) if day_tag else ""

        content = f"주최: {host}\n{field}\n마감: {deadline}\n상세 내용은 출처 URL에서 확인하세요."

        results.append({
            "title": title,
            "content": content,
            "date": deadline,
            "url": url,
            "source": f"위티 ({host})" if host else "위티(wevity.com)",
            "category": "contest",
        })

        if len(results) >= max_results:
            break

    return results
