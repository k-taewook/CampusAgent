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
    _load_student_info_from_json,
    load_student_info_data,
    search_student_info,
)


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
