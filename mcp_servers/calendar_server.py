"""
CampusAgent - 캘린더/일정 관리 MCP 도구 (LangChain Tool)
- 일정 추가 / 조회 / 삭제 / D-day 계산 / 오늘 일정
"""
from langchain_core.tools import tool
from typing import Optional

from database.db import (
    add_schedule,
    get_schedules,
    get_schedules_by_date_range,
    get_today_schedules,
    delete_schedule,
    get_schedule_by_id,
    get_dday_schedules,
)
from database.models import ScheduleCreate


@tool
def add_calendar_event(
    title: str,
    date: str,
    start_time: str = "",
    end_time: str = "",
    category: str = "personal",
    description: str = "",
    is_recurring: bool = False,
) -> str:
    """
    새로운 일정을 캘린더에 추가합니다.

    Args:
        title: 일정 제목 (예: "자료구조 수업", "중간고사")
        date: 일정 날짜 (YYYY-MM-DD 형식, 예: "2026-04-10")
        start_time: 시작 시간 (HH:MM 형식, 예: "09:00", 선택)
        end_time: 종료 시간 (HH:MM 형식, 예: "10:30", 선택)
        category: 카테고리 class/exam/personal/meeting/other (기본값: "personal")
        description: 상세 설명 (선택)
        is_recurring: 매주 반복 여부 (기본값: false)

    Returns:
        추가된 일정 정보 문자열
    """
    try:
        data = ScheduleCreate(
            title=title,
            date=date,
            start_time=start_time if start_time else None,
            end_time=end_time if end_time else None,
            category=category,
            description=description if description else None,
            is_recurring=is_recurring,
        )
        schedule = add_schedule(data)
        return f"✅ 일정이 추가되었습니다!\n\n{schedule.to_display_string()}"
    except Exception as e:
        return f"❌ 일정 추가 실패: {e}"


@tool
def list_calendar_events(
    category: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """
    등록된 일정 목록을 조회합니다.

    Args:
        category: 카테고리 필터 (class/exam/personal/meeting/other, 선택)
        date: 특정 날짜 필터 (YYYY-MM-DD, 선택)

    Returns:
        일정 목록 문자열
    """
    try:
        schedules = get_schedules(category=category, date=date)
        if not schedules:
            return "📭 등록된 일정이 없습니다."

        header = f"📅 **일정 목록** (총 {len(schedules)}건)\n{'─' * 30}\n\n"
        items = "\n\n".join(s.to_display_string() for s in schedules)
        return header + items
    except Exception as e:
        return f"❌ 일정 조회 실패: {e}"


@tool
def get_today_schedule() -> str:
    """
    오늘의 일정을 조회합니다. 인자 없이 호출합니다.

    Returns:
        오늘 일정 목록 문자열
    """
    try:
        schedules = get_today_schedules()
        if not schedules:
            return "📭 오늘은 등록된 일정이 없습니다! 여유로운 하루 되세요 🎉"

        header = f"📅 **오늘의 일정** (총 {len(schedules)}건)\n{'─' * 30}\n\n"
        items = "\n\n".join(s.to_display_string() for s in schedules)
        return header + items
    except Exception as e:
        return f"❌ 오늘 일정 조회 실패: {e}"


@tool
def get_week_schedule(start_date: str, end_date: str) -> str:
    """
    특정 기간의 일정을 조회합니다.

    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        해당 기간 일정 목록 문자열
    """
    try:
        schedules = get_schedules_by_date_range(start_date, end_date)
        if not schedules:
            return f"📭 {start_date} ~ {end_date} 기간에 일정이 없습니다."

        header = f"📅 **{start_date} ~ {end_date} 일정** (총 {len(schedules)}건)\n{'─' * 30}\n\n"
        items = "\n\n".join(s.to_display_string() for s in schedules)
        return header + items
    except Exception as e:
        return f"❌ 일정 조회 실패: {e}"


@tool
def delete_calendar_event(schedule_id: int) -> str:
    """
    일정을 삭제합니다.

    Args:
        schedule_id: 삭제할 일정의 ID 번호

    Returns:
        삭제 결과 문자열
    """
    try:
        schedule = get_schedule_by_id(schedule_id)
        if schedule is None:
            return f"❌ ID {schedule_id}번 일정을 찾을 수 없습니다."

        success = delete_schedule(schedule_id)
        if success:
            return f"🗑️ **'{schedule.title}'** 일정이 삭제되었습니다."
        return "❌ 삭제에 실패했습니다."
    except Exception as e:
        return f"❌ 삭제 실패: {e}"


@tool
def check_dday(category: str = "exam") -> str:
    """
    시험이나 중요 일정의 D-day를 계산합니다.

    Args:
        category: 조회할 카테고리 (기본값: "exam")

    Returns:
        D-day 목록 문자열
    """
    try:
        dday_list = get_dday_schedules(category=category)
        if not dday_list:
            return f"📭 예정된 {category} 일정이 없습니다."

        header = f"⏰ **D-day 현황** ({category})\n{'─' * 30}\n\n"
        items = "\n".join(d["display"] for d in dday_list)
        return header + items
    except Exception as e:
        return f"❌ D-day 조회 실패: {e}"


# 에이전트에 바인딩할 도구 리스트
CALENDAR_TOOLS = [
    add_calendar_event,
    list_calendar_events,
    get_today_schedule,
    get_week_schedule,
    delete_calendar_event,
    check_dday,
]
