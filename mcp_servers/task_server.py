"""
CampusAgent - Task 관리 MCP 도구 (LangChain Tool)
- 과제 추가 / 조회 / 상태변경 / 삭제 / 마감임박 조회
- Agent가 자연어 요청을 해석한 뒤 호출하는 도구 모음
"""
from langchain_core.tools import tool
from typing import Optional

from database.db import (
    add_assignment,
    get_assignments,
    get_assignment_by_id,
    update_assignment_status,
    delete_assignment,
    get_upcoming_assignments,
)
from database.models import AssignmentCreate


@tool
def add_task(
    title: str,
    course_name: str,
    due_date: str,
    description: str = "",
    priority: str = "medium",
) -> str:
    """
    새로운 과제(할 일)를 추가합니다.

    Args:
        title: 과제 제목 (예: "자료구조 레포트")
        course_name: 과목명 (예: "자료구조")
        due_date: 마감일 (YYYY-MM-DD 형식, 예: "2026-04-10")
        description: 과제 상세 설명 (선택, 기본값: "")
        priority: 우선순위 low/medium/high (선택, 기본값: "medium")

    Returns:
        추가된 과제 정보 문자열
    """
    try:
        data = AssignmentCreate(
            title=title,
            course_name=course_name,
            due_date=due_date,
            description=description if description else None,
            priority=priority,
        )
        assignment = add_assignment(data)
        return f"✅ 과제가 추가되었습니다!\n\n{assignment.to_display_string()}"
    except Exception as e:
        return f"❌ 과제 추가 실패: {e}"


@tool
def list_tasks(
    status: Optional[str] = None,
    course_name: Optional[str] = None,
) -> str:
    """
    등록된 과제 목록을 조회합니다.

    Args:
        status: 상태 필터 (pending/in_progress/done/overdue, 선택)
        course_name: 과목명 필터 (선택)

    Returns:
        과제 목록 문자열
    """
    try:
        assignments = get_assignments(status=status, course_name=course_name)
        if not assignments:
            return "📭 등록된 과제가 없습니다."

        header = f"📚 **과제 목록** (총 {len(assignments)}건)\n{'─' * 30}\n\n"
        items = "\n\n".join(a.to_display_string() for a in assignments)
        return header + items
    except Exception as e:
        return f"❌ 과제 조회 실패: {e}"


@tool
def update_task_status(assignment_id: int, new_status: str) -> str:
    """
    과제의 상태를 변경합니다.

    Args:
        assignment_id: 변경할 과제의 ID 번호
        new_status: 새로운 상태 (pending / in_progress / done)

    Returns:
        변경 결과 문자열
    """
    try:
        assignment = update_assignment_status(assignment_id, new_status)
        if assignment is None:
            return f"❌ ID {assignment_id}번 과제를 찾을 수 없습니다."
        return f"✅ 과제 상태가 변경되었습니다!\n\n{assignment.to_display_string()}"
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ 상태 변경 실패: {e}"


@tool
def delete_task(assignment_id: int) -> str:
    """
    과제를 삭제합니다.

    Args:
        assignment_id: 삭제할 과제의 ID 번호

    Returns:
        삭제 결과 문자열
    """
    try:
        # 삭제 전 정보 조회
        assignment = get_assignment_by_id(assignment_id)
        if assignment is None:
            return f"❌ ID {assignment_id}번 과제를 찾을 수 없습니다."

        success = delete_assignment(assignment_id)
        if success:
            return f"🗑️ **'{assignment.title}'** 과제가 삭제되었습니다."
        return f"❌ 삭제에 실패했습니다."
    except Exception as e:
        return f"❌ 삭제 실패: {e}"


@tool
def get_upcoming_deadlines(days: int = 7) -> str:
    """
    마감이 임박한 과제를 조회합니다.

    Args:
        days: 며칠 이내의 과제를 조회할지 (기본값: 7일)

    Returns:
        마감 임박 과제 목록 문자열
    """
    try:
        assignments = get_upcoming_assignments(days=days)
        if not assignments:
            return f"🎉 {days}일 이내에 마감인 과제가 없습니다!"

        header = f"⏰ **{days}일 이내 마감 과제** (총 {len(assignments)}건)\n{'─' * 30}\n\n"
        items = "\n\n".join(a.to_display_string() for a in assignments)
        return header + items
    except Exception as e:
        return f"❌ 조회 실패: {e}"


# 에이전트에 바인딩할 도구 리스트
TASK_TOOLS = [
    add_task,
    list_tasks,
    update_task_status,
    delete_task,
    get_upcoming_deadlines,
]
