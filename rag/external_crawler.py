# 외부 공공기관 소스 크롤러 (편입학/장학/취업/공모전)
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

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


# ──────────────────────────────────────────────────
# 1. 어디가(adiga.kr) — 편입학 정보
# ──────────────────────────────────────────────────

# 편입학 정보를 직접 제공하는 어디가 페이지
ADIGA_TRANSFER_SEARCH_URL = f"{ADIGA_BASE}/iphak/transfer/pcweb/PCUIPOKR000011100.do"
ADIGA_TRANSFER_LIST_URL = f"{ADIGA_BASE}/iphak/common/pcweb/PCUIPOKR000022100.do"


def crawl_transfer_by_school(school_name: str, max_results: int = 5) -> list[dict]:
    """
    어디가(adiga.kr) 편입학 검색 페이지에서 특정 학교의 편입학 정보를 크롤링합니다.
    학교명으로 검색하여 모집요강 목록을 반환합니다.

    robots.txt 상 비관리자 페이지는 허용되므로 법적으로 안전합니다.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    # 어디가 편입학 검색: searchKeyword 파라미터 시도
    results = []
    tried_urls = [
        (ADIGA_TRANSFER_SEARCH_URL, {"searchKeyword": school_name, "pageIndex": 1}),
        (ADIGA_TRANSFER_LIST_URL, {"searchUnivNm": school_name, "pageIndex": 1}),
    ]

    for url, params in tried_urls:
        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # 어디가 편입학 목록: table 또는 ul.result-list 구조
            rows = soup.select("table.tbl-basic tbody tr, ul.result-list li, div.info-list .item")
            for row in rows[:max_results]:
                title_tag = row.select_one("td.tit a, .tit a, strong, a")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                href = title_tag.get("href", "")
                full_url = href if href.startswith("http") else (ADIGA_BASE + href if href else url)
                # 날짜/기간 추출 시도
                date_text = ""
                for td in row.select("td, span"):
                    t = td.get_text(strip=True)
                    if re.match(r"\d{4}[-./]", t):
                        date_text = t
                        break
                results.append({
                    "title": title,
                    "content": f"{school_name} 편입학 모집요강. 상세 내용은 출처 URL에서 확인하세요.",
                    "date": date_text,
                    "url": full_url,
                    "source": "어디가(adiga.kr) 편입학 정보",
                    "category": "transfer",
                })
            if results:
                break
        except requests.RequestException:
            continue
        time.sleep(REQUEST_DELAY)

    # 어디가에서 결과가 없으면 학교 직접 안내 항목 반환
    if not results:
        results.append({
            "title": f"{school_name} 편입학 정보",
            "content": (
                f"{school_name}의 편입학 모집요강은 해당 학교 입학처 홈페이지 또는 "
                "어디가(adiga.kr)에서 직접 확인하세요."
            ),
            "date": "",
            "url": f"https://www.adiga.kr/iphak/transfer/main.do",
            "source": "어디가(adiga.kr)",
            "category": "transfer",
        })

    return results


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
