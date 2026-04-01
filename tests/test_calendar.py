"""
CampusAgent - 캘린더 CRUD 단위 테스트
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import (
    init_sqlite_db,
    add_schedule,
    get_schedules,
    get_schedule_by_id,
    get_schedules_by_date_range,
    get_today_schedules,
    delete_schedule,
    get_dday_schedules,
)
from database.models import ScheduleCreate
import config.settings as settings


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """각 테스트마다 임시 DB 사용"""
    test_db = str(tmp_path / "test_campus.db")
    settings.SQLITE_DB_PATH = test_db
    import database.db as db_module
    db_module.SQLITE_DB_PATH = test_db
    init_sqlite_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


class TestAddSchedule:
    def test_add_basic(self):
        """기본 일정 추가"""
        data = ScheduleCreate(
            title="자료구조 수업",
            date="2026-04-01",
            start_time="09:00",
            end_time="10:30",
            category="class",
        )
        result = add_schedule(data)
        assert result.id == 1
        assert result.title == "자료구조 수업"
        assert result.category == "class"
        assert result.start_time == "09:00"

    def test_add_exam(self):
        """시험 일정 추가"""
        data = ScheduleCreate(
            title="중간고사 - 알고리즘",
            date="2026-04-14",
            category="exam",
            description="범위: 1~5장",
        )
        result = add_schedule(data)
        assert result.category == "exam"
        assert result.description == "범위: 1~5장"

    def test_add_recurring(self):
        """반복 일정 추가"""
        data = ScheduleCreate(
            title="데이터베이스 수업",
            date="2026-04-02",
            start_time="13:00",
            end_time="14:30",
            category="class",
            is_recurring=True,
        )
        result = add_schedule(data)
        assert result.is_recurring is True


class TestGetSchedules:
    def _add_samples(self):
        samples = [
            ("자료구조 수업", "2026-04-01", "class"),
            ("알고리즘 시험", "2026-04-14", "exam"),
            ("스터디 모임", "2026-04-05", "meeting"),
        ]
        for title, date, cat in samples:
            add_schedule(ScheduleCreate(title=title, date=date, category=cat))

    def test_get_all(self):
        self._add_samples()
        schedules = get_schedules()
        assert len(schedules) == 3

    def test_filter_by_category(self):
        self._add_samples()
        exams = get_schedules(category="exam")
        assert len(exams) == 1
        assert exams[0].title == "알고리즘 시험"

    def test_filter_by_date(self):
        self._add_samples()
        april1 = get_schedules(date="2026-04-01")
        assert len(april1) == 1

    def test_date_range(self):
        self._add_samples()
        result = get_schedules_by_date_range("2026-04-01", "2026-04-10")
        assert len(result) == 2  # 4/1 + 4/5


class TestDeleteSchedule:
    def test_delete_existing(self):
        data = ScheduleCreate(title="삭제 테스트", date="2026-04-10")
        result = add_schedule(data)
        assert delete_schedule(result.id) is True
        assert get_schedule_by_id(result.id) is None

    def test_delete_nonexistent(self):
        assert delete_schedule(9999) is False


class TestGetById:
    def test_found(self):
        data = ScheduleCreate(title="조회 테스트", date="2026-04-10")
        result = add_schedule(data)
        found = get_schedule_by_id(result.id)
        assert found is not None
        assert found.title == "조회 테스트"

    def test_not_found(self):
        assert get_schedule_by_id(9999) is None


class TestDday:
    def test_dday_calculation(self):
        """D-day 계산"""
        # 미래 날짜로 시험 추가
        data = ScheduleCreate(
            title="기말고사",
            date="2026-12-31",
            category="exam",
        )
        add_schedule(data)
        dday_list = get_dday_schedules(category="exam")
        assert len(dday_list) >= 1
        assert dday_list[0]["d_day"] > 0
        assert "기말고사" in dday_list[0]["display"]
