"""
CampusAgent - 대학생 정보 검색 도구 테스트
"""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config.settings as settings
from mcp_servers.student_info_server import (
    STUDENT_INFO_KEYWORDS,
    _load_student_info_from_json,
    load_student_info_data,
    search_student_info,
    search_student_info_live,
    search_transfer_by_school,
    search_scholarship_policy,
    search_job_intern,
    search_contest_external,
)
import mcp_servers.student_info_server as student_info_server


@pytest.fixture(autouse=True)
def setup_test_chroma(tmp_path):
    test_chroma = str(tmp_path / "test_student_info_chroma")
    settings.CHROMA_DB_DIR = test_chroma

    import rag.embedder as emb
    import rag.retriever as ret

    emb.CHROMA_DB_DIR = test_chroma
    ret.CHROMA_DB_DIR = test_chroma
    yield
    try:
        if os.path.exists(test_chroma):
            shutil.rmtree(test_chroma, ignore_errors=True)
    except Exception:
        pass


def _sample_path():
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "student_info_samples.json",
    )


def test_load_student_info_json():
    docs = _load_student_info_from_json(_sample_path())
    assert len(docs) >= 6
    assert {"transfer", "policy", "contest"}.issubset({d["category"] for d in docs})
    assert "마감일" in docs[0]["full_text"]


def test_load_and_search_student_info():
    load_result = load_student_info_data.invoke({"filepath": _sample_path()})
    assert "대학생 정보 데이터 로드 완료" in load_result

    transfer_result = search_student_info.invoke({
        "query": "편입학 정보 알려줘",
        "category": "transfer",
        "n_results": 3,
    })
    assert "대학생 정보 검색 결과" in transfer_result
    assert "편입학" in transfer_result or "전공심화" in transfer_result

    policy_result = search_student_info.invoke({
        "query": "국가장학금 제도 찾아줘",
        "category": "policy",
        "n_results": 3,
    })
    assert "국가장학금" in policy_result or "국가제도" in policy_result

    contest_result = search_student_info.invoke({
        "query": "소프트웨어 공모전 추천해줘",
        "category": "contest",
        "n_results": 3,
    })
    assert "공모전" in contest_result or "대외활동" in contest_result


def test_student_info_keywords_defined():
    assert set(STUDENT_INFO_KEYWORDS.keys()) == {"transfer", "policy", "contest"}
    for kws in STUDENT_INFO_KEYWORDS.values():
        assert kws and all(isinstance(k, str) and k for k in kws)


def test_search_student_info_live_with_mocked_crawler(monkeypatch):
    """실시간 크롤러를 가짜로 대체하여 도구 흐름 검증 (네트워크 미사용)."""
    fake_payloads = {
        "편입": [
            {
                "title": "2026학년도 편입학 모집요강",
                "content": "전공심화 및 편입학 일반 안내. 모집학과, 제출서류 확인 필요.",
                "date": "2026-04-22",
                "url": "https://www.inhatc.ac.kr/combBbs/kr/2/107/999001/view.do",
                "category": "학사",
            }
        ],
        "전공심화": [],
        "국가장학금": [
            {
                "title": "국가장학금 신청 안내",
                "content": "한국장학재단 신청 기간 및 소득구간 안내.",
                "date": "2026-05-01",
                "url": "https://www.inhatc.ac.kr/combBbs/kr/2/107/999002/view.do",
                "category": "장학",
            }
        ],
        "장학금": [],
        "국가근로": [],
        "공모전": [],
        "현장실습": [],
        "인턴십": [],
    }

    def fake_search_school_notices_live(query, pages=1, max_results=None):
        return fake_payloads.get(query, [])

    import rag.crawler as crawler
    monkeypatch.setattr(
        crawler, "search_school_notices_live", fake_search_school_notices_live
    )
    student_info_server._LIVE_CACHE.clear()

    result = search_student_info_live.invoke({
        "query": "최신 편입학 모집요강 알려줘",
        "category": "transfer",
        "n_results": 3,
    })
    assert "실시간 크롤링" in result
    assert "편입학 모집요강" in result

    # 자동 추정 (카테고리 미지정)
    student_info_server._LIVE_CACHE.clear()
    auto = search_student_info_live.invoke({
        "query": "국가장학금 새로 나온 거 있어?",
        "category": "",
        "n_results": 3,
    })
    assert "국가장학금" in auto


def test_search_transfer_by_school_with_mock(monkeypatch):
    """편입학 크롤러를 가짜로 대체하여 도구 흐름 검증."""
    fake_results = [
        {
            "title": "연세대학교 2026 편입학 모집요강",
            "content": "연세대학교 편입학 안내. 모집학과 및 지원 서류 확인 필요.",
            "date": "2026-09-30",
            "url": "https://www.adiga.kr/iphak/transfer/main.do",
            "source": "어디가(adiga.kr) 편입학 정보",
            "category": "transfer",
        }
    ]
    import rag.external_crawler as ext
    monkeypatch.setattr(ext, "crawl_transfer_by_school", lambda **kw: fake_results)

    result = search_transfer_by_school.invoke({"school_name": "연세대", "n_results": 3})
    assert "연세대" in result
    assert "편입학" in result
    assert "어디가" in result


def test_search_scholarship_policy_no_api_key(monkeypatch):
    """API 키 없을 때 안내 메시지 반환 (에러 없음)."""
    import config.settings as cfg
    monkeypatch.setattr(cfg, "YOUTH_CENTER_API_KEY", "")

    result = search_scholarship_policy.invoke({"query": "국가장학금", "n_results": 3})
    assert "API 키가 설정되지 않았습니다" in result
    assert "YOUTH_CENTER_API_KEY" in result


def test_search_job_intern_no_api_key(monkeypatch):
    """워크넷 API 키 없을 때 안내 메시지 반환 (에러 없음)."""
    import config.settings as cfg
    monkeypatch.setattr(cfg, "WORKNET_API_KEY", "")

    result = search_job_intern.invoke({"query": "소프트웨어 인턴", "n_results": 3})
    assert "API 키가 설정되지 않았습니다" in result
    assert "WORKNET_API_KEY" in result


def test_search_contest_external_with_mock(monkeypatch):
    """K-스타트업 크롤러를 가짜로 대체하여 도구 흐름 검증."""
    fake_results = [
        {
            "title": "2026 AI 창업 공모전 모집",
            "content": "기관: 창업진흥원\n마감: D-5",
            "date": "D-5",
            "url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing-view.do?bizPbancSn=12345",
            "source": "K-스타트업 (창업진흥원)",
            "category": "contest",
        }
    ]
    import rag.external_crawler as ext
    monkeypatch.setattr(ext, "crawl_kstartup_contest", lambda **kw: fake_results)

    result = search_contest_external.invoke({"query": "AI 창업", "n_results": 3})
    assert "창업" in result
    assert "K-스타트업" in result
