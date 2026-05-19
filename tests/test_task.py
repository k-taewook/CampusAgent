"""
CampusAgent - Task CRUD 단위 테스트
"""
import pytest
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import (
    init_sqlite_db,
    add_assignment,
    add_subtask,
    add_subtasks,
    get_assignments,
    get_assignment_by_id,
    get_assignment_progress,
    get_assignments_with_progress,
    get_subtasks,
    update_assignment_status,
    update_subtask_status,
    delete_assignment,
    delete_subtask,
    get_upcoming_assignments,
)
from database.models import AssignmentCreate, AssignmentStatus, SubtaskCreate
from mcp_servers.task_server import _generate_subtask_plan
import config.settings as settings


# ──────────────────────────────────────
# Fixture: 테스트용 DB 사용
# ──────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """각 테스트마다 임시 DB 사용"""
    test_db = str(tmp_path / "test_campus.db")
    settings.SQLITE_DB_PATH = test_db
    # db.py 내부의 DB_PATH도 동기화
    import database.db as db_module
    db_module.SQLITE_DB_PATH = test_db
    init_sqlite_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


# ──────────────────────────────────────
# 테스트 케이스
# ──────────────────────────────────────

class TestAddAssignment:
    def test_add_basic(self):
        """기본 과제 추가"""
        data = AssignmentCreate(
            title="자료구조 레포트",
            course_name="자료구조",
            due_date="2026-04-10",
        )
        result = add_assignment(data)
        assert result.id == 1
        assert result.title == "자료구조 레포트"
        assert result.course_name == "자료구조"
        assert result.status == AssignmentStatus.PENDING

    def test_add_with_all_fields(self):
        """모든 필드 포함 과제 추가"""
        data = AssignmentCreate(
            title="알고리즘 프로젝트",
            course_name="알고리즘",
            due_date="2026-04-15",
            description="분할 정복 알고리즘 구현",
            priority="high",
        )
        result = add_assignment(data)
        assert result.description == "분할 정복 알고리즘 구현"
        assert result.priority == "high"

    def test_add_multiple(self):
        """여러 과제 추가"""
        for i in range(3):
            data = AssignmentCreate(
                title=f"과제 {i+1}",
                course_name=f"과목 {i+1}",
                due_date=f"2026-04-{10+i:02d}",
            )
            add_assignment(data)

        tasks = get_assignments()
        assert len(tasks) == 3


class TestGetAssignments:
    def _add_sample_tasks(self):
        """테스트용 샘플 과제 추가"""
        samples = [
            ("자료구조 레포트", "자료구조", "2026-04-10", "pending"),
            ("알고리즘 퀴즈", "알고리즘", "2026-04-12", "in_progress"),
            ("DB 과제", "데이터베이스", "2026-04-08", "done"),
        ]
        for title, course, due, status in samples:
            data = AssignmentCreate(title=title, course_name=course, due_date=due)
            a = add_assignment(data)
            if status != "pending":
                update_assignment_status(a.id, status)

    def test_get_all(self):
        """전체 조회"""
        self._add_sample_tasks()
        tasks = get_assignments()
        assert len(tasks) == 3

    def test_filter_by_status(self):
        """상태 필터"""
        self._add_sample_tasks()
        pending = get_assignments(status="pending")
        assert len(pending) == 1
        assert pending[0].title == "자료구조 레포트"

    def test_filter_by_course(self):
        """과목 필터"""
        self._add_sample_tasks()
        algo = get_assignments(course_name="알고리즘")
        assert len(algo) == 1


class TestUpdateStatus:
    def test_update_to_done(self):
        """완료 상태로 변경"""
        data = AssignmentCreate(title="테스트", course_name="과목", due_date="2026-04-10")
        result = add_assignment(data)
        updated = update_assignment_status(result.id, "done")
        assert updated.status == AssignmentStatus.DONE

    def test_update_invalid_status(self):
        """유효하지 않은 상태"""
        data = AssignmentCreate(title="테스트", course_name="과목", due_date="2026-04-10")
        result = add_assignment(data)
        with pytest.raises(ValueError):
            update_assignment_status(result.id, "invalid")

    def test_update_nonexistent(self):
        """존재하지 않는 과제"""
        result = update_assignment_status(9999, "done")
        assert result is None


class TestDeleteAssignment:
    def test_delete_existing(self):
        """존재하는 과제 삭제"""
        data = AssignmentCreate(title="삭제 테스트", course_name="과목", due_date="2026-04-10")
        result = add_assignment(data)
        assert delete_assignment(result.id) is True
        assert get_assignment_by_id(result.id) is None

    def test_delete_nonexistent(self):
        """존재하지 않는 과제 삭제"""
        assert delete_assignment(9999) is False


class TestGetById:
    def test_found(self):
        data = AssignmentCreate(title="조회 테스트", course_name="과목", due_date="2026-04-10")
        result = add_assignment(data)
        found = get_assignment_by_id(result.id)
        assert found is not None
        assert found.title == "조회 테스트"

    def test_not_found(self):
        found = get_assignment_by_id(9999)
        assert found is None


class TestSubtasks:
    def _add_parent(self):
        data = AssignmentCreate(
            title="캡스톤 디자인 발표",
            course_name="캡스톤디자인",
            due_date="2026-05-20",
        )
        return add_assignment(data)

    def test_add_subtask(self):
        parent = self._add_parent()
        subtask = add_subtask(
            SubtaskCreate(
                assignment_id=parent.id,
                title="발표 요구사항 확인",
                due_date="2026-05-15",
            )
        )

        assert subtask.id == 1
        assert subtask.assignment_id == parent.id
        assert subtask.status == AssignmentStatus.PENDING

    def test_add_multiple_subtasks_ordered(self):
        parent = self._add_parent()
        add_subtasks(
            parent.id,
            [
                SubtaskCreate(assignment_id=parent.id, title="세 번째", sort_order=3),
                SubtaskCreate(assignment_id=parent.id, title="첫 번째", sort_order=1),
                SubtaskCreate(assignment_id=parent.id, title="두 번째", sort_order=2),
            ],
        )

        subtasks = get_subtasks(parent.id)
        assert [s.title for s in subtasks] == ["첫 번째", "두 번째", "세 번째"]

    def test_progress_empty_subtasks(self):
        parent = self._add_parent()

        progress = get_assignment_progress(parent.id)

        assert progress["total"] == 0
        assert progress["done"] == 0
        assert progress["progress"] == 0

    def test_progress_partial_done(self):
        parent = self._add_parent()
        subtasks = add_subtasks(
            parent.id,
            [
                SubtaskCreate(assignment_id=parent.id, title="자료 조사", sort_order=1),
                SubtaskCreate(assignment_id=parent.id, title="PPT 작성", sort_order=2),
                SubtaskCreate(assignment_id=parent.id, title="리허설", sort_order=3),
            ],
        )

        update_subtask_status(subtasks[0].id, "done")
        progress = get_assignment_progress(parent.id)
        updated_parent = get_assignment_by_id(parent.id)

        assert progress["done"] == 1
        assert progress["total"] == 3
        assert progress["progress"] == 33
        assert updated_parent.status == AssignmentStatus.IN_PROGRESS

    def test_progress_all_done_updates_parent(self):
        parent = self._add_parent()
        subtasks = add_subtasks(
            parent.id,
            [
                SubtaskCreate(assignment_id=parent.id, title="자료 조사", sort_order=1),
                SubtaskCreate(assignment_id=parent.id, title="PPT 작성", sort_order=2),
            ],
        )

        for subtask in subtasks:
            update_subtask_status(subtask.id, "done")

        updated_parent = get_assignment_by_id(parent.id)
        progress = get_assignment_progress(parent.id)

        assert progress["progress"] == 100
        assert updated_parent.status == AssignmentStatus.DONE

    def test_delete_parent_removes_subtasks(self):
        parent = self._add_parent()
        add_subtask(SubtaskCreate(assignment_id=parent.id, title="자료 조사"))

        assert delete_assignment(parent.id) is True

        assert get_assignment_by_id(parent.id) is None
        assert get_subtasks(parent.id) == []

    def test_delete_subtask_resyncs_parent(self):
        parent = self._add_parent()
        subtasks = add_subtasks(
            parent.id,
            [
                SubtaskCreate(assignment_id=parent.id, title="자료 조사", sort_order=1),
                SubtaskCreate(assignment_id=parent.id, title="PPT 작성", sort_order=2),
            ],
        )
        update_subtask_status(subtasks[0].id, "done")

        assert delete_subtask(subtasks[0].id) is True

        progress = get_assignment_progress(parent.id)
        updated_parent = get_assignment_by_id(parent.id)
        assert progress["done"] == 0
        assert progress["total"] == 1
        assert updated_parent.status == AssignmentStatus.PENDING

    def test_subtask_invalid_status_rejected(self):
        parent = self._add_parent()
        subtask = add_subtask(SubtaskCreate(assignment_id=parent.id, title="자료 조사"))

        with pytest.raises(ValueError):
            update_subtask_status(subtask.id, "invalid")

    def test_get_assignments_with_progress(self):
        parent = self._add_parent()
        add_subtask(SubtaskCreate(assignment_id=parent.id, title="자료 조사"))

        items = get_assignments_with_progress()

        assert len(items) == 1
        assert items[0].assignment.id == parent.id
        assert items[0].total_subtasks == 1

    def test_generate_subtask_plan_count(self):
        plan = _generate_subtask_plan(
            "캡스톤 디자인 발표",
            "PPT 발표 준비",
            "2026-05-20",
        )

        assert 5 <= len(plan) <= 7
        assert all(item["title"] for item in plan)
        assert all(item["due_date"] for item in plan)
