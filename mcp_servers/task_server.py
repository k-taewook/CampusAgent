"""
CampusAgent - Task 관리 MCP 도구 (LangChain Tool)
- 과제 추가 / 조회 / 상태변경 / 삭제 / 마감임박 조회
- Agent가 자연어 요청을 해석한 뒤 호출하는 도구 모음
"""
from datetime import datetime, timedelta
from langchain_core.tools import tool
from typing import Optional

from database.db import (
    add_assignment,
    add_subtasks,
    get_assignments,
    get_assignment_by_id,
    get_assignment_progress,
    get_assignments_with_progress,
    get_subtasks,
    update_assignment_status,
    update_subtask_status,
    delete_assignment,
    get_upcoming_assignments,
)
from database.models import AssignmentCreate, SubtaskCreate


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


def _build_subtask_template(task_type: str) -> list[tuple[str, str]]:
    """과제 유형별 기본 서브태스크 템플릿"""
    templates = {
        "report": [
            ("요구사항 확인", "교수자 요구사항과 제출 형식을 확인합니다."),
            ("자료 조사", "핵심 참고 자료와 근거를 수집합니다."),
            ("목차 설계", "보고서 전체 구조와 흐름을 정리합니다."),
            ("초안 작성", "핵심 내용을 중심으로 초안을 작성합니다."),
            ("수정 및 보완", "표현, 논리, 분량을 점검하고 보완합니다."),
            ("최종 제출 준비", "파일 형식과 제출 경로를 확인하고 제출합니다."),
        ],
        "presentation": [
            ("요구사항 확인", "발표 주제와 평가 기준을 확인합니다."),
            ("자료 조사", "발표에 필요한 근거 자료를 수집합니다."),
            ("슬라이드 구조 설계", "발표 흐름과 슬라이드 구성을 정리합니다."),
            ("슬라이드 작성", "핵심 내용을 슬라이드에 반영합니다."),
            ("발표 대본 정리", "전달할 핵심 문장을 정리합니다."),
            ("리허설", "발표 시간과 흐름을 점검합니다."),
        ],
        "coding": [
            ("요구사항 분석", "기능 요구사항과 제출 조건을 정리합니다."),
            ("구조 설계", "모듈 구성과 구현 범위를 나눕니다."),
            ("핵심 기능 구현", "주요 기능을 먼저 구현합니다."),
            ("예외 처리 보강", "예외 상황과 누락된 로직을 점검합니다."),
            ("테스트 작성", "주요 흐름을 검증하는 테스트를 준비합니다."),
            ("제출 정리", "실행 방법과 제출 파일을 최종 점검합니다."),
        ],
        "exam": [
            ("범위 확인", "시험 범위와 평가 비중을 정리합니다."),
            ("핵심 개념 정리", "중요 개념과 공식을 요약합니다."),
            ("문제 풀이", "대표 문제를 풀어봅니다."),
            ("오답 정리", "틀린 문제와 약한 부분을 다시 확인합니다."),
            ("암기 보강", "반복 암기가 필요한 내용을 보강합니다."),
            ("최종 복습", "시험 직전 전체 흐름을 점검합니다."),
        ],
        "general": [
            ("요구사항 정리", "해야 할 작업과 제출 조건을 정리합니다."),
            ("자료 수집", "필요한 자료와 참고 정보를 모읍니다."),
            ("작업 계획 수립", "세부 순서와 우선순위를 정합니다."),
            ("핵심 작업 수행", "실제 본 작업을 진행합니다."),
            ("검토 및 보완", "누락과 오류를 점검합니다."),
            ("최종 제출 준비", "마감 전 제출 상태를 확인합니다."),
        ],
    }
    return templates.get(task_type, templates["general"])


def _guess_task_type(title: str, description: str) -> str:
    """과제 유형 추정"""
    combined = f"{title} {description}".lower()
    if any(keyword in combined for keyword in ["보고서", "레포트", "리포트", "조사"]):
        return "report"
    if any(keyword in combined for keyword in ["발표", "ppt", "프레젠테이션"]):
        return "presentation"
    if any(keyword in combined for keyword in ["프로젝트", "구현", "개발", "프로그래밍", "코드"]):
        return "coding"
    if any(keyword in combined for keyword in ["시험", "중간고사", "기말고사", "퀴즈"]):
        return "exam"
    return "general"


def _format_subtask_due_date(parent_due_date: str, offset_days: int) -> str:
    """부모 마감일 기준으로 서브태스크 날짜 계산"""
    normalized = parent_due_date.strip()
    due_has_time = len(normalized) > 10
    due_dt = datetime.strptime(normalized[:10], "%Y-%m-%d")
    target_dt = due_dt - timedelta(days=offset_days)
    if due_has_time and offset_days == 0:
        return normalized
    return target_dt.strftime("%Y-%m-%d")


def _generate_subtask_plan(title: str, description: str, due_date: str) -> list[dict]:
    """규칙 기반 서브태스크 계획 생성"""
    task_type = _guess_task_type(title, description)
    template = _build_subtask_template(task_type)
    total = len(template)
    subtasks: list[dict] = []

    for index, (subtask_title, subtask_description) in enumerate(template):
        offset_days = max(total - index - 1, 0)
        subtasks.append({
            "title": subtask_title,
            "description": subtask_description,
            "due_date": _format_subtask_due_date(due_date, offset_days),
            "status": "pending",
            "sort_order": index,
        })

    return subtasks


@tool
def add_task_with_subtasks(
    title: str,
    course_name: str,
    due_date: str,
    description: str = "",
    priority: str = "medium",
) -> str:
    """
    큰 과제를 추가하고 5~7개의 서브태스크로 자동 분해합니다.

    Args:
        title: 과제 제목
        course_name: 과목명
        due_date: 마감일 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)
        description: 과제 상세 설명
        priority: 우선순위 low/medium/high

    Returns:
        부모 과제와 서브태스크 생성 결과 문자열
    """
    try:
        assignment = add_assignment(
            AssignmentCreate(
                title=title,
                course_name=course_name,
                due_date=due_date,
                description=description if description else None,
                priority=priority,
            )
        )
        plan = _generate_subtask_plan(title, description, due_date)
        subtask_payloads = [
            SubtaskCreate(assignment_id=assignment.id, **item)
            for item in plan
        ]
        created = add_subtasks(assignment.id, subtask_payloads)
        progress = get_assignment_progress(assignment.id)

        lines = [
            "✅ 큰 과제를 서브태스크로 분해해 등록했습니다.",
            "",
            f"📌 부모 과제: [{assignment.id}] {assignment.title}",
            f"📚 과목: {assignment.course_name}",
            f"📅 마감일: {assignment.due_date}",
            f"📊 진행률: {progress['progress_percent']}% ({progress['completed_subtasks']}/{progress['total_subtasks']})",
            "",
            "📝 생성된 서브태스크",
        ]
        lines.extend(
            f"{index}. {subtask.title} ({subtask.due_date or '마감일 미정'})"
            for index, subtask in enumerate(created, 1)
        )
        lines.extend([
            "",
            "💡 다음 추천 행동",
            "- 서브태스크를 하나씩 진행 상태로 바꾸거나 완료 처리할 수 있습니다.",
            "- 진행률을 보려면 과제 대시보드나 `get_task_progress`를 사용하세요.",
        ])
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 서브태스크 과제 등록 실패: {e}"


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
def list_task_tree(
    status: Optional[str] = None,
    course_name: Optional[str] = None,
) -> str:
    """
    과제와 서브태스크를 계층형으로 조회합니다.

    Args:
        status: 상태 필터
        course_name: 과목명 필터

    Returns:
        계층형 과제 목록 문자열
    """
    try:
        assignments = get_assignments_with_progress(status=status, course_name=course_name)
        if not assignments:
            return "📭 등록된 과제가 없습니다."

        lines = [f"🌳 **과제 트리** (총 {len(assignments)}건)", "─" * 30, ""]
        for item in assignments:
            assignment = item.assignment
            lines.append(
                f"📌 **[{assignment.id}] {assignment.title}** | "
                f"{item.progress_percent}% ({item.completed_subtasks}/{item.total_subtasks}) | "
                f"상태: {assignment.status.value}"
            )
            lines.append(f"   📚 과목: {assignment.course_name} | 📅 마감: {assignment.due_date}")
            if not item.subtasks:
                lines.append("   └─ 서브태스크 없음")
            else:
                for subtask in item.subtasks:
                    lines.append(
                        f"   └─ [{subtask.id}] {subtask.title} | "
                        f"{subtask.status.value} | "
                        f"{subtask.due_date or '마감일 미정'}"
                    )
            lines.append("")
        return "\n".join(lines).rstrip()
    except Exception as e:
        return f"❌ 과제 트리 조회 실패: {e}"


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
def update_subtask_status_tool(subtask_id: int, new_status: str) -> str:
    """
    서브태스크 상태를 변경하고 부모 과제 진행률을 갱신합니다.

    Args:
        subtask_id: 변경할 서브태스크 ID
        new_status: 새로운 상태 (pending / in_progress / done)

    Returns:
        변경 결과 문자열
    """
    try:
        subtask = update_subtask_status(subtask_id, new_status)
        if subtask is None:
            return f"❌ ID {subtask_id}번 서브태스크를 찾을 수 없습니다."

        parent = get_assignment_by_id(subtask.assignment_id)
        progress = get_assignment_progress(subtask.assignment_id)
        return (
            "✅ 서브태스크 상태가 변경되었습니다!\n\n"
            f"📌 서브태스크: {subtask.title}\n"
            f"📍 상태: {subtask.status.value}\n"
            f"📊 부모 과제 진행률: {progress['progress_percent']}% "
            f"({progress['completed_subtasks']}/{progress['total_subtasks']})\n"
            f"🧩 부모 과제 상태: {parent.status.value if parent else '알 수 없음'}"
        )
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ 서브태스크 상태 변경 실패: {e}"


@tool
def get_task_progress(assignment_id: int) -> str:
    """
    특정 과제의 진행률과 남은 서브태스크를 조회합니다.

    Args:
        assignment_id: 진행률을 확인할 과제 ID

    Returns:
        진행률 문자열
    """
    try:
        assignment = get_assignment_by_id(assignment_id)
        if assignment is None:
            return f"❌ ID {assignment_id}번 과제를 찾을 수 없습니다."

        progress = get_assignment_progress(assignment_id)
        subtasks = get_subtasks(assignment_id)
        pending_items = [
            f"- {subtask.title} ({subtask.status.value})"
            for subtask in subtasks
            if subtask.status.value != "done"
        ]

        lines = [
            f"📊 **[{assignment.id}] {assignment.title} 진행률**",
            f"📚 과목: {assignment.course_name}",
            f"📅 마감일: {assignment.due_date}",
            f"📍 상태: {assignment.status.value}",
            f"✅ 진행률: {progress['progress_percent']}% ({progress['completed_subtasks']}/{progress['total_subtasks']})",
        ]
        if subtasks:
            lines.append("")
            lines.append("📝 남은 서브태스크")
            lines.extend(pending_items or ["- 모든 서브태스크 완료"])
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 진행률 조회 실패: {e}"


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
    add_task_with_subtasks,
    list_tasks,
    list_task_tree,
    update_task_status,
    update_subtask_status_tool,
    get_task_progress,
    delete_task,
    get_upcoming_deadlines,
]
