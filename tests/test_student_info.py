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
    _build_personalized_queries,
    _load_student_info_from_json,
    load_student_info_data,
    search_personalized_student_info,
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


def test_build_personalized_queries():
    queries = _build_personalized_queries(
        major="컴퓨터시스템공학과",
        grade="2학년",
        interests="policy,contest,intern",
        preferred_school="인하대",
        career_goal="백엔드 개발자",
    )

    labels = {q["label"] for q in queries}
    assert "장학금/청년정책" in labels
    assert "공모전/대외활동" in labels
    assert "현장실습/인턴십" in labels
    assert any("컴퓨터시스템공학과" in q["query"] for q in queries)


def test_personalized_student_info_search():
    load_student_info_data.invoke({"filepath": _sample_path()})

    result = search_personalized_student_info.invoke({
        "major": "컴퓨터시스템공학과",
        "grade": "2학년",
        "interests": "policy,contest",
        "preferred_school": "",
        "career_goal": "소프트웨어 개발자",
        "n_results": 4,
    })

    assert "개인화 대학 정보 추천" in result
    assert "컴퓨터시스템공학과" in result
    assert "추천 이유" in result or "맞춤 결과를 찾지 못했습니다" in result


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
            "url": "https://admission.yonsei.ac.kr",
            "source": "연세대학교 입학처",
            "category": "transfer",
        }
    ]
    import rag.external_crawler as ext
    monkeypatch.setattr(ext, "crawl_transfer_by_school", lambda **kw: fake_results)

    result = search_transfer_by_school.invoke({"school_name": "연세대", "n_results": 3})
    assert "연세대" in result
    assert "편입학" in result
    assert "입학처" in result


def test_transfer_fallback_does_not_return_removed_adiga_url():
    """편입학 안내가 삭제된 어디가 예전 경로를 반환하지 않는지 검증."""
    from rag.external_crawler import crawl_transfer_by_school

    results = crawl_transfer_by_school("인하대", max_results=3)
    joined = "\n".join(item["url"] for item in results)

    assert "https://admission.inha.ac.kr" in joined
    assert "/iphak/transfer/main.do" not in joined


def test_search_scholarship_policy_no_api_key(monkeypatch):
    """API 키 없을 때 안내 메시지 반환 (에러 없음)."""
    import config.settings as cfg
    monkeypatch.setattr(cfg, "YOUTH_CENTER_API_KEY", "")

    result = search_scholarship_policy.invoke({"query": "국가장학금", "n_results": 3})
    assert "API 키가 설정되지 않았습니다" in result
    assert "YOUTH_CENTER_API_KEY" in result


def test_search_scholarship_policy_asks_for_missing_context(monkeypatch):
    """개인화 정책 추천에 필요한 조건이 부족하면 바로 검색하지 않고 질문한다."""
    import config.settings as cfg
    monkeypatch.setattr(cfg, "YOUTH_CENTER_API_KEY", "dummy-key")

    result = search_scholarship_policy.invoke({
        "query": "내가 받을 수 있는 청년 정책 찾아줘",
        "n_results": 3,
    })

    assert "추가 조건이 필요합니다" in result
    assert "거주 지역" in result
    assert "나이" in result
    assert "재학 상태" in result
    assert "취업 상태" in result


def test_search_scholarship_policy_reranks_with_user_context(monkeypatch):
    """사용자 조건이 있으면 온통청년 결과를 후보로 표시하고 조건 단서가 있는 항목을 우선한다."""
    import config.settings as cfg
    import rag.external_crawler as ext

    monkeypatch.setattr(cfg, "YOUTH_CENTER_API_KEY", "dummy-key")
    fake_results = [
        {
            "title": "전국 청년 문화 지원",
            "content": "청년 대상 일반 지원사업",
            "date": "",
            "url": "https://www.youthcenter.go.kr/a",
            "source": "온통청년",
            "category": "policy",
        },
        {
            "title": "인천 대학생 미취업 청년 지원",
            "content": "인천 거주 대학생 및 미취업 청년 대상 지원사업",
            "date": "",
            "url": "https://www.youthcenter.go.kr/b",
            "source": "온통청년",
            "category": "policy",
        },
    ]
    monkeypatch.setattr(ext, "fetch_youth_policy", lambda **kw: fake_results)

    result = search_scholarship_policy.invoke({
        "query": "나는 인천에 사는 대학생이고 아직 취업 안 했어. 내가 받을 수 있는 청년 정책 찾아줘",
        "n_results": 2,
    })

    assert "청년정책/장학금 후보" in result
    assert "실제 신청 가능 여부를 확정하지 않는" in result
    assert "온통청년 원문 URL" in result
    assert result.index("인천 대학생 미취업 청년 지원") < result.index("전국 청년 문화 지원")
    assert "확인 필요 조건" in result


def test_search_scholarship_policy_stores_public_api_metadata(monkeypatch):
    """공공 API 결과를 저장할 때 출처 유형과 자격 확인 여부 metadata를 남긴다."""
    import chromadb
    import config.settings as cfg
    import rag.external_crawler as ext

    monkeypatch.setattr(cfg, "YOUTH_CENTER_API_KEY", "dummy-key")
    monkeypatch.setattr(ext, "fetch_youth_policy", lambda **kw: [
        {
            "title": "인천 청년 주거 지원",
            "content": "인천 거주 청년 대상 주거 지원",
            "date": "",
            "url": "https://www.youthcenter.go.kr/policy",
            "source": "온통청년",
            "category": "policy",
        }
    ])

    search_scholarship_policy.invoke({
        "query": "인천 24세 대학생 미취업 청년 주거 지원",
        "n_results": 1,
        "region": "인천",
        "age": "24세",
        "student_status": "대학생",
        "employment_status": "미취업",
    })

    client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
    collection = client.get_collection(settings.CHROMA_COLLECTION_NAME)
    stored = collection.get(include=["metadatas"])
    metadata = stored["metadatas"][0]
    assert metadata["source_type"] == "public_api"
    assert metadata["provider"] == "youthcenter"
    assert metadata["eligibility_checked"] == "false"
    assert "인천" in metadata["query_context"]


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
