"""
CampusAgent - 공지사항 웹 크롤러
- 인하공업전문대학 학과 공지사항 크롤링 (K2Web BBS)
- 인하공업전문대학 대표 홈페이지 공지사항 크롤링 (combBbs)
- requests + BeautifulSoup 기반 정적 크롤링
- 기존 RAG 파이프라인(loader → chunker → embedder)과 호환되는 dict 형식 반환
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import time
import json
import os
import re
import base64
from urllib.parse import quote
from datetime import datetime


# ──────────────────────────────────────
# 크롤링 설정
# ──────────────────────────────────────
BASE_URL = "https://www.inhatc.ac.kr"

# 학과별 게시판 설정 (확장 가능)
DEPARTMENT_BOARDS = {
    "cse": {
        "name": "컴퓨터시스템공학과",
        "board_code": "107",
        "path_prefix": "cse",
        "subview_id": "2206",
    },
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{BASE_URL}/",
}

REQUEST_DELAY = 1.0  # 서버 부하 방지를 위한 요청 간격 (초)


# ──────────────────────────────────────
# 메인 크롤러 함수
# ──────────────────────────────────────


def _build_enc_param(board_path: str, page: int = 1, search_keyword: Optional[str] = None) -> str:
    """K2Web 시스템의 enc 파라미터를 생성합니다."""
    query_str = f"page={page}&"
    if search_keyword:
        query_str += f"srchColumn=sj&srchWrd={quote(search_keyword)}&"
    
    inner_url = quote(f"{board_path}?{query_str}", safe='')
    raw = f"fnct1|@@|{inner_url}"
    return base64.b64encode(raw.encode()).decode()


def crawl_notice_list(
    department: str = "cse",
    pages: int = 3,
    search_keyword: Optional[str] = None,
) -> List[dict]:
    """
    학과 공지사항 목록을 크롤링합니다.

    Args:
        department: 학과 코드 (기본값: "cse" = 컴퓨터시스템공학과)
        pages: 크롤링할 페이지 수 (기본값: 3)
        search_keyword: 게시판 내부 제목 검색어 (선택)

    Returns:
        공지사항 목록 [{title, date, url, views, is_pinned}, ...]
    """
    board = DEPARTMENT_BOARDS.get(department)
    if not board:
        print(f"⚠️ 지원하지 않는 학과 코드: {department}")
        return []

    board_code = board["board_code"]
    path_prefix = board["path_prefix"]
    subview_id = board["subview_id"]
    dept_name = board["name"]
    board_path = f"/bbs/{path_prefix}/{board_code}/artclList.do"

    all_notices = []
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    for page_num in range(1, pages + 1):
        # K2Web enc 방식으로 목록 페이지 접근
        enc = _build_enc_param(board_path, page_num, search_keyword)
        url = f"{BASE_URL}/{path_prefix}/{subview_id}/subview.do"

        print(f"📡 [{dept_name}] 페이지 {page_num}/{pages} 크롤링 중...")

        try:
            resp = session.get(url, params={"enc": enc}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ 페이지 {page_num} 요청 실패: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # artclView를 포함하는 링크 찾기 (K2Web 게시판 공통)
        view_links = soup.select('a[href*="artclView"]')

        for link_tag in view_links:
            href = link_tag.get("href", "")
            if not href:
                continue

            # 제목 추출
            title_tag = link_tag.select_one("strong")
            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)

            if not title or len(title) < 2:
                continue

            # 부모 요소에서 메타 정보 추출
            li = link_tag.find_parent("li") or link_tag.find_parent("div")
            date_text = ""
            views_text = ""

            if li:
                spans = li.select("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if _looks_like_date(text):
                        date_text = _normalize_date(text)
                    elif text.isdigit():
                        views_text = text

            # 고정 공지 여부 (첫 번째 공지 등)
            is_pinned = bool(link_tag.find_parent(class_=re.compile(r"noti|notice|pin")))

            # 절대 URL 생성
            full_url = href if href.startswith("http") else BASE_URL + href

            all_notices.append({
                "title": title,
                "date": date_text,
                "url": full_url,
                "views": views_text,
                "is_pinned": is_pinned,
                "department": dept_name,
            })

        if page_num < pages:
            time.sleep(REQUEST_DELAY)

    # 중복 제거 (URL 기준)
    seen_urls = set()
    unique_notices = []
    for notice in all_notices:
        if notice["url"] not in seen_urls:
            seen_urls.add(notice["url"])
            unique_notices.append(notice)

    print(f"✅ [{dept_name}] 총 {len(unique_notices)}건의 공지 목록 수집 완료")
    return unique_notices


def crawl_notice_detail(url: str) -> dict:
    """
    공지사항 상세 페이지의 본문 내용을 크롤링합니다.
    K2Web의 board-view 구조: .view-con (본문), .view-info (메타), .view-file (첨부)

    Args:
        url: 공지사항 상세 페이지 URL

    Returns:
        {title, content, date, attachments} 딕셔너리
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 상세 페이지 요청 실패 ({url}): {e}")
        return {"title": "", "content": "", "date": "", "attachments": []}

    soup = BeautifulSoup(resp.text, "html.parser")

    # 제목 추출 (.view-title 또는 .view-info 내)
    title = ""
    title_area = soup.select_one(".view-title")
    if title_area:
        title = title_area.get_text(strip=True)
    else:
        # view-info에서 제목 추출 시도
        info_area = soup.select_one(".view-info")
        if info_area:
            # 글번호 이후의 텍스트가 제목
            text = info_area.get_text(strip=True)
            # "글번호NNNNN제목..." 패턴
            match = re.search(r"글번호\d+(.*)", text)
            if match:
                title = match.group(1).strip()

    # 날짜 추출
    date_text = ""
    info_area = soup.select_one(".view-info")
    if info_area:
        dds = info_area.select("dd")
        for dd in dds:
            text = dd.get_text(strip=True)
            if _looks_like_date(text):
                date_text = _normalize_date(text)
                break

    # 본문 내용 추출 (.view-con)
    content = ""
    content_area = soup.select_one(".view-con")
    if content_area:
        content = _html_to_text(content_area)

    # 첨부파일 추출 (.view-file)
    attachments = []
    file_area = soup.select_one(".view-file")
    if file_area:
        for a_tag in file_area.select("a"):
            file_name = a_tag.get_text(strip=True)
            file_href = a_tag.get("href", "")
            if file_name and file_href:
                attachments.append({
                    "name": file_name,
                    "url": file_href if file_href.startswith("http") else BASE_URL + file_href,
                })

    return {
        "title": title,
        "content": content.strip(),
        "date": date_text,
        "attachments": attachments,
    }


def crawl_full_notices(
    department: str = "cse",
    pages: int = 3,
    max_detail: int = 30,
    save_json: bool = True,
) -> List[dict]:
    """
    공지사항 목록 + 상세 내용을 모두 크롤링하여 RAG 파이프라인 호환 형식으로 반환합니다.

    Args:
        department: 학과 코드 (기본값: "cse")
        pages: 목록 크롤링 페이지 수 (기본값: 3)
        max_detail: 상세 내용을 가져올 최대 공지 수 (기본값: 30)
        save_json: 크롤링 결과를 JSON 파일로 저장할지 여부

    Returns:
        RAG 파이프라인 호환 문서 리스트 [{id, title, content, date, category, source, full_text}, ...]
    """
    # 1. 목록 크롤링
    notice_list = crawl_notice_list(department=department, pages=pages)
    if not notice_list:
        return []

    # 2. 상세 내용 크롤링 (최대 max_detail 건)
    documents = []
    target_notices = notice_list[:max_detail]

    print(f"\n📄 상세 내용 크롤링 시작 ({len(target_notices)}건)...")

    for idx, notice in enumerate(target_notices):
        print(f"  [{idx + 1}/{len(target_notices)}] {notice['title'][:40]}...")

        detail = crawl_notice_detail(notice["url"])
        time.sleep(REQUEST_DELAY)

        # 상세 페이지에서 가져온 제목/날짜가 더 정확할 수 있음
        final_title = detail["title"] if detail["title"] else notice["title"]
        final_date = detail["date"] if detail["date"] else notice["date"]
        content = detail["content"] if detail["content"] else notice["title"]

        category = _guess_category(final_title, content)

        doc = {
            "id": f"crawl_{department}_{idx}",
            "title": final_title,
            "content": content,
            "date": final_date,
            "category": category,
            "source": notice.get("department", "학과 홈페이지"),
            "url": notice["url"],
            "views": notice.get("views", ""),
            "attachments": detail.get("attachments", []),
            "full_text": f"[{category}] {final_title} - {content}",
            "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        documents.append(doc)

    print(f"✅ 총 {len(documents)}건의 공지사항 크롤링 완료")

    # 3. JSON 파일로 저장 (선택)
    if save_json and documents:
        save_path = f"data/crawled_notices_{department}.json"
        os.makedirs("data", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        print(f"💾 크롤링 결과 저장: {save_path}")

    return documents


# ──────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────


def _html_to_text(element) -> str:
    """BeautifulSoup 엘리먼트를 깨끗한 텍스트로 변환 (줄바꿈 보존)"""
    # <br> 태그를 줄바꿈으로 변환
    for br in element.find_all("br"):
        br.replace_with("\n")

    # <p>, <div>, <li> 등 블록 요소 뒤에 줄바꿈 추가
    for tag in element.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.append("\n")

    # 텍스트 추출 후 정리
    text = element.get_text()
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    return text


def _looks_like_date(text: str) -> bool:
    """텍스트가 날짜처럼 보이는지 확인"""
    # YYYY.MM.DD 또는 YYYY-MM-DD 패턴
    return bool(re.match(r"^\d{4}[.\-/]\d{2}[.\-/]\d{2}\.?$", text.strip()))


def _normalize_date(date_str: str) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 정규화"""
    clean = date_str.strip().rstrip(".")
    clean = re.sub(r"[./]", "-", clean)
    return clean


def _guess_category(title: str, content: str) -> str:
    """제목과 내용으로 카테고리 자동 추정"""
    text = (title + " " + content).lower()

    category_keywords = {
        "장학": ["장학금", "장학", "학비", "등록금", "감면", "국가근로"],
        "취업": ["취업", "채용", "인턴", "현장실습", "산학", "기업", "모집"],
        "학사": [
            "수강", "학점", "성적", "졸업", "이수", "학사일정",
            "중간고사", "기말고사", "시험", "수업", "교과",
            "캡스톤", "교육과정", "개강", "종강", "휴강",
        ],
        "행사": ["특강", "세미나", "워크숍", "행사", "대회", "컨퍼런스", "공모전"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            return category

    return "일반"


def search_notices_live(
    query: str,
    department: str = "cse",
    pages: int = 1,
    max_results: Optional[int] = None,
) -> List[dict]:
    """
    실시간 크롤링 + 검색: 학과 홈페이지 검색 기능을 이용하여 공지사항을 수집한 뒤 반환합니다.
    RAG DB 저장 없이, 바로 크롤링 → 상세 내용 반환.

    Args:
        query: 사용자 입력 쿼리 (예: "장학금 공지사항 찾아줘", "수강 변경", "졸업 요건")
        department: 학과 코드 (기본값: "cse")
        pages: 크롤링할 페이지 수 (기본값: 1)
        max_results: 최대 반환 결과 수 (기본값: None = 페이지 전체)

    Returns:
        검색 결과 [{title, content, date, category, url, attachments}, ...]
    """
    # 1. 쿼리에서 가장 중요한 검색어 하나를 추출합니다
    keywords = _extract_keywords(query)
    main_keyword = keywords[0] if keywords else query.replace(" ", "")

    print(f"📡 '{main_keyword}' 키워드로 홈페이지 서버 사이드 검색 시도 중...")

    # 2. 서버 사이드 검색으로 목록 크롤링
    notice_list = crawl_notice_list(department=department, pages=pages, search_keyword=main_keyword)

    if not notice_list:
        print(f"⚠️ 서버에 '{main_keyword}'로 검색된 공지가 없습니다.")
        return []

    matched = notice_list[:max_results] if max_results is not None else notice_list
    print(f"🔍 홈페이지 서버에서 '{main_keyword}' 검색 → {len(matched)}건 수집 완료")

    # 3. 검색된 공지의 상세 내용 크롤링
    results = []
    for idx, notice in enumerate(matched):
        print(f"  [{idx + 1}/{len(matched)}] {notice['title'][:40]}...")
        detail = crawl_notice_detail(notice["url"])
        time.sleep(REQUEST_DELAY)

        final_title = detail["title"] if detail["title"] else notice["title"]
        final_date = detail["date"] if detail["date"] else notice["date"]
        content = detail["content"] if detail["content"] else notice["title"]
        category = _guess_category(final_title, content)

        results.append({
            "title": final_title,
            "content": content,
            "date": final_date,
            "category": category,
            "url": notice["url"],
            "views": notice.get("views", ""),
            "attachments": detail.get("attachments", []),
        })

    return results


def _extract_keywords(query: str) -> List[str]:
    """검색 쿼리에서 불용어를 제거하고 의미 있는 단어를 순서대로 반환합니다."""
    stopwords = {
        "공지", "공지사항", "찾아줘", "검색", "알려줘", "보여줘",
        "관련", "최신", "해줘", "좀", "있어", "뭐", "어떤",
        "대학", "학과", "확인", "조회",
    }

    words = query.replace(",", " ").split()
    keywords = [w for w in words if w not in stopwords and len(w) >= 2]

    return keywords if keywords else [query]


# ──────────────────────────────────────────────────────────
# 대표 홈페이지 공지사항 크롤러 (combBbs 시스템)
# ──────────────────────────────────────────────────────────

SCHOOL_NOTICE_LIST_URL = f"{BASE_URL}/combBbs/kr/2/list.do"


def crawl_school_notice_list(
    pages: int = 1,
    search_keyword: Optional[str] = None,
) -> List[dict]:
    """
    인하공업전문대학 대표 홈페이지 공지사항 목록을 크롤링합니다.
    combBbs 시스템의 table.board-table 구조를 파싱합니다.

    Args:
        pages: 크롤링할 페이지 수 (기본값: 1)
        search_keyword: 제목 검색어 (선택)

    Returns:
        공지사항 목록 [{title, date, url, views, is_pinned, department}, ...]
    """
    all_notices = []
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    for page_num in range(1, pages + 1):
        params: dict = {"page": page_num}
        if search_keyword:
            params["findType"] = "sj"
            params["findWord"] = search_keyword

        print(f"📡 [대표홈페이지] 페이지 {page_num}/{pages} 크롤링 중...")

        try:
            resp = session.get(SCHOOL_NOTICE_LIST_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ 페이지 {page_num} 요청 실패: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # combBbs 테이블 구조 파싱
        table = soup.select_one("table.board-table")
        if not table:
            print(f"⚠️ 페이지 {page_num}에서 게시판 테이블을 찾을 수 없습니다.")
            continue

        rows = table.select("tbody tr")
        for row in rows:
            # 번호
            td_no = row.select_one("td.td-num, td:first-child")
            no_text = td_no.get_text(strip=True) if td_no else ""
            is_pinned = no_text in ("공지", "필독", "")

            # 제목 + URL
            td_subject = row.select_one("td.td-subject")
            if not td_subject:
                continue

            link_tag = td_subject.select_one("a")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            # href에서 URL 추출 (javascript:jf_combBbs_view(...) 패턴)
            href = link_tag.get("href", "")

            if href.startswith("javascript:"):
                # jf_combBbs_view('kr','2','17','107973') 패턴
                match = re.search(r"jf_combBbs_view\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'", href)
                if match:
                    lang, board_id, col_id, art_id = match.groups()
                    full_url = f"{BASE_URL}/combBbs/{lang}/{board_id}/{col_id}/{art_id}/view.do"
                else:
                    continue
            elif href and href != "#":
                full_url = href if href.startswith("http") else BASE_URL + href
            else:
                continue

            # 날짜
            td_date = row.select_one("td.td-date")
            date_text = ""
            if td_date:
                raw_date = td_date.get_text(strip=True)
                # "2026.04.22." → "2026-04-22"
                cleaned = raw_date.rstrip(".")
                if re.match(r"^\d{4}\.\d{2}\.\d{2}$", cleaned):
                    date_text = cleaned.replace(".", "-")
                else:
                    date_text = cleaned

            # 조회수
            td_views = row.select_one("td.td-access, td.td-count, td.td-view")
            views_text = ""
            if td_views:
                views_text = td_views.get_text(strip=True)
            else:
                # 테이블에서 숫자만 있는 td 찾기 (조회수 위치 추정)
                tds = row.select("td")
                if len(tds) >= 4:
                    candidate = tds[-2].get_text(strip=True)
                    if candidate.isdigit():
                        views_text = candidate

            all_notices.append({
                "title": title,
                "date": date_text,
                "url": full_url,
                "views": views_text,
                "is_pinned": is_pinned,
                "department": "인하공업전문대학(대표)",
            })

        if page_num < pages:
            time.sleep(REQUEST_DELAY)

    # 중복 제거 (URL 기준)
    seen_urls = set()
    unique_notices = []
    for notice in all_notices:
        if notice["url"] not in seen_urls:
            seen_urls.add(notice["url"])
            unique_notices.append(notice)

    print(f"✅ [대표홈페이지] 총 {len(unique_notices)}건의 공지 목록 수집 완료")
    return unique_notices


def crawl_school_notice_detail(url: str) -> dict:
    """
    대표 홈페이지 공지사항 상세 페이지의 본문 내용을 크롤링합니다.
    combBbs 시스템의 board-view 구조를 파싱합니다.

    Args:
        url: 공지사항 상세 페이지 URL

    Returns:
        {title, content, date, attachments} 딕셔너리
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 상세 페이지 요청 실패 ({url}): {e}")
        return {"title": "", "content": "", "date": "", "attachments": []}

    soup = BeautifulSoup(resp.text, "html.parser")

    # 제목 추출
    title = ""
    # combBbs는 .board-view-info h2 또는 .view-title 사용
    for sel in [".board-view-info h2", ".view-title", "h2.bv-title", ".board-view h2"]:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get_text(strip=True)
            break

    if not title:
        # 제목이 dl/dt 구조일 수도 있음
        dt = soup.select_one(".board-view-info dt, .bv-info dt")
        if dt and "제목" in dt.get_text():
            dd = dt.find_next_sibling("dd")
            if dd:
                title = dd.get_text(strip=True)

    # 날짜 추출
    date_text = ""
    info_area = soup.select_one(".board-view-info, .bv-info, .view-info")
    if info_area:
        # dd 태그들에서 날짜 패턴 찾기
        for dd in info_area.select("dd, span, li"):
            text = dd.get_text(strip=True)
            if _looks_like_date(text):
                date_text = _normalize_date(text)
                break
        # 날짜를 못 찾으면 전체 텍스트에서 패턴 추출
        if not date_text:
            full_text = info_area.get_text()
            date_match = re.search(r"(\d{4}[.\-/]\d{2}[.\-/]\d{2})", full_text)
            if date_match:
                date_text = _normalize_date(date_match.group(1))

    # 본문 내용 추출
    content = ""
    for sel in [".view-con", ".board-view-con", ".bv-con", ".board-view-content"]:
        content_area = soup.select_one(sel)
        if content_area:
            content = _html_to_text(content_area)
            break

    # 첨부파일 추출
    attachments = []
    for sel in [".view-file", ".board-view-file", ".bv-file"]:
        file_area = soup.select_one(sel)
        if file_area:
            for a_tag in file_area.select("a"):
                file_name = a_tag.get_text(strip=True)
                file_href = a_tag.get("href", "")
                if file_name and file_href:
                    attachments.append({
                        "name": file_name,
                        "url": file_href if file_href.startswith("http") else BASE_URL + file_href,
                    })
            break

    return {
        "title": title,
        "content": content.strip(),
        "date": date_text,
        "attachments": attachments,
    }


def search_school_notices_live(
    query: str,
    pages: int = 1,
    max_results: Optional[int] = None,
) -> List[dict]:
    """
    대표 홈페이지 공지사항을 실시간 크롤링 + 검색합니다.
    학교 메인 공지를 검색 기능으로 크롤링한 뒤 상세 내용을 반환합니다.

    Args:
        query: 사용자 입력 쿼리 (예: "장학금", "등록금", "학사일정")
        pages: 크롤링할 페이지 수 (기본값: 1)
        max_results: 최대 반환 결과 수 (기본값: None = 페이지 전체)

    Returns:
        검색 결과 [{title, content, date, category, url, attachments}, ...]
    """
    keywords = _extract_keywords(query)
    main_keyword = keywords[0] if keywords else query.replace(" ", "")

    print(f"📡 [대표홈페이지] '{main_keyword}' 키워드로 서버 검색 시도 중...")

    # 서버 사이드 검색으로 목록 크롤링
    notice_list = crawl_school_notice_list(pages=pages, search_keyword=main_keyword)

    if not notice_list:
        print(f"⚠️ 대표홈페이지에 '{main_keyword}'로 검색된 공지가 없습니다.")
        return []

    matched = notice_list[:max_results] if max_results is not None else notice_list
    print(f"🔍 대표홈페이지에서 '{main_keyword}' 검색 → {len(matched)}건 수집 완료")

    # 검색된 공지의 상세 내용 크롤링
    results = []
    for idx, notice in enumerate(matched):
        print(f"  [{idx + 1}/{len(matched)}] {notice['title'][:40]}...")
        detail = crawl_school_notice_detail(notice["url"])
        time.sleep(REQUEST_DELAY)

        final_title = detail["title"] if detail["title"] else notice["title"]
        final_date = detail["date"] if detail["date"] else notice["date"]
        content = detail["content"] if detail["content"] else notice["title"]
        category = _guess_category(final_title, content)

        results.append({
            "title": final_title,
            "content": content,
            "date": final_date,
            "category": category,
            "url": notice["url"],
            "views": notice.get("views", ""),
            "attachments": detail.get("attachments", []),
            "source": "대표홈페이지",
        })

    return results


# ──────────────────────────────────────
# CLI 테스트용
# ──────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("🕷️ CampusAgent 실시간 크롤링 검색 테스트")
    print("=" * 50)

    print("\n--- 학과 공지사항 검색 ---")
    results = search_notices_live(query="장학금", pages=1, max_results=3)
    for doc in results:
        print(f"\n📌 {doc['title']}")
        print(f"   📅 {doc['date']} | 📂 {doc['category']}")
        print(f"   📄 {doc['content'][:100]}...")

    print("\n--- 대표홈페이지 공지사항 검색 ---")
    results2 = search_school_notices_live(query="장학금", pages=1, max_results=3)
    for doc in results2:
        print(f"\n📌 {doc['title']}")
        print(f"   📅 {doc['date']} | 📂 {doc['category']}")
        print(f"   📄 {doc['content'][:100]}...")
