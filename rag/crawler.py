"""
CampusAgent - 학과 공지사항 웹 크롤러
- 인하공업전문대학 컴퓨터시스템공학과 공지사항 크롤링
- requests + BeautifulSoup 기반 정적 크롤링
- K2Web 기반 BBS 시스템에 맞춘 파싱 로직
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


def _build_enc_param(board_path: str, page: int = 1) -> str:
    """K2Web 시스템의 enc 파라미터를 생성합니다."""
    inner_url = quote(f"{board_path}?page={page}&", safe='')
    raw = f"fnct1|@@|{inner_url}"
    return base64.b64encode(raw.encode()).decode()


def crawl_notice_list(
    department: str = "cse",
    pages: int = 3,
) -> List[dict]:
    """
    학과 공지사항 목록을 크롤링합니다.

    Args:
        department: 학과 코드 (기본값: "cse" = 컴퓨터시스템공학과)
        pages: 크롤링할 페이지 수 (기본값: 3)

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
        enc = _build_enc_param(board_path, page_num)
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


# ──────────────────────────────────────
# CLI 테스트용
# ──────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("🕷️ CampusAgent 학과 공지사항 크롤러 테스트")
    print("=" * 50)

    docs = crawl_full_notices(department="cse", pages=1, max_detail=3)
    for doc in docs:
        print(f"\n📌 {doc['title']}")
        print(f"   📅 {doc['date']} | 📂 {doc['category']}")
        print(f"   📄 {doc['content'][:100]}...")
