"""
CampusAgent - 장기기억 SQLite 저장/복원 테스트
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config.settings as settings
import database.db as db_module
from database.db import (
    clear_conversation_history,
    get_latest_memory_summary,
    get_or_create_conversation_session,
    init_sqlite_db,
    load_recent_conversation_messages,
    save_conversation_message,
    save_memory_summary,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db = str(tmp_path / "test_campus_memory.db")
    settings.SQLITE_DB_PATH = test_db
    db_module.SQLITE_DB_PATH = test_db
    init_sqlite_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


def test_create_session_and_store_messages():
    session = get_or_create_conversation_session("test_session", "테스트 세션")
    assert session["id"] == "test_session"

    user_id = save_conversation_message("test_session", "user", "편입학 정보 알려줘")
    assistant_id = save_conversation_message("test_session", "assistant", "편입학 정보를 찾았습니다.")
    assert assistant_id > user_id

    messages = load_recent_conversation_messages("test_session", limit=10)
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "편입학 정보 알려줘"


def test_memory_summary_roundtrip():
    save_memory_summary("test_session", "사용자는 편입학 정보에 관심이 있음")
    assert get_latest_memory_summary("test_session") == "사용자는 편입학 정보에 관심이 있음"


def test_clear_conversation_history():
    save_conversation_message("test_session", "user", "국가장학금 알려줘")
    save_memory_summary("test_session", "장학금 관심")

    assert clear_conversation_history("test_session") is True
    assert load_recent_conversation_messages("test_session") == []
    assert get_latest_memory_summary("test_session") is None


def test_invalid_role_rejected():
    """유효하지 않은 role은 ValueError"""
    with pytest.raises(ValueError):
        save_conversation_message("test_session", "bot", "내용")


def test_empty_content_rejected():
    """빈 content는 ValueError"""
    with pytest.raises(ValueError):
        save_conversation_message("test_session", "user", "   ")


def test_clear_preserves_session_row():
    """clear 후에도 세션 row 자체는 남아 있음"""
    save_conversation_message("test_session", "user", "안녕")
    clear_conversation_history("test_session")
    session = get_or_create_conversation_session("test_session")
    assert session["id"] == "test_session"


def test_clear_nonexistent_returns_false():
    """메시지·요약이 없는 세션을 clear하면 False"""
    assert clear_conversation_history("없는_세션") is False
