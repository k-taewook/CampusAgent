"""
CampusAgent - Task 관리 MCP 도구 (LangChain Tool)
- 과제 추가 / 조회 / 상태변경 / 삭제 / 마감임박 조회
- Agent가 자연어 요청을 해석한 뒤 호출하는 도구 모음
"""
from langchain_core.tools import tool
from typing import Optional
from datetime import datetime, timedelta

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
from database.models import AssignmentCreate, AssignmentStatus, SubtaskCreate


def _base_due_date(due_date: str) -> datetime:
    """부모 과제 마감일의 날짜 부분을 파싱합니다."""
    return datetime.strptime(due_date[:10], "%Y-%m-%d")


def _subtask_due_date(parent_due_date: str, index: int, total: int) -> str:
    """부모 마감일 기준으로 서브태스크 마감일을 역산합니다."""
    try:
        target = _base_due_date(parent_due_date)
    except ValueError:
        return parent_due_date[:10] if parent_due_date else ""

    days_before = max(total - index, 0)
    planned = target - timedelta(days=days_before)
    return planned.strftime("%Y-%m-%d")


def _detect_assignment_type(title: str, description: str = "") -> str:
    """제목과 설명 키워드로 과제 유형을 추정합니다."""
    text = f"{title} {description}".lower()
    if any(keyword in text for keyword in ["발표", "ppt", "프레젠테이션", "presentation"]):
        return "presentation"
    if any(keyword in text for keyword in ["보고서", "레포트", "리포트", "조사"]):
        return "report"
    if any(keyword in text for keyword in ["프로젝트", "구현", "개발", "프로그래밍", "코딩", "코드"]):
        return "coding"
    if any(keyword in text for keyword in ["시험", "중간고사", "기말고사", "퀴즈"]):
        return "exam"
    return "general"


def _generate_subtask_plan(title: str, description: str = "", due_date: str = "") -> list[dict]:
    """규칙 기반으로 5~7개의 서브태스크 계획을 생성합니다."""
    task_type = _detect_assignment_type(title, description)
    templates = {
        "presentation": [
            ("요구사항 확인", "발표 주제, 분량, 평가 기준, 제출 형식을 확인합니다."),
            ("자료 조사", "발표에 필요한 핵심 자료와 근거를 수집합니다."),
            ("슬라이드 구성 설계", "도입, 본론, 결론 흐름과 슬라이드 목차를 잡습니다."),
            ("PPT 초안 작성", "각 슬라이드의 핵심 문장과 시각 자료를 배치합니다."),
            ("발표 대본 작성", "슬라이드별 설명과 전환 멘트를 준비합니다."),
            ("리허설 및 제출 정리", "시간을 맞춰 연습하고 최종 제출 파일을 정리합니다."),
        ],
        "report": [
            ("주제와 요구사항 확인", "보고서 주제, 분량, 인용 방식, 제출 형식을 확인합니다."),
            ("자료 조사", "신뢰할 수 있는 자료와 참고문헌 후보를 수집합니다."),
            ("목차 작성", "서론, 본론, 결론 구조와 핵심 논점을 정리합니다."),
            ("초안 작성", "목차에 따라 본문 초안을 작성합니다."),
            ("검토 및 보완", "논리 흐름, 인용, 문장 표현을 점검합니다."),
            ("최종 편집 및 제출", "형식과 파일명을 정리하고 제출합니다."),
        ],
        "coding": [
            ("요구사항 분석", "기능 요구사항과 제출 조건을 구체화합니다."),
            ("구조 설계", "모듈, 데이터 구조, 주요 흐름을 설계합니다."),
            ("핵심 기능 구현", "가장 중요한 기능부터 동작하도록 구현합니다."),
            ("예외 처리와 디버깅", "오류 상황과 경계 조건을 점검합니다."),
            ("테스트 작성 및 실행", "주요 기능을 검증하는 테스트를 작성하고 실행합니다."),
            ("제출 파일 정리", "README, 실행 방법, 제출물을 정리합니다."),
        ],
        "exam": [
            ("시험 범위 확인", "시험 범위, 형식, 준비 자료를 확인합니다."),
            ("핵심 개념 요약", "단원별 핵심 개념과 공식을 정리합니다."),
            ("기출 및 예제 풀이", "대표 문제를 풀며 출제 유형을 익힙니다."),
            ("오답 정리", "틀린 문제와 헷갈린 개념을 다시 정리합니다."),
            ("최종 복습", "요약 노트와 오답을 중심으로 반복 확인합니다."),
        ],
        "general": [
            ("요구사항 정리", "과제 목표, 제출 형식, 마감 조건을 확인합니다."),
            ("자료 수집", "필요한 자료와 참고 정보를 모읍니다."),
            ("작업 계획 수립", "해야 할 일을 순서대로 나누고 우선순위를 정합니다."),
            ("본문 작업", "핵심 산출물을 작성하거나 제작합니다."),
            ("검토 및 수정", "누락된 요구사항과 품질을 점검합니다."),
            ("최종 제출 정리", "파일명, 형식, 제출 경로를 확인합니다."),
        ],
    }

    steps = templates[task_type]
    return [
        {
            "title": step_title,
            "description": step_description,
            "due_date": _subtask_due_date(due_date, index, len(steps)) if due_date else None,
            "sort_order": index,
        }
        for index, (step_title, step_description) in enumerate(steps, start=1)
    ]


def _format_progress_line(assignment_id: int) -> str:
    progress = get_assignment_progress(assignment_id)
    return f"진행률 {progress['progress']}% ({progress['done']}/{progress['total']})"


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
        title: 부모 과제 제목
        course_name: 과목명
        due_date: 부모 과제 마감일 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)
        description: 과제 상세 설명
        priority: 우선순위 low/medium/high

    Returns:
        부모 과제와 생성된 서브태스크 목록
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
        subtasks = add_subtasks(
            assignment.id,
            [
                SubtaskCreate(
                    assignment_id=assignment.id,
                    title=item["title"],
                    description=item["description"],
                    due_date=item["due_date"],
                    sort_order=item["sort_order"],
                )
                for item in plan
            ],
        )
        items = "\n".join(
            f"{index}. {subtask.title}"
            f"{f' ({subtask.due_date})' if subtask.due_date else ''}"
            for index, subtask in enumerate(subtasks, start=1)
        )
        return (
            "✅ 큰 과제를 서브태스크로 분해해 등록했습니다.\n\n"
            f"📌 부모 과제: [{assignment.id}] {assignment.title}\n"
            f"📊 {_format_progress_line(assignment.id)}\n\n"
            f"{items}\n\n"
            "💡 다음 추천 행동: 1번 서브태스크를 시작하면 상태를 `in_progress`로 바꿔보세요."
        )
    except Exception as e:
        return f"❌ 과제 분해 등록 실패: {e}"


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
def list_task_tree() -> str:
    """
    부모 과제와 서브태스크를 계층 구조로 조회합니다.

    Returns:
        과제 트리 목록
    """
    try:
        items = get_assignments_with_progress()
        if not items:
            return "📭 등록된 과제가 없습니다."

        lines = [f"📚 **과제 트리** (총 {len(items)}건)"]
        for item in items:
            assignment = item.assignment
            lines.append(
                f"\n📌 **[{assignment.id}] {assignment.title}** "
                f"({assignment.course_name}, {assignment.due_date})"
            )
            if item.total_subtasks:
                lines.append(f"   📊 진행률 {item.progress}% ({item.done_subtasks}/{item.total_subtasks})")
                for subtask in item.subtasks:
                    marker = "✅" if subtask.status == AssignmentStatus.DONE else "☐"
                    due = f" | {subtask.due_date}" if subtask.due_date else ""
                    lines.append(f"   {marker} [{subtask.id}] {subtask.title}{due}")
            else:
                lines.append(f"   상태: {assignment.status.value}")
        return "\n".join(lines)
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
        new_status: pending / in_progress / done

    Returns:
        변경 결과와 부모 과제 진행률
    """
    try:
        subtask = update_subtask_status(subtask_id, new_status)
        if subtask is None:
            return f"❌ ID {subtask_id}번 서브태스크를 찾을 수 없습니다."
        return (
            "✅ 서브태스크 상태가 변경되었습니다.\n\n"
            f"{subtask.to_display_string()}\n"
            f"📊 부모 과제 {_format_progress_line(subtask.assignment_id)}"
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
        assignment_id: 조회할 부모 과제 ID

    Returns:
        진행률과 서브태스크 목록
    """
    try:
        assignment = get_assignment_by_id(assignment_id)
        if assignment is None:
            return f"❌ ID {assignment_id}번 과제를 찾을 수 없습니다."
        progress = get_assignment_progress(assignment_id)
        subtasks = get_subtasks(assignment_id)
        if not subtasks:
            return f"📊 [{assignment.id}] {assignment.title}에는 아직 서브태스크가 없습니다."

        lines = [
            f"📊 **[{assignment.id}] {assignment.title} 진행률**",
            f"- {progress['progress']}% ({progress['done']}/{progress['total']})",
        ]
        for subtask in subtasks:
            marker = "✅" if subtask.status == AssignmentStatus.DONE else "☐"
            lines.append(f"{marker} [{subtask.id}] {subtask.title} - {subtask.status.value}")
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
